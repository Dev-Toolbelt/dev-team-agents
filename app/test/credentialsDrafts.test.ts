/**
 * The pure rules behind the credentials form: what counts as a change, and the ordered ops a
 * save sends. Ops are checked by applying them to a copy of the document, the way the CLI does.
 */
import { describe, expect, it } from 'vitest';

import {
  EMPTY_DRAFTS,
  addDatabase,
  editAddedDatabase,
  pointerOf,
  removeDatabase,
  reportDrafts,
  segmentsOf,
  setSecret,
  setValue,
} from '../src/renderer/credentials/drafts.js';
import type { CredentialsLocalView, CredentialsPatchOp } from '../src/shared/api.js';

function view(data: Record<string, unknown> | null): CredentialsLocalView {
  return { path: '/p/credentials.local.json', exists: true, valid: data !== null, error: null, hash: 'h', data, unknown_paths: [] };
}

const secret = (set: boolean) => ({ secret: true, set });
const dbRow = (host: string, port: unknown = '') => ({ type: 'pg', host, port, database: '', username: '', password: secret(false) });

function baseData(): Record<string, unknown> {
  return {
    work_feedback_active: true,
    work_feedback_interval_minutes: 5,
    devops: { agents: ['a'], staging: { database: [dbRow('h0', 5432), dbRow('h1'), dbRow('h2')] } },
    app: { staging: { appUrl: '', username: '', password: secret(true) } },
  };
}

/** Hosts of the database rows in `devops.staging` of an applied document. */
function hostsOf(document: Record<string, unknown>): unknown[] {
  const devops = document['devops'] as { staging: { database: { host: unknown }[] } };
  return devops.staging.database.map((row) => row.host);
}

/** A tiny RFC 6902-ish applier for the ops the form emits (`set`, `unset`, `-` append). */
type Container = Record<string, unknown> | unknown[];

function apply(document: unknown, ops: readonly CredentialsPatchOp[]): Record<string, unknown> {
  const root = structuredClone(document) as Record<string, unknown>;
  for (const op of ops) {
    const segments = segmentsOf(op.pointer);
    const last = segments[segments.length - 1] as string;
    let parent: Container = root;
    for (const segment of segments.slice(0, -1)) {
      const next: unknown = (parent as Record<string, unknown>)[segment];
      if (next === undefined) throw new Error(`missing parent for ${op.pointer}`);
      parent = next as Container;
    }
    if (op.op === 'unset') {
      if (Array.isArray(parent)) parent.splice(Number(last), 1);
      else delete parent[last];
    } else if (Array.isArray(parent)) {
      if (last === '-') parent.push(op.value);
      else parent[Number(last)] = op.value;
    } else {
      parent[last] = op.value;
    }
  }
  return root;
}

describe('pointers', () => {
  it('escapes ~ and / in keys and round-trips them', () => {
    const pointer = pointerOf('a~b', 'c/d', 3);
    expect(pointer).toBe('/a~0b/c~1d/3');
    expect(segmentsOf(pointer)).toEqual(['a~b', 'c/d', '3']);
  });
});

