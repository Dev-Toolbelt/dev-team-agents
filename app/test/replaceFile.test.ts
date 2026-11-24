/**
 * `replaceFile`'s rename retry: Windows reports EPERM/EACCES/EBUSY while another process
 * holds the destination open, and the hold is brief.
 */

import { mkdtemp, readdir, readFile, rename as fsRename, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

import { describe, expect, it, onTestFinished } from 'vitest';

import { replaceFile } from '../src/cli/replaceFile.js';

async function scratch(): Promise<string> {
  const dir = await mkdtemp(join(tmpdir(), 'devteam-app-replace-'));
  onTestFinished(async () => {
    await rm(dir, { recursive: true, force: true });
  });
  return dir;
}

function failing(code: string, times: number): { rename: (from: string, to: string) => Promise<void>; calls: () => number } {
  let calls = 0;
  return {
    rename: async (from, to) => {
      calls += 1;
      if (calls <= times) throw Object.assign(new Error(`${code}: rename`), { code });
      await fsRename(from, to);
    },
    calls: () => calls,
  };
}

const noSleep = async (): Promise<void> => {};

describe('replaceFile', () => {
  it.each(['EPERM', 'EACCES', 'EBUSY'])('retries a %s rename on Windows until it succeeds', async (code) => {
    const dir = await scratch();
    const target = join(dir, 'file.json');
    const fake = failing(code, 3);

    await replaceFile(target, 'new\n', { platform: 'win32', rename: fake.rename, sleep: noSleep });

    expect(fake.calls()).toBe(4);
    expect(await readFile(target, 'utf8')).toBe('new\n');
    expect(await readdir(dir)).toEqual(['file.json']);
  });

  it('gives up after the last retry, rethrows and removes the temp file', async () => {
    const dir = await scratch();
    const fake = failing('EPERM', Number.POSITIVE_INFINITY);

    await expect(
      replaceFile(join(dir, 'file.json'), 'new\n', { platform: 'win32', rename: fake.rename, sleep: noSleep }),
    ).rejects.toMatchObject({ code: 'EPERM' });

    expect(fake.calls()).toBe(7);
    expect(await readdir(dir)).toEqual([]);
  });

  it('does not retry outside Windows', async () => {
    const dir = await scratch();
    const fake = failing('EPERM', 1);

    await expect(
      replaceFile(join(dir, 'file.json'), 'new\n', { platform: 'linux', rename: fake.rename, sleep: noSleep }),
    ).rejects.toMatchObject({ code: 'EPERM' });

    expect(fake.calls()).toBe(1);
  });

  it('does not retry an error that is not a sharing violation', async () => {
    const dir = await scratch();
    const fake = failing('ENOENT', 1);

    await expect(
      replaceFile(join(dir, 'file.json'), 'new\n', { platform: 'win32', rename: fake.rename, sleep: noSleep }),
    ).rejects.toMatchObject({ code: 'ENOENT' });

    expect(fake.calls()).toBe(1);
  });
});
