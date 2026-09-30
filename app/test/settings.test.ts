/**
 * The app's own settings file, and the one load-bearing round trip: a `problem` read
 * here must survive into `EnvironmentReport.settings.problem`, because that is the only
 * thing that puts the UI banner up. `ipc.ts` discarded it before this round — silently
 * returning `problem: undefined`-shaped success — so the round-trip test at the bottom
 * is the one that actually protects the fix, not just the read function in isolation.
 */

import { chmod, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { SETTINGS_FILE_NAME, readSettings, writeOpenAtLogin, writeProjectName } from '../src/main/settings.js';

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

describe('readSettings — projectNames degrades to empty rather than a problem or a throw', () => {
  it('reports no names when the file does not exist', async () => {
    const result = await readSettings(dir);
    expect(result.projectNames).toEqual({});
  });

  it('reports no names, and no problem, when projectNames is absent from an otherwise valid file', async () => {
    await writeFile(join(dir, SETTINGS_FILE_NAME), JSON.stringify({ cliPath: '/usr/local/bin/devteam' }), 'utf8');
    const result = await readSettings(dir);
    expect(result.projectNames).toEqual({});
    expect(result.problem).toBeUndefined();
  });

  it('reads a valid projectNames map alongside a valid cliPath', async () => {
    await writeFile(
      join(dir, SETTINGS_FILE_NAME),
      JSON.stringify({ cliPath: '/usr/local/bin/devteam', projectNames: { 'proj-1': 'My Project' } }),
      'utf8',
    );
    const result = await readSettings(dir);
    expect(result.projectNames).toEqual({ 'proj-1': 'My Project' });
    expect(result.cliPath).toBe('/usr/local/bin/devteam');
  });

  it('drops non-string and blank entries but keeps the valid ones, without raising a problem', async () => {
    await writeFile(
      join(dir, SETTINGS_FILE_NAME),
      JSON.stringify({ projectNames: { good: 'Kept', blank: '   ', wrongType: 42 } }),
      'utf8',
    );
    const result = await readSettings(dir);
    expect(result.projectNames).toEqual({ good: 'Kept' });
    expect(result.problem).toBeUndefined();
  });

  it('degrades to no names, never throws, when projectNames itself is not an object', async () => {
    await writeFile(join(dir, SETTINGS_FILE_NAME), JSON.stringify({ projectNames: 'not an object' }), 'utf8');
    await expect(readSettings(dir)).resolves.toMatchObject({ projectNames: {} });
  });

  it('a malformed cliPath does not blank out otherwise-valid projectNames', async () => {
    await writeFile(
      join(dir, SETTINGS_FILE_NAME),
      JSON.stringify({ cliPath: 42, projectNames: { 'proj-1': 'Kept anyway' } }),
      'utf8',
    );
    const result = await readSettings(dir);
    expect(result.cliPath).toBeUndefined();
    expect(result.problem).toBe('`cliPath` is not a non-empty string');
    expect(result.projectNames).toEqual({ 'proj-1': 'Kept anyway' });
  });
});

describe('writeProjectName', () => {
  it('creates the file when none exists, and readSettings sees the write', async () => {
    await writeProjectName(dir, 'proj-1', 'My Project');
    const result = await readSettings(dir);
    expect(result.projectNames).toEqual({ 'proj-1': 'My Project' });
  });

  it('trims the stored name', async () => {
    await writeProjectName(dir, 'proj-1', '  My Project  ');
    expect((await readSettings(dir)).projectNames).toEqual({ 'proj-1': 'My Project' });
  });

  it('is a no-op for a blank name — never stores an empty string', async () => {
    await writeProjectName(dir, 'proj-1', '   ');
    const result = await readSettings(dir);
    expect(result.projectNames).toEqual({});
    // No file at all was created for a no-op write.
    await expect(readFile(join(dir, SETTINGS_FILE_NAME), 'utf8')).rejects.toThrow();
  });

  it('preserves an existing cliPath, and merges into an existing projectNames map', async () => {
    await writeFile(
      join(dir, SETTINGS_FILE_NAME),
      JSON.stringify({ cliPath: '/usr/local/bin/devteam', projectNames: { 'proj-1': 'First' } }),
      'utf8',
    );
    await writeProjectName(dir, 'proj-2', 'Second');
    const result = await readSettings(dir);
    expect(result.cliPath).toBe('/usr/local/bin/devteam');
    expect(result.projectNames).toEqual({ 'proj-1': 'First', 'proj-2': 'Second' });
  });

  it('overwrites the name already stored for the same project_id', async () => {
    await writeProjectName(dir, 'proj-1', 'Old Name');
    await writeProjectName(dir, 'proj-1', 'New Name');
    expect((await readSettings(dir)).projectNames).toEqual({ 'proj-1': 'New Name' });
  });

  it('leaves no temp file behind after a successful write', async () => {
    await writeProjectName(dir, 'proj-1', 'My Project');
    const { readdir } = await import('node:fs/promises');
    const entries = await readdir(dir);
    expect(entries).toEqual([SETTINGS_FILE_NAME]);
  });
});

describe('writes never destroy a file that could not be read', () => {
  it('refuses to write over non-JSON content and leaves the file byte for byte as found', async () => {
    const path = join(dir, SETTINGS_FILE_NAME);
    await writeFile(path, '{ "cliPath": "/opt/devteam", oops', 'utf8');
    // Mutation: dropping the `current.problem` guard rebuilds the file from "no settings".
    await expect(writeProjectName(dir, 'p1', 'Name')).rejects.toThrow(/not overwriting/);
    await expect(writeOpenAtLogin(dir, true)).rejects.toThrow(/not overwriting/);
    expect(await readFile(path, 'utf8')).toBe('{ "cliPath": "/opt/devteam", oops');
  });

  it('refuses a top-level array and a hand-edited bad cliPath rather than dropping it', async () => {
    const path = join(dir, SETTINGS_FILE_NAME);
    await writeFile(path, '[1, 2]', 'utf8');
    await expect(writeProjectName(dir, 'p1', 'Name')).rejects.toThrow(/not overwriting/);
    await writeFile(path, JSON.stringify({ cliPath: 42, extra: true }), 'utf8');
    await expect(writeProjectName(dir, 'p1', 'Name')).rejects.toThrow(/not overwriting/);
    expect(JSON.parse(await readFile(path, 'utf8'))).toEqual({ cliPath: 42, extra: true });
  });

  it('still creates the file when it does not exist yet', async () => {
    await writeProjectName(dir, 'p1', 'Name');
    expect((await readSettings(dir)).projectNames).toEqual({ p1: 'Name' });
  });

  it('keeps writing after one write was refused', async () => {
    const path = join(dir, SETTINGS_FILE_NAME);
    await writeFile(path, 'garbage', 'utf8');
    await expect(writeProjectName(dir, 'p1', 'A')).rejects.toThrow();
    await writeFile(path, JSON.stringify({ cliPath: '/opt/devteam' }), 'utf8');
    await writeProjectName(dir, 'p1', 'A');
    expect(await readSettings(dir)).toMatchObject({ cliPath: '/opt/devteam', projectNames: { p1: 'A' } });
  });
});

describe('concurrent writes do not lose each other', () => {
  it('keeps every project name and the login choice when they are written at once', async () => {
    // Mutation: without the write chain each call reads the same empty file and the last
    // rename wins, leaving one field.
    await Promise.all([
      ...Array.from({ length: 12 }, (_unused, index) => writeProjectName(dir, `p${index}`, `Name ${index}`)),
      writeOpenAtLogin(dir, true),
    ]);
    const result = await readSettings(dir);
    expect(Object.keys(result.projectNames)).toHaveLength(12);
    expect(result.openAtLogin).toBe(true);
    expect(result.problem).toBeUndefined();
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
      trustedRenderer: { indexUrl: 'file:///app/index.html', devServerOrigin: null },
    });

    const environmentHandler = handlers.get(CHANNELS.environment);
    expect(environmentHandler).toBeDefined();
    const report = (await environmentHandler?.({ senderFrame: { url: 'file:///app/index.html', parent: null } })) as {
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
