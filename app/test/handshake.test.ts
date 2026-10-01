/**
 * The compat handshake, both ways.
 *
 * ADR-0011's rule is that a client which does not understand the store "degrades to
 * read-only and says so". These tests assert both halves: the verdict is read from the
 * framework's own `may_write`, and the incompatible case is a *finding* (exit 1) that
 * still produces a usable answer rather than an error state.
 */

import { chmod, copyFile, lstat, mkdtemp, readdir, readFile, rm, stat, symlink, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

import { describe, expect, it, onTestFinished } from 'vitest';

import { APP_STORE_SCHEMAS, performHandshake, writeDeclarationFile, type Handshake } from '../src/cli/declaration.js';
import { readLauncherManifest, resolveFixtureBinary } from './fixtures/launcher-manifest.js';

const FAKE = fileURLToPath(new URL('./fixtures/fake-devteam.mjs', import.meta.url));

/**
 * `performHandshake` fixes its own `args` (`['compat', '--client', …]`, see
 * `declaration.ts`) and takes only `binary`, so unlike `invoke.test.ts` this helper
 * cannot route the fake CLI through `node` to make it executable on Windows — there is
 * no seam to insert an interpreter ahead of the subcommand. `FAKE` has to be `binary`
 * itself, and a `.mjs` script has no Windows-native way to run directly (see
 * `invoke.test.ts`'s `fakeCli()` comment for the general shape of the problem). On
 * Windows, `FAKE_BINARY` is instead the compiled launcher `launcher-global-setup.ts`
 * built — a real PE `spawn(..., { shell: false })` can execute — when one was built;
 * `launcherAvailable` says whether it was, and gates every `it.skipIf` below that isn't
 * skipped for the separate, POSIX-mode-bit reason this file's own comments name.
 */
const { binary: FAKE_BINARY, available: launcherAvailable } = resolveFixtureBinary(
  FAKE,
  readLauncherManifest()?.fakeDevteam,
);

/**
 * On POSIX this hands the scenario straight to `invokeDevteam`'s `env` option, which
 * reaches the fixture directly — no launcher involved, so nothing more is needed.
 *
 * On Windows it cannot: that `env` becomes the *launcher's own* process environment,
 * set by node's `spawn()` at `CreateProcess` time, and `launcher.c` only ever hands its
 * node child an environment through `_spawnv`'s plain inheritance (see that file's own
 * comment on why an explicit `_spawnve` block was tried and made things worse). The CI
 * evidence for these two tests — `expected 'unknown' to be 'answered'` — is exactly
 * what `fake-devteam.mjs` answers when `FAKE_DEVTEAM_SCENARIO` is unset (its default
 * `'ok'` scenario has no `may_write`), so whatever that inheritance carries, this
 * variable is not observably part of it. `resolve.test.ts`'s `plant()` already has a
 * working answer that needs no environment at all: a sibling `.scenario` file next to
 * the binary, which `launcher.c` reads at startup and applies with `_putenv_s`
 * *before* it ever calls `_spawnv`. This does the same — a fresh copy of the shared
 * launcher plus its own `.scenario` sibling — instead of routing the scenario through
 * `env`.
 */
async function handshake(scenario: string): Promise<Handshake> {
  if (process.platform !== 'win32') {
    return performHandshake({ binary: FAKE_BINARY, env: { FAKE_DEVTEAM_SCENARIO: scenario } });
  }
  // `skipOnWindowsWithoutLauncher` gates every caller of this branch, so `FAKE_BINARY`
  // is the built launcher whenever it actually runs.
  const dir = await mkdtemp(join(tmpdir(), 'devteam-app-handshake-'));
  onTestFinished(async () => {
    await rm(dir, { recursive: true, force: true });
  });
  const binary = join(dir, 'devteam.exe');
  await copyFile(FAKE_BINARY, binary);
  await writeFile(`${binary}.scenario`, scenario, 'utf8');
  return performHandshake({ binary });
}

const skipOnWindows = process.platform === 'win32';
const skipOnWindowsWithoutLauncher = skipOnWindows && !launcherAvailable;

describe('the declaration is the app’s own constant', () => {
  it('names every shape `store_schemas()` declares', () => {
    // Silence is unsupported (`compat.unsupported_by`), so a missing name is not neutral.
    expect(Object.keys(APP_STORE_SCHEMAS).sort()).toEqual([
      'bind_manifest',
      'credentials',
      'integration_settings',
      'integrations',
      'plugin_settings',
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
    // `onTestFinished` rather than a trailing `await rm(...)`: a failed assertion above
    // used to skip the cleanup and leak the directory — this runs regardless of outcome.
    onTestFinished(async () => {
      await rm(dir, { recursive: true, force: true });
    });
    const path = await writeDeclarationFile(dir);
    const parsed = JSON.parse(await readFile(path, 'utf8')) as Record<string, unknown>;
    expect(parsed).toEqual(APP_STORE_SCHEMAS);
    // `compat.parse_client_schemas` rejects a non-integer value for a present key.
    expect(Object.values(parsed).every((value) => typeof value === 'number' && Number.isInteger(value))).toBe(true);
  });

  it('replaces a pre-planted symlink instead of writing through it', async () => {
    const dir = await mkdtemp(join(tmpdir(), 'devteam-app-decl-'));
    const targetDir = await mkdtemp(join(tmpdir(), 'devteam-app-decl-target-'));
    onTestFinished(async () => {
      await rm(dir, { recursive: true, force: true });
      await rm(targetDir, { recursive: true, force: true });
    });
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
  });

  // Windows has no POSIX permission bits: `fs`'s `mode` there only ever reflects the
  // read-only DOS attribute, never a specific octal value, so `writeFile(…, { mode:
  // 0o600 })` cannot be observed back as `0o600` the way this asserts. Same platform
  // limit `resolve.ts`'s `worldWritableDirProblem` and `invoke.test.ts`'s
  // not-executable test are POSIX-only for.
  it.skipIf(skipOnWindows)('replaces a pre-planted world-writable file rather than keeping its mode', async () => {
    const dir = await mkdtemp(join(tmpdir(), 'devteam-app-decl-'));
    onTestFinished(async () => {
      await rm(dir, { recursive: true, force: true });
    });
    const declarationPath = join(dir, 'client-schemas.json');
    await writeFile(declarationPath, 'pre-existing', { mode: 0o666 });
    await chmod(declarationPath, 0o666); // belt-and-suspenders against an inherited umask

    await writeDeclarationFile(dir);

    const info = await stat(declarationPath);
    // 0o600, not the 0o666 the pre-planted file had — `{ mode }` on a `writeFile` to an
    // existing path is a no-op, so this only holds because the file was replaced, not
    // opened and overwritten.
    expect(info.mode & 0o777).toBe(0o600);
  });

  it('leaves no temp file behind after a successful write', async () => {
    const dir = await mkdtemp(join(tmpdir(), 'devteam-app-decl-'));
    onTestFinished(async () => {
      await rm(dir, { recursive: true, force: true });
    });
    await writeDeclarationFile(dir);
    expect(await readdir(dir)).toEqual(['client-schemas.json']);
  });
});

describe.skipIf(skipOnWindowsWithoutLauncher)('compatible', () => {
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

describe.skipIf(skipOnWindowsWithoutLauncher)('behind', () => {
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

  it.skipIf(skipOnWindowsWithoutLauncher)('degrades to read-only on a non-conforming answer', async () => {
    const view = await handshake('two-documents');
    expect(view.state).toBe('unknown');
    if (view.state !== 'unknown') throw new Error('unreachable');
    expect(view.detail).toContain('one JSON document');
  });

  it.skipIf(skipOnWindowsWithoutLauncher)('degrades to read-only when the CLI reports an error', async () => {
    const view = await handshake('environment');
    expect(view.state).toBe('unknown');
    if (view.state !== 'unknown') throw new Error('unreachable');
    expect(view.detail).toContain('no active version');
  });
});
