/**
 * Opens the first task in the user's own terminal (ADR-0030).
 *
 * The provider needs a real terminal: it is interactive, and the user should watch it work in
 * a window that is theirs, not in a pane this app owns. The main process therefore starts the
 * platform's terminal on a small script it writes, rather than spawning the provider itself.
 *
 *  - macOS: a `.command` script opened with `open -a Terminal`.
 *  - Windows: a `.cmd` script run by Windows Terminal (`wt`), or by `cmd` when `wt` is absent.
 *
 * **What goes into the script is quoted per shell** (`shared/shellQuote.ts`), never joined: the
 * argv comes from the CLI's launch map and the folder from the user's picker. An argument that
 * cannot be quoted for the shell that will read it (a `%` or `"` in a Windows batch file) makes
 * the whole launch refuse, and the screen offers "Copy command" instead. Spawning uses an
 * argument array and `shell: false`; the script path is the only value the terminal receives.
 *
 * Linux is not launched: there is no one terminal to open, so it is "Copy command".
 */
import { spawn } from 'node:child_process';
import { chmod, mkdtemp, writeFile } from 'node:fs/promises';
import { join } from 'node:path';

import type { LaunchFirstTaskAnswer } from '../shared/api.js';
import { joinQuoted, quoteCmd, quotePosix } from '../shared/shellQuote.js';

/** A provider's executable name: letters, digits, dot, underscore, dash. No path, no flag-looking name. */
const BINARY_NAME = /^[A-Za-z0-9][A-Za-z0-9._-]*$/;
const MAX_ARGS = 32;
const MAX_ARG_LENGTH = 4000;

/** Why an argv is not something to run, or `null`. The renderer never sees the argv; main does. */
export function launchArgvProblem(argv: unknown): string | null {
  if (!Array.isArray(argv) || argv.length === 0 || argv.length > MAX_ARGS) return 'the launch command is not a short, non-empty list';
  for (const entry of argv) {
    if (typeof entry !== 'string' || entry.length > MAX_ARG_LENGTH || entry.includes('\0')) return 'the launch command has an argument that cannot be passed safely';
  }
  if (!BINARY_NAME.test(argv[0] as string)) return 'the launch command does not start with a plain program name';
  return null;
}

/** Folders are quoted, but a leading `-` after `cd` would still be read as an option on some shells. */
function folderProblem(cwd: string): string | null {
  if (cwd === '' || cwd.includes('\0')) return 'the folder is not usable';
  return null;
}

/** macOS: the script Terminal runs. It removes itself first, so nothing is left behind. */
export function posixScript(cwd: string, argv: readonly string[]): string | null {
  const dir = quotePosix(cwd);
  const command = joinQuoted(argv, quotePosix);
  if (dir === null || command === null) return null;
  return [
    '#!/bin/sh',
    'rm -f -- "$0"',
    // A terminal opened from a Finder-launched app can have a short PATH: add the usual homes
    // of the provider binaries after the user's own entries.
    'PATH="$PATH:/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin"',
    'export PATH',
    `cd -- ${dir} || exit 1`,
    command,
    '',
  ].join('\n');
}

/** Windows: the batch file `wt`/`cmd` runs. `null` when any value has no safe `cmd.exe` quoting. */
export function batchScript(cwd: string, argv: readonly string[]): string | null {
  const dir = quoteCmd(cwd);
  const command = joinQuoted(argv, quoteCmd);
  if (dir === null || command === null) return null;
  return ['@echo off', `cd /d ${dir}`, command, ''].join('\r\n');
}

export interface Spawnable {
  readonly command: string;
  readonly args: readonly string[];
}

/** The terminals to try, in order, for a script at `scriptPath`. */
export function terminalCommands(platform: NodeJS.Platform, scriptPath: string): readonly Spawnable[] {
  if (platform === 'darwin') return [{ command: 'open', args: ['-a', 'Terminal', scriptPath] }];
  if (platform === 'win32') {
    const commands: Spawnable[] = [];
    // `;` separates commands on `wt`'s own command line and cannot be escaped in a path.
    if (!scriptPath.includes(';')) commands.push({ command: 'wt.exe', args: ['cmd.exe', '/k', scriptPath] });
    commands.push({ command: 'cmd.exe', args: ['/d', '/c', 'start', '', 'cmd.exe', '/k', scriptPath] });
    return commands;
  }
  return [];
}

export interface LauncherDeps {
  readonly platform: NodeJS.Platform;
  readonly tempDir: string;
  /** Resolves `true` when the process started, `false` when it could not be started at all. */
  readonly start: (spec: Spawnable) => Promise<boolean>;
  readonly writeScript?: (path: string, content: string) => Promise<void>;
  readonly makeDir?: (prefix: string) => Promise<string>;
}

export async function launchInTerminal(deps: LauncherDeps, cwd: string, argv: readonly string[]): Promise<LaunchFirstTaskAnswer> {
  const argvIssue = launchArgvProblem(argv);
  if (argvIssue !== null) return { launched: false, message: argvIssue };
  const folderIssue = folderProblem(cwd);
  if (folderIssue !== null) return { launched: false, message: folderIssue };
  if (deps.platform !== 'darwin' && deps.platform !== 'win32') {
    return { launched: false, message: 'Opening a terminal is not supported on this system.' };
  }

  const windows = deps.platform === 'win32';
  const script = windows ? batchScript(cwd, argv) : posixScript(cwd, argv);
  if (script === null) {
    return { launched: false, message: 'This folder or command has a character that cannot be passed to a terminal safely.' };
  }

  const makeDir = deps.makeDir ?? ((prefix: string) => mkdtemp(join(deps.tempDir, prefix)));
  const writeScript =
    deps.writeScript ??
    (async (path: string, content: string) => {
      await writeFile(path, content, { encoding: 'utf8', mode: 0o700, flag: 'wx' });
      if (!windows) await chmod(path, 0o700);
    });

  let scriptPath: string;
  try {
    const dir = await makeDir('devteam-first-task-');
    scriptPath = join(dir, windows ? 'first-task.cmd' : 'first-task.command');
    await writeScript(scriptPath, script);
  } catch (error) {
    return { launched: false, message: `The terminal script could not be written: ${error instanceof Error ? error.message : String(error)}` };
  }

  for (const spec of terminalCommands(deps.platform, scriptPath)) {
    if (await deps.start(spec)) return { launched: true };
  }
  return { launched: false, message: 'No terminal could be opened.' };
}

/** The real start: detached, no shell, no output; resolved when the process exists or could not. */
export function startDetached(spec: Spawnable): Promise<boolean> {
  return new Promise((resolve) => {
    try {
      const child = spawn(spec.command, [...spec.args], { shell: false, detached: true, stdio: 'ignore', windowsHide: false });
      child.once('error', () => resolve(false));
      child.once('spawn', () => {
        child.unref();
        resolve(true);
      });
    } catch {
      resolve(false);
    }
  });
}
