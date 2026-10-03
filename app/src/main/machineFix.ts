/**
 * "Fix" for a machine prerequisite (ADR-0030): runs the command `doctor --machine` named for a
 * finding the CLI marked `auto_fixable`, once, after the user's click.
 *
 * Three rules keep this from being a way to run arbitrary text:
 *  - the renderer names a finding by index; the command is the one the main process kept from
 *    the CLI's own answer, never a string the renderer sent;
 *  - the command is split into words and run with `spawn` and `shell: false`. A command that
 *    needs a shell (a pipe, a redirect, an expansion, a quote) is refused, not interpreted;
 *  - only findings the CLI flagged `auto_fixable` run. A provider's install command is shown
 *    with a copy button and never reaches this file.
 */
import { spawn } from 'node:child_process';

import type { MachineFixAnswer } from '../shared/api.js';

/** Anything a shell would act on. A fix that needs one of these is not a plain command. */
const SHELL_SYNTAX = /[|&;<>$`\\"'(){}*?!~#\n\r\0]/;
const MAX_WORDS = 12;
const TIMEOUT_MS = 10 * 60_000;
const OUTPUT_TAIL = 400;

/** The words of a plain command line, or `null` when it is not one. */
export function parseFixCommand(fix: string): string[] | null {
  const trimmed = fix.trim();
  if (trimmed === '' || SHELL_SYNTAX.test(trimmed)) return null;
  const words = trimmed.split(/\s+/);
  if (words.length > MAX_WORDS) return null;
  if (!/^[A-Za-z0-9][A-Za-z0-9._/@+-]*$/.test(words[0]!)) return null;
  return words;
}

/** Where Finder-launched apps cannot see tools: the usual Homebrew and user bin directories. */
export function fixEnvironment(env: NodeJS.ProcessEnv, platform: NodeJS.Platform): NodeJS.ProcessEnv {
  if (platform === 'win32') return env;
  const extra = ['/opt/homebrew/bin', '/usr/local/bin'];
  const home = env['HOME'];
  if (typeof home === 'string' && home !== '') extra.push(`${home}/.local/bin`);
  const current = (env['PATH'] ?? '').split(':').filter((entry) => entry !== '');
  return { ...env, PATH: [...current, ...extra.filter((entry) => !current.includes(entry))].join(':') };
}

export interface FixDeps {
  readonly platform: NodeJS.Platform;
  readonly env: NodeJS.ProcessEnv;
  /** The resolved `devteam` binary, for a fix that starts with `devteam`. */
  readonly cliPath: string | null;
  readonly run?: (command: string, args: readonly string[], env: NodeJS.ProcessEnv) => Promise<{ code: number | null; output: string }>;
}

export async function runMachineFix(deps: FixDeps, fix: string): Promise<MachineFixAnswer> {
  const words = parseFixCommand(fix);
  if (words === null) {
    return { ran: false, message: 'This fix is not a simple command, so it was not run. Copy it and run it yourself.' };
  }
  const [name, ...args] = words as [string, ...string[]];
  // `devteam …` means the CLI this app resolved, not whichever `devteam` the minimal PATH finds.
  const command = name === 'devteam' && deps.cliPath !== null ? deps.cliPath : name;
  const result = await (deps.run ?? runProcess)(command, args, fixEnvironment(deps.env, deps.platform));
  if (result.code === 0) return { ran: true, succeeded: true, message: 'Done.' };
  const tail = result.output.trim().slice(-OUTPUT_TAIL);
  return {
    ran: true,
    succeeded: false,
    message: tail === '' ? `The fix did not finish (exit ${String(result.code)}).` : `The fix did not finish (exit ${String(result.code)}): ${tail}`,
  };
}

function runProcess(command: string, args: readonly string[], env: NodeJS.ProcessEnv): Promise<{ code: number | null; output: string }> {
  return new Promise((resolve) => {
    let output = '';
    const child = spawn(command, [...args], { shell: false, env, stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true, timeout: TIMEOUT_MS });
    const keep = (chunk: Buffer) => {
      output = (output + chunk.toString('utf8')).slice(-OUTPUT_TAIL * 4);
    };
    child.stdout.on('data', keep);
    child.stderr.on('data', keep);
    child.once('error', (error) => resolve({ code: null, output: error.message }));
    child.once('close', (code) => resolve({ code, output }));
  });
}
