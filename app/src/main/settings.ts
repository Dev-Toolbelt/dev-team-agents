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

import { BOARD_SETTING_BOUNDS, type BoardSettings } from '../shared/api.js';
import { isEmptyFolders, normalizeProjectFolders, NO_FOLDERS, type ProjectFolders } from '../shared/projectFolders.js';

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
  /**
   * The user's choice to start this app at login (phase 2). Only the choice: whether the
   * OS actually registered it is read live from `app.getLoginItemSettings()`, because on an
   * unsigned macOS build the two can differ and the UI must say so.
   */
  readonly openAtLogin: boolean;
  /** The task board's thresholds (ADR-0018). App-local: never a `preferences.json` key. */
  readonly board: BoardSettings;
  /**
   * The Projects screen's folders (ADR-0021). App-local, like `projectNames`, and read the
   * same forgiving way: `normalizeProjectFolders` salvages what it can and never turns a
   * malformed value into a `problem`.
   */
  readonly projectFolders: ProjectFolders;
}

export const DEFAULT_BOARD_SETTINGS: BoardSettings = Object.freeze({
  staleAfterMinutes: BOARD_SETTING_BOUNDS.staleAfterMinutes.fallback,
  doneRetentionDays: BOARD_SETTING_BOUNDS.doneRetentionDays.fallback,
  directTodoTtlHours: BOARD_SETTING_BOUNDS.directTodoTtlHours.fallback,
});

function clampSetting(value: unknown, bounds: { readonly min: number; readonly max: number; readonly fallback: number }): number {
  if (typeof value !== 'number' || !Number.isFinite(value)) return bounds.fallback;
  return Math.min(bounds.max, Math.max(bounds.min, Math.round(value)));
}

/** Read-side normalisation: a missing, malformed or out-of-range value never blocks the app. */
export function readBoardSettings(record: Record<string, unknown>): BoardSettings {
  return {
    staleAfterMinutes: clampSetting(record['boardStaleAfterMinutes'], BOARD_SETTING_BOUNDS.staleAfterMinutes),
    doneRetentionDays: clampSetting(record['boardDoneRetentionDays'], BOARD_SETTING_BOUNDS.doneRetentionDays),
    directTodoTtlHours: clampSetting(record['boardDirectTodoTtlHours'], BOARD_SETTING_BOUNDS.directTodoTtlHours),
  };
}

/**
 * Write-side check: a value outside the bounds is refused with a sentence, not clamped —
 * the user typed it, and silently storing a different number would be a lie.
 */
export function boardSettingsProblem(value: unknown): string | null {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) return 'the board settings are not an object';
  const record = value as Record<string, unknown>;
  const checks = [
    ['staleAfterMinutes', 'the stale threshold (minutes)', BOARD_SETTING_BOUNDS.staleAfterMinutes],
    ['doneRetentionDays', 'the done retention (days)', BOARD_SETTING_BOUNDS.doneRetentionDays],
    ['directTodoTtlHours', 'the direct work to-do lifetime (hours)', BOARD_SETTING_BOUNDS.directTodoTtlHours],
  ] as const;
  for (const [key, label, bounds] of checks) {
    const n = record[key];
    if (typeof n !== 'number' || !Number.isInteger(n)) return `${label} must be a whole number`;
    if (n < bounds.min || n > bounds.max) return `${label} must be between ${bounds.min} and ${bounds.max}`;
  }
  return null;
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
      openAtLogin: false,
      board: DEFAULT_BOARD_SETTINGS,
      projectFolders: NO_FOLDERS,
    };
  }
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch (error) {
    return { cliPath: undefined, path, problem: `is not valid JSON: ${String(error)}`, projectNames: NO_NAMES, openAtLogin: false, board: DEFAULT_BOARD_SETTINGS, projectFolders: NO_FOLDERS };
  }
  if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) {
    return { cliPath: undefined, path, problem: 'is not a JSON object', projectNames: NO_NAMES, openAtLogin: false, board: DEFAULT_BOARD_SETTINGS, projectFolders: NO_FOLDERS };
  }
  const record = parsed as Record<string, unknown>;
  // Read independently of the `cliPath` checks below, so a bad `cliPath` never costs the
  // caller its (possibly perfectly valid) project names.
  const projectNames = readProjectNames(record['projectNames']);
  // Anything but a literal `true` is "not chosen": starting at login is opt-in.
  const openAtLogin = record['openAtLogin'] === true;
  const board = readBoardSettings(record);
  const projectFolders = normalizeProjectFolders(record['projectFolders']);

  const value = record['cliPath'];
  if (value === undefined) return { cliPath: undefined, path, problem: undefined, projectNames, openAtLogin, board, projectFolders };
  if (typeof value !== 'string' || value.trim() === '') {
    return { cliPath: undefined, path, problem: '`cliPath` is not a non-empty string', projectNames, openAtLogin, board, projectFolders };
  }
  return { cliPath: value.trim(), path, problem: undefined, projectNames, openAtLogin, board, projectFolders };
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

  await writeSettings(userDataDir, (current) => ({ projectNames: { ...current.projectNames, [projectId]: trimmed } }));
}

