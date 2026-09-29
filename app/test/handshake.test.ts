/**
 * The compat handshake, both ways.
 *
 * ADR-0011's rule is that a client which does not understand the store "degrades to
 * read-only and says so". These tests assert both halves: the verdict is read from the
 * framework's own `may_write`, and the incompatible case is a *finding* (exit 1) that
 * still produces a usable answer rather than an error state.
 */

import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

import { describe, expect, it } from 'vitest';

import { APP_STORE_SCHEMAS, performHandshake, writeDeclarationFile } from '../src/cli/declaration.js';

const FAKE = fileURLToPath(new URL('./fixtures/fake-devteam.mjs', import.meta.url));

function handshake(scenario: string) {
  return performHandshake({ binary: FAKE, env: { FAKE_DEVTEAM_SCENARIO: scenario } });
}

describe('the declaration is the app’s own constant', () => {
  it('names every shape `store_schemas()` declares', () => {
    // Silence is unsupported (`compat.unsupported_by`), so a missing name is not neutral.
    expect(Object.keys(APP_STORE_SCHEMAS).sort()).toEqual([
      'bind_manifest',
      'credentials',
      'project',
      'project_layout',
      'registry',
    ]);
  });

  it('is frozen, so nothing can derive it from a store at runtime', () => {
    expect(Object.isFrozen(APP_STORE_SCHEMAS)).toBe(true);
    expect(Object.values(APP_STORE_SCHEMAS).every((value) => Number.isInteger(value))).toBe(true);
  });

  it('writes a declaration file the CLI’s own parser would accept', async () => {
    const dir = await mkdtemp(join(tmpdir(), 'devteam-app-decl-'));
    const path = await writeDeclarationFile(dir);
    // Removed, not left behind: this file used to leak one directory per run.
    const parsed = JSON.parse(await readFile(path, 'utf8')) as Record<string, unknown>;
    expect(parsed).toEqual(APP_STORE_SCHEMAS);
    // `compat.parse_client_schemas` rejects a non-integer value for a present key.
    expect(Object.values(parsed).every((value) => typeof value === 'number' && Number.isInteger(value))).toBe(true);
    await rm(dir, { recursive: true, force: true });
  });
});

describe('compatible', () => {
  it('reports may_write true and echoes the shapes', async () => {
    const view = await handshake('compat-compatible');
    expect(view.state).toBe('answered');
    if (view.state !== 'answered') throw new Error('unreachable');
    expect(view.mayWrite).toBe(true);
    expect(view.unsupported).toEqual({});
    expect(view.clientSchemas).toEqual(APP_STORE_SCHEMAS);
    expect(view.jsonContract).toBe(1);
  });
});

describe('behind', () => {
  it('treats the exit-1 answer as a verdict, not a failure, and stays read-only', async () => {
    const view = await handshake('compat-behind');
    expect(view.state).toBe('answered');
    if (view.state !== 'answered') throw new Error('unreachable');
    expect(view.mayWrite).toBe(false);
    expect(view.unsupported['project_layout']).toEqual({ store: 9, client: 2 });
    expect(view.summary).toContain('read-only');
    expect(view.summary).toContain('project_layout');
  });

  it('does not infer the verdict from `unsupported` when no boolean was returned', async () => {
    const view = await handshake('compat-no-verdict');
    expect(view.state).toBe('unknown');
    if (view.state !== 'unknown') throw new Error('unreachable');
    expect(view.detail).toContain('may_write');
  });
});

describe('when the handshake cannot be completed', () => {
  it('degrades to read-only on a missing binary', async () => {
    const view = await performHandshake({ binary: join(tmpdir(), 'no-devteam-here') });
    expect(view.state).toBe('unknown');
    if (view.state !== 'unknown') throw new Error('unreachable');
    expect(view.summary).toContain('read-only');
  });

  it('degrades to read-only on a non-conforming answer', async () => {
    const view = await handshake('two-documents');
    expect(view.state).toBe('unknown');
    if (view.state !== 'unknown') throw new Error('unreachable');
    expect(view.detail).toContain('one JSON document');
  });

  it('degrades to read-only when the CLI reports an error', async () => {
    const view = await handshake('environment');
    expect(view.state).toBe('unknown');
    if (view.state !== 'unknown') throw new Error('unreachable');
    expect(view.detail).toContain('no active version');
  });
});
