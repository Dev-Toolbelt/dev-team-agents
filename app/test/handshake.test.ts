/**
 * The compat handshake, both ways.
 *
 * ADR-0011's rule is that a client which does not understand the store "degrades to
 * read-only and says so". These tests assert both halves: the verdict is read from the
 * framework's own `may_write`, and the incompatible case is a *finding* (exit 1) that
 * still produces a usable answer rather than an error state.
 */

import { chmod, lstat, mkdtemp, readdir, readFile, rm, stat, symlink, writeFile } from 'node:fs/promises';
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

  it('replaces a pre-planted symlink instead of writing through it', async () => {
    const dir = await mkdtemp(join(tmpdir(), 'devteam-app-decl-'));
    const targetDir = await mkdtemp(join(tmpdir(), 'devteam-app-decl-target-'));
    const sensitive = join(targetDir, 'sensitive.json');
    await writeFile(sensitive, 'do not touch');
    const declarationPath = join(dir, 'client-schemas.json');
    await symlink(sensitive, declarationPath);

    const path = await writeDeclarationFile(dir);

    expect(path).toBe(declarationPath);
    // The symlink is gone — replaced by a regular file — not followed and truncated.
    const info = await lstat(path);
    expect(info.isSymbolicLink()).toBe(false);
    expect(JSON.parse(await readFile(path, 'utf8'))).toEqual(APP_STORE_SCHEMAS);
    // What the symlink pointed at is untouched.
    expect(await readFile(sensitive, 'utf8')).toBe('do not touch');

    await rm(dir, { recursive: true, force: true });
    await rm(targetDir, { recursive: true, force: true });
  });

  it('replaces a pre-planted world-writable file rather than keeping its mode', async () => {
    const dir = await mkdtemp(join(tmpdir(), 'devteam-app-decl-'));
    const declarationPath = join(dir, 'client-schemas.json');
    await writeFile(declarationPath, 'pre-existing', { mode: 0o666 });
    await chmod(declarationPath, 0o666); // belt-and-suspenders against an inherited umask

    await writeDeclarationFile(dir);

    const info = await stat(declarationPath);
    // 0o600, not the 0o666 the pre-planted file had — `{ mode }` on a `writeFile` to an
    // existing path is a no-op, so this only holds because the file was replaced, not
    // opened and overwritten.
    expect(info.mode & 0o777).toBe(0o600);

    await rm(dir, { recursive: true, force: true });
  });

  it('leaves no temp file behind after a successful write', async () => {
    const dir = await mkdtemp(join(tmpdir(), 'devteam-app-decl-'));
    await writeDeclarationFile(dir);
    expect(await readdir(dir)).toEqual(['client-schemas.json']);
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