/** Record the user's start-at-login choice. The OS registration is `index.ts`'s job. */
export async function writeOpenAtLogin(userDataDir: string, enabled: boolean): Promise<void> {
  await writeSettings(userDataDir, () => ({ openAtLogin: enabled }));
}

/** Record the Projects screen's folders. The caller validates with `projectFoldersProblem` first. */
export async function writeProjectFolders(userDataDir: string, projectFolders: ProjectFolders): Promise<void> {
  await writeSettings(userDataDir, () => ({ projectFolders }));
}

/** Record the board's thresholds. The caller validates with `boardSettingsProblem` first. */
export async function writeBoardSettings(userDataDir: string, board: BoardSettings): Promise<void> {
  await writeSettings(userDataDir, () => ({ board }));
}

/**
 * Every write, one after another. The read-modify-write below is not atomic on its own:
 * two concurrent callers (a bind naming a project while the user flips start-at-login)
 * would both read the same file and the second rename would erase the first's field.
 * A module-level chain rather than a lock file because this process is the file's only
 * writer; the single-instance lock in `index.ts` is what makes that true.
 */
let writeChain: Promise<unknown> = Promise.resolve();

/**
 * The one writer, carrying every field forward.
 *
 * It used to be inlined in `writeProjectName`, rebuilding the file from `cliPath` and
 * `projectNames` alone — so the first field added beside them would have been erased by
 * the next bind. Re-reads rather than trusting an in-memory copy, which is what keeps a
 * concurrently hand-edited `cliPath` from being clobbered.
 *
 * **Refuses to write over a file it could not read.** A `settings.json` that is unreadable,
 * not JSON, or not an object was read as "no settings", and rebuilding from that would
 * replace whatever the user had — a hand-edited `cliPath` among it — with a file holding
 * one project name. The caller gets the reason instead; both callers already treat a failed
 * write as non-fatal.
 */
function writeSettings(
  userDataDir: string,
  patchFrom: (current: AppSettings) => Partial<Pick<AppSettings, 'projectNames' | 'openAtLogin' | 'board' | 'projectFolders'>>,
): Promise<void> {
  const run = writeChain.then(() => writeSettingsNow(userDataDir, patchFrom));
  // The chain continues past a failure; the failure itself still reaches this caller.
  writeChain = run.catch(() => undefined);
  return run;
}

async function writeSettingsNow(
  userDataDir: string,
  patchFrom: (current: AppSettings) => Partial<Pick<AppSettings, 'projectNames' | 'openAtLogin' | 'board' | 'projectFolders'>>,
): Promise<void> {
  const path = join(userDataDir, SETTINGS_FILE_NAME);
  const current = await readSettings(userDataDir);
  if (current.problem !== undefined) {
    throw new Error(`${path} ${current.problem}; not overwriting it`);
  }
  const patch = patchFrom(current);
  const payload: Record<string, unknown> = {};
  if (current.cliPath !== undefined) payload['cliPath'] = current.cliPath;
  payload['projectNames'] = patch.projectNames ?? current.projectNames;
  const openAtLogin = patch.openAtLogin ?? current.openAtLogin;
  if (openAtLogin) payload['openAtLogin'] = true;
  // Only a departure from the default is written, so a file that never customised the
  // board stays exactly as it was.
  const board = patch.board ?? current.board;
  if (board.staleAfterMinutes !== DEFAULT_BOARD_SETTINGS.staleAfterMinutes) payload['boardStaleAfterMinutes'] = board.staleAfterMinutes;
  if (board.doneRetentionDays !== DEFAULT_BOARD_SETTINGS.doneRetentionDays) payload['boardDoneRetentionDays'] = board.doneRetentionDays;
  if (board.directTodoTtlHours !== DEFAULT_BOARD_SETTINGS.directTodoTtlHours) payload['boardDirectTodoTtlHours'] = board.directTodoTtlHours;
  const projectFolders = patch.projectFolders ?? current.projectFolders;
  if (!isEmptyFolders(projectFolders)) payload['projectFolders'] = projectFolders;

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
