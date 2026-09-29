/**
 * The app's own settings file: `cliPath`, and now `projectNames`.
 *
 * `cliPath` is the first step of the resolution order in `cli/resolve.ts` — the user's
 * explicit answer to "which `devteam`?". `projectNames` is a different kind of field
 * entirely: nobody hand-edits it, and it is this app's own write, not the user's. Both
 * still belong here rather than in a second file, because there is exactly one file this
 * app owns on this machine — see `BindRequest.name` in `shared/api.ts` for why the name
 * cannot live anywhere the CLI would touch. Preferences remain the CLI's business
 * (`devteam prefs`, resolved into `.dev-team-agents/resolved/preferences.json`); a second
 * store for them here would be the drift ADR-0011 forbids.
 *
 * `cliPath` stays read-only in this slice: a user sets it by hand, or uses
 * `DEVTEAM_CLI_PATH`. `writeProjectName` is the one write this file gets, and it always
 * reads the current file first and keeps `cliPath` exactly as found — naming a project
 * must never be the thing that silently drops a hand-edited CLI path.
 */

import { randomBytes } from 'node:crypto';
import { readFile, rename, rm, writeFile } from 'node:fs/promises';
import { join } from 'node:path';

export const SETTINGS_FILE_NAME = 'settings.json';

const NO_NAMES: Readonly<Record<string, string>> = Object.freeze({});

export interface AppSettings {
  readonly cliPath: string | undefined;
  /** Where the file was looked for, so the UI can tell the user what to edit. */
  readonly path: string;
  /** Set when a file exists but could not be used. Reported, never silently ignored. */
  readonly problem: string | undefined;
  /**
   * This app's own names for bound projects, keyed by `project_id`.
   *
   * Read independently of `cliPath` and `problem` below: a malformed `cliPath` value must
   * not blank out otherwise-valid names, and a malformed `projectNames` value must not
   * manufacture a `problem` the user would try to fix by hand. Nobody edits this key
   * directly, so a malformed entry is this app's own past bug, not something to surface —
   * it degrades to "no names" instead.
   */
  readonly projectNames: Readonly<Record<string, string>>;
}

/** `NO_NAMES` when `value` is not a plain object; otherwise every string-valued,
 *  non-blank entry, trimmed. Anything else in the map is silently dropped. */
function readProjectNames(value: unknown): Readonly<Record<string, string>> {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) return NO_NAMES;
  const out: Record<string, string> = {};
  for (const [projectId, name] of Object.entries(value as Record<string, unknown>)) {
    if (typeof name === 'string' && name.trim() !== '') out[projectId] = name.trim();
  }
  return out;
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
      projectNames: NO_NAMES,
    };
  }
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch (error) {
    return { cliPath: undefined, path, problem: `is not valid JSON: ${String(error)}`, projectNames: NO_NAMES };
  }
  if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) {
    return { cliPath: undefined, path, problem: 'is not a JSON object', projectNames: NO_NAMES };
  }
  const record = parsed as Record<string, unknown>;
  // Read independently of the `cliPath` checks below, so a bad `cliPath` never costs the
  // caller its (possibly perfectly valid) project names.
  const projectNames = readProjectNames(record['projectNames']);

  const value = record['cliPath'];
  if (value === undefined) return { cliPath: undefined, path, problem: undefined, projectNames };
  if (typeof value !== 'string' || value.trim() === '') {
    return { cliPath: undefined, path, problem: '`cliPath` is not a non-empty string', projectNames };
  }
  return { cliPath: value.trim(), path, problem: undefined, projectNames };
}

/**
 * Store this app's own name for a bound project, keyed by `project_id`.
 *
 * Called only after `bindProject` in `main/ipc.ts` has already succeeded — a bind that
 * fails must not leave a name behind, and this function has no way to know whether the
 * bind it is being called for succeeded, so that ordering is entirely the caller's job.
 *
 * A blank name (after trimming) is treated as "nothing to store" and this is a no-op:
 * `projectNames()`'s own doc comment promises an absent entry falls back to the
 * directory's basename, and writing `""` would defeat that by giving every reader a name
 * to render instead of letting them fall back.
 *
 * Written the same way `cli/declaration.ts`'s `writeDeclarationFile` is: to a temp file in
 * the same directory, then renamed into place, so a pre-planted symlink at `path` is
 * replaced rather than written through.
 */
export async function writeProjectName(userDataDir: string, projectId: string, name: string): Promise<void> {
  const trimmed = name.trim();
  if (trimmed === '') return;

  const path = join(userDataDir, SETTINGS_FILE_NAME);
  // Re-reads rather than trusting an in-memory copy the caller might hold: this is the one
  // write this file gets, and reading fresh is what keeps a concurrently hand-edited
  // `cliPath` from being clobbered by a bind that happened to race it.
  const current = await readSettings(userDataDir);
  const payload: Record<string, unknown> = {};
  if (current.cliPath !== undefined) payload['cliPath'] = current.cliPath;
  payload['projectNames'] = { ...current.projectNames, [projectId]: trimmed };

  const tempPath = join(userDataDir, `.${SETTINGS_FILE_NAME}.${randomBytes(8).toString('hex')}.tmp`);
  await writeFile(tempPath, `${JSON.stringify(payload, null, 2)}\n`, {
    encoding: 'utf8',
    mode: 0o600,
    flag: 'wx',
  });
  try {
    await rename(tempPath, path);
  } catch (error) {
    await rm(tempPath, { force: true });
    throw error;
  }
}
