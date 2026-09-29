/**
 * The app's own settings file: one key, and a reason for it.
 *
 * `cliPath` is the first step of the resolution order in `cli/resolve.ts` — the user's
 * explicit answer to "which `devteam`?". Nothing else belongs here yet: preferences are
 * the CLI's business (`devteam prefs`, resolved into `.dev-team-agents/resolved/
 * preferences.json`), and a second store for them in the app would be the drift
 * ADR-0011 forbids.
 *
 * Read-only in this slice: the file is never written. A user sets it by hand, or uses
 * `DEVTEAM_CLI_PATH`, until the write path exists.
 */

import { readFile } from 'node:fs/promises';
import { join } from 'node:path';

export const SETTINGS_FILE_NAME = 'settings.json';

export interface AppSettings {
  readonly cliPath: string | undefined;
  /** Where the file was looked for, so the UI can tell the user what to edit. */
  readonly path: string;
  /** Set when a file exists but could not be used. Reported, never silently ignored. */
  readonly problem: string | undefined;
}

export async function readSettings(userDataDir: string): Promise<AppSettings> {
  const path = join(userDataDir, SETTINGS_FILE_NAME);
  let raw: string;
  try {
    raw = await readFile(path, 'utf8');
  } catch (error) {
    const code = (error as NodeJS.ErrnoException).code;
    return {
      cliPath: undefined,
      path,
      problem: code === 'ENOENT' ? undefined : `could not be read: ${String(error)}`,
    };
  }
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch (error) {
    return { cliPath: undefined, path, problem: `is not valid JSON: ${String(error)}` };
  }
  if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) {
    return { cliPath: undefined, path, problem: 'is not a JSON object' };
  }
  const value = (parsed as Record<string, unknown>)['cliPath'];
  if (value === undefined) return { cliPath: undefined, path, problem: undefined };
  if (typeof value !== 'string' || value.trim() === '') {
    return { cliPath: undefined, path, problem: '`cliPath` is not a non-empty string' };
  }
  return { cliPath: value.trim(), path, problem: undefined };
}