describe('reportDrafts', () => {
  it('sends nothing when nothing changed', () => {
    const report = reportDrafts(view(baseData()), EMPTY_DRAFTS);
    expect(report).toEqual({ ops: [], problems: {}, changes: 0 });
  });

  it('sends nothing when a draft equals the saved value', () => {
    const drafts = setValue(setValue(EMPTY_DRAFTS, '/work_feedback_active', true), '/work_feedback_interval_minutes', '5');
    expect(reportDrafts(view(baseData()), drafts).changes).toBe(0);
  });

  it('turns one leaf edit into one set op at its pointer', () => {
    const drafts = setValue(EMPTY_DRAFTS, '/app/staging/appUrl', 'https://x.test');
    const report = reportDrafts(view(baseData()), drafts);
    expect(report.ops).toEqual([{ op: 'set', pointer: '/app/staging/appUrl', value: 'https://x.test' }]);
    expect(report.changes).toBe(1);
  });

  it('escapes ~ and / in the pointer of an edited key', () => {
    const data = { odd: { 'a~b/c': 'old' } };
    const drafts = setValue(EMPTY_DRAFTS, pointerOf('odd', 'a~b/c'), 'new');
    const { ops } = reportDrafts(view(data), drafts);
    expect(ops).toEqual([{ op: 'set', pointer: '/odd/a~0b~1c', value: 'new' }]);
    expect(apply(data, ops)).toEqual({ odd: { 'a~b/c': 'new' } });
  });

  it('sends a changed list of strings whole', () => {
    const report = reportDrafts(view(baseData()), setValue(EMPTY_DRAFTS, '/devops/agents', ['a', 'b']));
    expect(report.ops).toEqual([{ op: 'set', pointer: '/devops/agents', value: ['a', 'b'] }]);
  });

  describe('interval', () => {
    it('is sent as a number', () => {
      const report = reportDrafts(view(baseData()), setValue(EMPTY_DRAFTS, '/work_feedback_interval_minutes', ' 10 '));
      expect(report.ops).toEqual([{ op: 'set', pointer: '/work_feedback_interval_minutes', value: 10 }]);
    });

    it.each(['', '0', '-3', '1.5', 'abc'])('rejects %j and sends nothing for it', (text) => {
      const report = reportDrafts(view(baseData()), setValue(EMPTY_DRAFTS, '/work_feedback_interval_minutes', text));
      expect(report.ops).toEqual([]);
      expect(report.problems['/work_feedback_interval_minutes']).toBeTruthy();
      expect(report.changes).toBe(1);
    });
  });

  describe('type preservation', () => {
    it('keeps a numeric port a number', () => {
      const report = reportDrafts(view(baseData()), setValue(EMPTY_DRAFTS, '/devops/staging/database/0/port', '6543'));
      expect(report.ops).toEqual([{ op: 'set', pointer: '/devops/staging/database/0/port', value: 6543 }]);
    });

    it('keeps a string port a string, even when it looks numeric', () => {
      const report = reportDrafts(view(baseData()), setValue(EMPTY_DRAFTS, '/devops/staging/database/1/port', '6543'));
      expect(report.ops).toEqual([{ op: 'set', pointer: '/devops/staging/database/1/port', value: '6543' }]);
    });

    it('falls back to text when a numeric port is given non-numeric text', () => {
      const report = reportDrafts(view(baseData()), setValue(EMPTY_DRAFTS, '/devops/staging/database/0/port', 'abc'));
      expect(report.ops[0]?.value).toBe('abc');
    });
  });

  describe('secrets', () => {
    it('sends a replacement as a set with the typed value', () => {
      const report = reportDrafts(view(baseData()), setSecret(EMPTY_DRAFTS, '/app/staging/password', { kind: 'replace', value: 'hunter2' }));
      expect(report.ops).toEqual([{ op: 'set', pointer: '/app/staging/password', value: 'hunter2' }]);
    });

    it('ignores a replace that was opened but left empty', () => {
      const report = reportDrafts(view(baseData()), setSecret(EMPTY_DRAFTS, '/app/staging/password', { kind: 'replace', value: '' }));
      expect(report).toEqual({ ops: [], problems: {}, changes: 0 });
    });

    it('sends a removal as a set to the empty string, keeping the key', () => {
      const report = reportDrafts(view(baseData()), setSecret(EMPTY_DRAFTS, '/app/staging/password', { kind: 'remove' }));
      expect(report.ops).toEqual([{ op: 'set', pointer: '/app/staging/password', value: '' }]);
    });

    it('does nothing to remove a secret that is not set', () => {
      const report = reportDrafts(view(baseData()), setSecret(EMPTY_DRAFTS, '/devops/staging/database/0/password', { kind: 'remove' }));
      expect(report.ops).toEqual([]);
    });
  });

  describe('database rows', () => {
    const list = '/devops/staging/database';

    it('appends an added row with the dash pointer', () => {
      let drafts = addDatabase(EMPTY_DRAFTS, list);
      drafts = editAddedDatabase(drafts, list, 1, 'host', 'new-host');
      const { ops } = reportDrafts(view(baseData()), drafts);
      expect(ops).toEqual([
        { op: 'set', pointer: `${list}/-`, value: { type: '', host: 'new-host', port: '', database: '', username: '', password: '' } },
      ]);
      expect(hostsOf(apply(baseData(), ops))).toHaveLength(4);
    });

    it('removes rows from the highest index down', () => {
      let drafts = removeDatabase(EMPTY_DRAFTS, list, 0);
      drafts = removeDatabase(drafts, list, 2);
      const { ops } = reportDrafts(view(baseData()), drafts);
      expect(ops).toEqual([
        { op: 'unset', pointer: `${list}/2` },
        { op: 'unset', pointer: `${list}/0` },
      ]);
      const hosts = hostsOf(apply(baseData(), ops));
      expect(hosts).toEqual(['h1']);
    });

    it('removing the same row twice counts once', () => {
      const drafts = removeDatabase(removeDatabase(EMPTY_DRAFTS, list, 1), list, 1);
      expect(reportDrafts(view(baseData()), drafts).ops).toHaveLength(1);
    });

    it('combines edit, removal and add into ops that yield the intended document', () => {
      let drafts = setValue(EMPTY_DRAFTS, `${list}/1/host`, 'edited');
      drafts = removeDatabase(drafts, list, 0);
      drafts = addDatabase(drafts, list);
      drafts = editAddedDatabase(drafts, list, 1, 'host', 'fresh');
      const { ops, changes } = reportDrafts(view(baseData()), drafts);
      expect(changes).toBe(3);
      const hosts = hostsOf(apply(baseData(), ops));
      expect(hosts).toEqual(['edited', 'h2', 'fresh']);
    });

    it('drops edits and secrets under a row that is being removed', () => {
      let drafts = setValue(EMPTY_DRAFTS, `${list}/0/host`, 'ignored');
      drafts = setSecret(drafts, `${list}/0/password`, { kind: 'replace', value: 'x' });
      drafts = removeDatabase(drafts, list, 0);
      expect(reportDrafts(view(baseData()), drafts).ops).toEqual([{ op: 'unset', pointer: `${list}/0` }]);
    });

    it('removes the last row and adds a new one into the same list', () => {
      const data = { devops: { staging: { database: [dbRow('only')] } } };
      let drafts = removeDatabase(EMPTY_DRAFTS, list, 0);
      drafts = addDatabase(drafts, list);
      drafts = editAddedDatabase(drafts, list, 1, 'host', 'next');
      const hosts = hostsOf(apply(data, reportDrafts(view(data), drafts).ops));
      expect(hosts).toEqual(['next']);
    });

    it('creates a missing list before appending to it', () => {
      const data = { devops: { staging: {} } };
      const drafts = addDatabase(EMPTY_DRAFTS, list);
      const { ops } = reportDrafts(view(data), drafts);
      expect(ops[0]).toEqual({ op: 'set', pointer: list, value: [] });
      expect(ops[1]?.pointer).toBe(`${list}/-`);
      expect(hostsOf(apply(data, ops))).toHaveLength(1);
    });
  });

  describe('missing parents', () => {
    it('creates the nearest missing ancestor in the first op', () => {
      const data = { devops: {} };
      const { ops } = reportDrafts(view(data), setValue(EMPTY_DRAFTS, '/devops/staging/ssh/host', 'h'));
      expect(ops).toEqual([{ op: 'set', pointer: '/devops/staging', value: { ssh: { host: 'h' } } }]);
      expect(apply(data, ops)).toEqual({ devops: { staging: { ssh: { host: 'h' } } } });
    });

    it('does not re-create the parent for a second edit under it', () => {
      const data = { devops: {} };
      let drafts = setValue(EMPTY_DRAFTS, '/devops/staging/ssh/host', 'h');
      drafts = setValue(drafts, '/devops/staging/ssh/user', 'u');
      const { ops } = reportDrafts(view(data), drafts);
      expect(ops).toHaveLength(2);
      expect(apply(data, ops)).toEqual({ devops: { staging: { ssh: { host: 'h', user: 'u' } } } });
    });
  });

  describe('a database key that is not a list', () => {
    it('refuses the add instead of overwriting what the file keeps there', () => {
      const data = { devops: { staging: { database: 'managed elsewhere' } } };
      const drafts = addDatabase(EMPTY_DRAFTS, '/devops/staging/database');
      const report = reportDrafts(view(data), drafts);
      expect(report.ops).toEqual([]);
      expect(report.problems['/devops/staging/database']).toMatch(/not a list/);
      expect(report.changes).toBe(1);
    });
  });
});
