/**
 * The editor's pure model: the working copy is the loaded document with the op journal applied,
 * with the semantics `cred local patch` applies on disk, so what is drawn is what a save writes.
 */
import { describe, expect, it } from 'vitest';

import { applyOps, coerce, editProblem, opsFor, productionAt, record, searchHits } from '../src/renderer/credentials/document.js';

const DOC = {
  a: { $secrets: ['pw'], pw: { secret: true, set: true, marked: true }, host: 'h.test' },
  list: ['x', 'y'],
  prod: { $production: true, inner: { url: 'https://p.test' } },
};

describe('applyOps', () => {
  it('sets, creating missing parents, unsets, appends and moves without touching the input', () => {
    const out = applyOps(DOC, [
      { op: 'set', pointer: '/new/deep/key', value: 1 },
      { op: 'unset', pointer: '/a/host' },
      { op: 'set', pointer: '/list/-', value: 'z' },
      { op: 'move', from: '/a/pw', pointer: '/a/password' },
    ]);
    expect(out['new']).toEqual({ deep: { key: 1 } });
    expect(out['a']).toEqual({ $secrets: ['pw'], password: { secret: true, set: true, marked: true } });
    expect(out['list']).toEqual(['x', 'y', 'z']);
    expect(DOC.a.host).toBe('h.test');
  });

  it('removes list items by index, shifting the rest', () => {
    expect(applyOps(DOC, [{ op: 'unset', pointer: '/list/0' }])['list']).toEqual(['y']);
  });
});

describe('record', () => {
  it('folds consecutive sets of one pointer into the last, and keeps everything else', () => {
    const ops = record([], { op: 'set', pointer: '/a', value: '1' }, { op: 'set', pointer: '/a', value: '12' });
    expect(ops).toEqual([{ op: 'set', pointer: '/a', value: '12' }]);
    expect(record(ops, { op: 'unset', pointer: '/a' })).toHaveLength(2);
  });
});

describe('opsFor', () => {
  it('renames with a move and keeps $secrets in step', () => {
    expect(opsFor(DOC, { kind: 'rename', path: ['a', 'pw'], to: 'password' })).toEqual([
      { op: 'move', from: '/a/pw', pointer: '/a/password' },
      { op: 'set', pointer: '/a/$secrets', value: ['password'] },
    ]);
  });

  it('drops a removed key from $secrets, unsetting the list when it empties', () => {
    expect(opsFor(DOC, { kind: 'remove', path: ['a', 'pw'] })).toEqual([
      { op: 'unset', pointer: '/a/pw' },
      { op: 'unset', pointer: '/a/$secrets' },
    ]);
  });

  it('appends to a list with "-" and escapes keys holding / and ~', () => {
    expect(opsFor(DOC, { kind: 'add', parent: ['list'], key: null, value: 'z' })).toEqual([{ op: 'set', pointer: '/list/-', value: 'z' }]);
    expect(opsFor(DOC, { kind: 'add', parent: [], key: 'a/b~c', value: '' })).toEqual([{ op: 'set', pointer: '/a~1b~0c', value: '' }]);
  });

  it('marks, unmarks and toggles production', () => {
    expect(opsFor(DOC, { kind: 'secret', path: ['a', 'host'], marked: true })).toEqual([
      { op: 'set', pointer: '/a/$secrets', value: ['host', 'pw'] },
    ]);
    expect(opsFor(DOC, { kind: 'production', path: ['prod'], on: false })).toEqual([{ op: 'unset', pointer: '/prod/$production' }]);
  });
});

describe('editProblem', () => {
  it('refuses empty, reserved and duplicate names', () => {
    expect(editProblem(DOC, { kind: 'add', parent: ['a'], key: ' ', value: '' })).toMatch(/required/);
    expect(editProblem(DOC, { kind: 'add', parent: ['a'], key: '$x', value: '' })).toMatch(/reserved/);
    expect(editProblem(DOC, { kind: 'rename', path: ['a', 'pw'], to: 'host' })).toMatch(/already exists/);
    expect(editProblem(DOC, { kind: 'rename', path: ['a', 'pw'], to: 'pass' })).toBeNull();
  });
});

describe('productionAt and searchHits', () => {
  it('tells an own production flag from an inherited one', () => {
    expect(productionAt(DOC, ['prod'])).toEqual({ own: true, inherited: false });
    expect(productionAt(DOC, ['prod', 'inner'])).toEqual({ own: false, inherited: true });
    expect(productionAt(DOC, ['a'])).toEqual({ own: false, inherited: false });
  });

  it('matches keys and visible values with their ancestors, never hidden values or reserved keys', () => {
    expect([...(searchHits(DOC, 'p.test') ?? [])].sort()).toEqual(['/prod', '/prod/inner', '/prod/inner/url']);
    expect(searchHits(DOC, 'secret')?.size).toBe(0);
    expect(searchHits(DOC, '$production')?.size).toBe(0);
    expect(searchHits(DOC, '  ')).toBeNull();
  });
});

describe('coerce', () => {
  it('keeps a number a number and flags text that is not one', () => {
    expect(coerce('10', 5)).toEqual({ value: 10, problem: null });
    expect(coerce('ten', 5).problem).toBe('Must be a number');
    expect(coerce('ten', 'x')).toEqual({ value: 'ten', problem: null });
  });
});
