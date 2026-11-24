/**
 * Write a file by creating a fresh temp file beside it and renaming it into place.
 *
 * A direct `writeFile(path, …)` follows a symlink at `path` — a pre-planted one would be
 * written through and truncated — and `{ mode: 0o600 }` is a no-op when the file already
 * exists, so a pre-planted world-writable file would keep its permissions. The temp file
 * is created fresh (so its mode is honoured) and `rename()` replaces whatever is at
 * `path`, symlink or not, as a single directory-entry swap.
 *
 * On Windows that swap fails with `EPERM`, `EACCES` or `EBUSY` while another process
 * holds the destination open: an antivirus scan, or a `devteam` call still reading it.
 * The hold is brief, so the rename is retried with a short backoff before giving up.
 */

import { randomBytes } from 'node:crypto';
import { rename as fsRename, rm, writeFile } from 'node:fs/promises';
import { basename, dirname, join } from 'node:path';

/** Error codes Windows reports for a rename onto a file another process has open. */
const TRANSIENT_RENAME_CODES: ReadonlySet<string> = new Set(['EPERM', 'EACCES', 'EBUSY']);

/** Waits between attempts, in milliseconds; about one second in total. */
const RETRY_DELAYS_MS: readonly number[] = [20, 50, 100, 200, 300, 400];

export interface ReplaceFileOptions {
  /** Defaults to `process.platform`; the retry runs only on `win32`. */
  platform?: NodeJS.Platform;
  /** Defaults to `fs.promises.rename`; a seam for tests. */
  rename?: (from: string, to: string) => Promise<void>;
  /** Defaults to a timer; a seam for tests. */
  sleep?: (ms: number) => Promise<void>;
}

function errorCode(error: unknown): string | undefined {
  if (typeof error !== 'object' || error === null) return undefined;
  const code = (error as { code?: unknown }).code;
  return typeof code === 'string' ? code : undefined;
}

async function renameWithRetry(from: string, to: string, options: ReplaceFileOptions): Promise<void> {
  const rename = options.rename ?? fsRename;
  const retry = (options.platform ?? process.platform) === 'win32';
  const sleep = options.sleep ?? ((ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms)));
  for (let attempt = 0; ; attempt += 1) {
    try {
      await rename(from, to);
      return;
    } catch (error) {
      const code = errorCode(error);
      if (!retry || code === undefined || !TRANSIENT_RENAME_CODES.has(code) || attempt >= RETRY_DELAYS_MS.length) {
        throw error;
      }
      await sleep(RETRY_DELAYS_MS[attempt] as number);
    }
  }
}

/** Replace `path` with `content`, mode `0o600`, through a temp file and a rename. */
export async function replaceFile(path: string, content: string, options: ReplaceFileOptions = {}): Promise<void> {
  const tempPath = join(dirname(path), `.${basename(path)}.${randomBytes(8).toString('hex')}.tmp`);
  await writeFile(tempPath, content, {
    encoding: 'utf8',
    mode: 0o600,
    flag: 'wx', // exclusive create: refuse to follow anything already at the temp name too.
  });
  try {
    await renameWithRetry(tempPath, path, options);
  } catch (error) {
    await rm(tempPath, { force: true });
    throw error;
  }
}
