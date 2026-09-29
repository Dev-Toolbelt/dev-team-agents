/**
 * The app's own settings file, and the one load-bearing round trip: a `problem` read
 * here must survive into `EnvironmentReport.settings.problem`, because that is the only
 * thing that puts the UI banner up. `ipc.ts` discarded it before this round — silently
 * returning `problem: undefined`-shaped success — so the round-trip test at the bottom
 * is the one that actually protects the fix, not just the read function in isolation.
 */

import { chmod, mkdtemp, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { SETTINGS_FILE_NAME, readSettings } from '../src/main/settings.js';

let dir: string;

beforeEach(async () => {
  dir = await mkdtemp(join(tmpdir(), 'devteam-app-settings-'));
});

afterEach(async () => {
  await rm(dir, { recursive: true, force: true });
});

describe('readSettings — missing file and empty-but-valid file are not problems', () => {
  it('reports no problem and no cliPath when the file does not exist', async () => {
    const result = await readSettings(dir);
    expect(result.problem).toBeUndefined();
    expect(result.cliPath).toBeUndefined();
    expect(result.path).toBe(join(dir, SETTINGS_FILE_NAME));
  });

  it('reports no problem when the file is valid JSON with no cliPath key', async () => {
    await writeFile(join(dir, SETTINGS_FILE_NAME), JSON.stringify({ other: 'value' }), 'utf8');
    const result = await readSettings(dir);
    expect(result.problem).toBeUndefined();
    expect(result.cliPath).toBeUndefined();
  });
});

describe('readSettings — every other case is a problem, and cliPath is withheld', () => {
  it('flags a file that cannot be read (permission denied) and withholds cliPath', async () => {
    const path = join(dir, SETTINGS_FILE_NAME);
    await writeFile(path, JSON.stringify({ cliPath: '/usr/local/bin/devteam' }), 'utf8');
    await chmod(path, 0o000);
    try {
      const result = await readSettings(dir);
      // On some CI runners (root, or certain filesystems) chmod 0 still permits reads;
      // only assert the invariant when the environment actually enforced it.
      if (result.problem !== undefined) {
        expect(result.cliPath).toBeUndefined();
        expect(result.problem).toContain('could not be read');
      }
    } finally {
      await chmod(path, 0o600);
    }
  });

  it('flags non-JSON content and withholds cliPath', async () => {
    await writeFile(join(dir, SETTINGS_FILE_NAME), 'not json at all {{{', 'utf8');
    const result = await readSettings(dir);
    expect(result.problem).toContain('not valid JSON');
    expect(result.cliPath).toBeUndefined();
  });

  it('flags a top-level array and withholds cliPath', async () => {
    await writeFile(join(dir, SETTINGS_FILE_NAME), JSON.stringify(['not', 'an', 'object']), 'utf8');
    const result = await readSettings(dir);
    expect(result.problem).toBe('is not a JSON object');
    expect(result.cliPath).toBeUndefined();
  });

  it('flags a null document and withholds cliPath', async () => {
    await writeFile(join(dir, SETTINGS_FILE_NAME), 'null', 'utf8');
    const result = await readSettings(dir);
    expect(result.problem).toBe('is not a JSON object');
    expect(result.cliPath).toBeUndefined();
  });

  it('flags a non-object, non-array JSON value (a bare string) and withholds cliPath', async () => {
    await writeFile(join(dir, SETTINGS_FILE_NAME), '"just a string"', 'utf8');
    const result = await readSettings(dir);
    expect(result.problem).toBe('is not a JSON object');
    expect(result.cliPath).toBeUndefined();
  });

  it('flags a cliPath that is not a string and withholds cliPath', async () => {
    await writeFile(join(dir, SETTINGS_FILE_NAME), JSON.stringify({ cliPath: 42 }), 'utf8');
    const result = await readSettings(dir);
    expect(result.problem).toBe('`cliPath` is not a non-empty string');
    expect(result.cliPath).toBeUndefined();
  });

  it('flags an empty-string cliPath and withholds cliPath', async () => {
    await writeFile(join(dir, SETTINGS_FILE_NAME), JSON.stringify({ cliPath: '' }), 'utf8');
    const result = await readSettings(dir);
    expect(result.problem).toBe('`cliPath` is not a non-empty string');
    expect(result.cliPath).toBeUndefined();
  });

  it('flags a whitespace-only cliPath and withholds cliPath', async () => {
    await writeFile(join(dir, SETTINGS_FILE_NAME), JSON.stringify({ cliPath: '   ' }), 'utf8');
    const result = await readSettings(dir);
    expect(result.problem).toBe('`cliPath` is not a non-empty string');
    expect(result.cliPath).toBeUndefined();
  });
});

describe('readSettings — cliPath and path shape', () => {
  it('trims a valid cliPath', async () => {
    await writeFile(
      join(dir, SETTINGS_FILE_NAME),
      JSON.stringify({ cliPath: '  /usr/local/bin/devteam  ' }),
      'utf8',
    );
    const result = await readSettings(dir);
    expect(result.cliPath).toBe('/usr/local/bin/devteam');
    expect(result.problem).toBeUndefined();
  });

  it('always reports path as <userDataDir>/settings.json, problem or not', async () => {
    const expected = join(dir, 'settings.json');
    expect((await readSettings(dir)).path).toBe(expected);
    await writeFile(join(dir, SETTINGS_FILE_NAME), 'garbage', 'utf8');
    expect((await readSettings(dir)).path).toBe(expected);
  });
});

describe('the round trip: a settings problem must survive into EnvironmentReport', () => {
  it('surfaces problem through registerIpc\'s environment handler, not silently dropped', async () => {
    vi.resetModules();
    const handlers = new Map<string, (...args: unknown[]) => unknown>();
    vi.doMock('electron', () => ({
      ipcMain: {
        handle: (channel: string, listener: (...args: unknown[]) => unknown) => {
          handlers.set(channel, listener);
        },
      },
    }));

    await writeFile(join(dir, SETTINGS_FILE_NAME), 'not json at all {{{', 'utf8');

    const { registerIpc } = await import('../src/main/ipc.js');
    const { CHANNELS } = await import('../src/shared/api.js');

    registerIpc({
      userDataDir: dir,
      appVersion: '0.0.0-test',
      electronVersion: '39.8.10',
      packaged: false,
    });

    const environmentHandler = handlers.get(CHANNELS.environment);
    expect(environmentHandler).toBeDefined();
    const report = (await environmentHandler?.()) as {
      settings: { problem: string | null; cliPathConfigured: boolean };
    };
    // Mutation: `problem: current.problem ?? null` replaced with `problem: null`, or the
    // `settings` field dropped from the returned object entirely, is exactly the defect
    // this test exists to catch — both leave every other assertion in this file green
    // while the UI never sees the banner.
    expect(report.settings.problem).toContain('not valid JSON');
    expect(report.settings.cliPathConfigured).toBe(false);

    vi.doUnmock('electron');
  });
});
