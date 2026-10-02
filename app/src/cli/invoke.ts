/**
 * Spawning `devteam`. The whole product is this file plus `parse.ts`; the UI renders
 * what they return.
 *
 * Rules held here, each of which is a way this layer could otherwise go wrong:
 *   - **no shell, ever.** `spawn(binary, args, { shell: false })`. Nothing the user
 *     types is ever interpolated into a command string, so there is no quoting bug to
 *     have. `shell` is passed explicitly rather than left to the default, because the
 *     default is the thing a future edit would change by accident.
 *   - **exit 1 is a result, not an error.** See `contract.ts`.
 *   - **a non-conforming response is reported.** Never an empty success.
 *   - **every invocation has a deadline** and says what timed out when it trips.
 *   - **`--json` is added here**, not by callers, so no operation can forget it.
 *   - **a secret goes through stdin, never argv.** `secretStdin` is written to the child's
 *     stdin and closed. It is never part of `command`, and any echo of it in the child's
 *     stdout/stderr is scrubbed before those are parsed, returned, or logged.
 *
 * Imports nothing from `electron`.
 */

import { spawn } from 'node:child_process';
import {
  OUTCOME_BY_EXIT,
  type CliResult,
  type CommandDescription,
  type ExitCode,
} from './contract.js';
import { launchCommand, lookupEnv } from './launch.js';
import { parseSingleDocument } from './parse.js';

/** Long enough for a cold `catalog` walk on a large store, short enough to notice. */
export const DEFAULT_TIMEOUT_MS = 20_000;

/**
 * Grace between SIGTERM and SIGKILL when a deadline trips.
 *
 * Injectable only so a test does not have to wait out a real two seconds: a test that
 * depends on a wall-clock window that wide passes on an idle machine and fails on a loaded
 * CI runner, which is a flake rather than a finding. Production callers leave it alone.
 */
export const KILL_GRACE_MS = 2_000;

/**
 * How long the pipes get to drain after the child has exited, before they are cut.
 *
 * `close` waits for every holder of the child's stdout and stderr, not only the child. A
 * grandchild that inherited the pipes (a hook, a daemonised helper) keeps them open long
 * after the CLI is gone, and a deadline kill does not reach it — so waiting for `close`
 * alone turned a timeout into a hang with no deadline at all. `exit` is the child's own
 * end; this is the time allowed for what it had already written to arrive.
 */
export const PIPE_GRACE_MS = 500;

/**
 * How much of each stream is kept. A `catalog` document on a very large store is the
 * biggest thing this app reads and is far below this; anything above it is a runaway, and
 * buffering a runaway in the main process's heap is a worse failure than reporting one.
 * The child is killed at the cap rather than allowed to keep writing into a full pipe.
 */
export const MAX_STREAM_BYTES = 32 * 1024 * 1024;

export interface InvokeOptions {
  /** Absolute path to the `devteam` executable. Resolved by `resolve.ts`. */
  readonly binary: string;
  /** Subcommand and flags, as separate array entries. `--json` is added for you. */
  readonly args: readonly string[];
  readonly timeoutMs?: number;
  /** See `KILL_GRACE_MS`. Present for tests; production callers omit it. */
  readonly killGraceMs?: number;
  /** See `PIPE_GRACE_MS`. Present for tests; production callers omit it. */
  readonly pipeGraceMs?: number;
  readonly cwd?: string;
  /**
   * Extra environment for the child. Merged over a **minimal** inherited set rather
   * than over the whole of `process.env`: an Electron main process carries a large,
   * partly Electron-specific environment, and handing all of it to a python CLI is
   * both noise and a way for an unrelated variable to change the CLI's answer.
   */
  readonly env?: Readonly<Record<string, string>>;
  /**
   * Path to this client's schema declaration file, passed as `--client-schemas`.
   * Present on every invocation once the app has written it: ADR-0014's write gate
   * binds a client that declares, so declaring on every call — including read-only
   * ones — is what makes the gate real for this app the moment a write path lands.
   */
  readonly declarationFile?: string;
  /**
   * Opt in to being SIGTERMed by `terminateInFlight` when the app quits. Only for a
   * cancellable, long-running action whose script the CLI itself tears down on SIGTERM
   * (`plugin run`). Everything else — every write — is left to finish; see
   * `settleInFlight`.
   */
  readonly cancelOnQuit?: boolean;
  /**
   * A secret (an integration API token) for the child's stdin. Written, then stdin is
   * closed. Never put a secret in `args`: argv is visible in the process table and in
   * `command.display`. The value is redacted from everything this function returns; do
   * not copy it into a log line, a `Problem`, or anything bound for the renderer.
   * When absent, the child's stdin is `ignore`, exactly as before.
   */
  readonly secretStdin?: string;
  /**
   * Further values to redact from everything this function returns, in addition to
   * `secretStdin` as a whole. For a structured stdin payload (ADR-0024's patch ops) where a
   * single secret inside it could be echoed on its own in an error message.
   */
  readonly redactAlso?: readonly string[];
  /**
   * A secret now and a second one later, for the one command that reads stdin in two
   * stages with a wait the user spends elsewhere (`auth login --signup`: the password,
   * then the emailed code). `first` is written at once, stdin stays open, and `rest` —
   * settled by the caller when the user has the code — is written and closes it; `null`
   * closes it empty (cancelled). Both are redacted from everything returned, exactly like
   * `secretStdin`, which this replaces for that call.
   */
  readonly lateStdin?: { readonly first: string; readonly rest: Promise<string | null> };
}

export const REDACTED = '[redacted]';
const MIN_REDACTABLE = 4;

/** Replace every occurrence of `secret` (raw and JSON-escaped) in `text`. */
export function redactSecret(text: string, secret: string | undefined): string {
  // A value this short would also match inside unrelated text and mangle the JSON around it.
  if (secret === undefined || secret.length < MIN_REDACTABLE) return text;
  const escaped = JSON.stringify(secret).slice(1, -1);
  let out = text.split(secret).join(REDACTED);
  if (escaped !== secret) out = out.split(escaped).join(REDACTED);
  return out;
}

/** Variables a python CLI legitimately needs. Everything else is dropped. */
const PASS_THROUGH_ENV = [
  'PATH',
  'HOME',
  'USER',
  'LOGNAME',
  'SHELL',
  'TMPDIR',
  'TEMP',
  'TMP',
  'LANG',
  'LC_ALL',
  'LC_CTYPE',
  'XDG_CONFIG_HOME',
  'XDG_DATA_HOME',
  'XDG_CACHE_HOME',
  'XDG_STATE_HOME',
  'APPDATA',
  'LOCALAPPDATA',
  'USERPROFILE',
  'SYSTEMROOT',
  'SYSTEMDRIVE',
  'WINDIR',
  'HOMEDRIVE',
  'HOMEPATH',
  'PATHEXT',
  'COMSPEC',
  'DEVTEAM_HOME',
  // The CLI's own children (`git`, and `gh` for the user's recorded commands) reach the
  // network and the user's credentials through these; without them a proxied or
  // agent-authenticated host fails in the app while the same command works in a terminal.
  'HTTP_PROXY',
  'http_proxy',
  'HTTPS_PROXY',
  'https_proxy',
  'NO_PROXY',
  'no_proxy',
  'SSH_AUTH_SOCK',
  'GH_TOKEN',
  'GITHUB_TOKEN',
  'GH_HOST',
] as const;

export function childEnvironment(
  parent: Readonly<Record<string, string | undefined>>,
  extra: Readonly<Record<string, string>> = {},
  platform: NodeJS.Platform = process.platform,
): Record<string, string> {
  const env: Record<string, string> = {};
  const seen = new Set<string>();
  for (const key of PASS_THROUGH_ENV) {
    // Windows env names are case-insensitive, so `http_proxy` and `HTTP_PROXY` are one
    // variable: look up the way the platform does, and emit it once.
    const folded = platform === 'win32' ? key.toLowerCase() : key;
    if (seen.has(folded)) continue;
    const value = lookupEnv(parent, key, platform);
    if (typeof value === 'string') {
      env[key] = value;
      seen.add(folded);
    }
  }
  // `PYTHONUNBUFFERED` so a killed child's partial stdout is not lost in a pipe
  // buffer — the timeout report is worth more when it can quote what did arrive.
  env['PYTHONUNBUFFERED'] = '1';
  return { ...env, ...extra };
}

function describe(binary: string, args: readonly string[]): CommandDescription {
  return {
    binary,
    args,
    // For messages only. Quoted so a path with a space reads correctly; this string
    // is never handed to a shell.
    display: [binary, ...args].map((part) => (/[\s"']/.test(part) ? JSON.stringify(part) : part)).join(' '),
  };
}

/** Documented iff it is one of `OUTCOME_BY_EXIT`'s own keys — see that object's comment. */
function isDocumentedExit(code: number): code is ExitCode {
  return Object.hasOwn(OUTCOME_BY_EXIT, code);
}

interface InFlight {
  readonly cancelOnQuit: boolean;
  /** Resolves when the child has ended, whichever way. */
  readonly ended: Promise<void>;
}

/** Children alive right now, so a quitting app can end or await them instead of orphaning them. */
const inFlight = new Map<ReturnType<typeof spawn>, InFlight>();

/**
 * SIGTERM the children that opted in with `cancelOnQuit`. Called on app quit: a plugin
 * action can run for up to an hour, and the CLI forwards SIGTERM to the script's process
 * group, so the script does not outlive the app that started it.
 *
 * Writes (`bind`, `upgrade`, `sync`, `prefs set`, ...) are deliberately not touched: killing
 * one mid-write is how a store ends up half-updated. They are awaited by `settleInFlight`.
 */
export function terminateInFlight(): void {
  for (const [child, entry] of inFlight) {
    if (entry.cancelOnQuit && child.exitCode === null && child.signalCode === null) child.kill('SIGTERM');
  }
}

/** True while a child that `terminateInFlight` would not cancel is still running. */
export function hasPendingWrites(): boolean {
  for (const entry of inFlight.values()) if (!entry.cancelOnQuit) return true;
  return false;
}

/**
 * Resolve once every non-cancellable child has ended, or after `timeoutMs`, whichever is
 * first. The bound keeps a wedged child (each has its own deadline anyway) from holding
 * the app open on quit.
 */
export async function settleInFlight(timeoutMs: number): Promise<void> {
  const pending = [...inFlight.values()].filter((entry) => !entry.cancelOnQuit).map((entry) => entry.ended);
  if (pending.length === 0) return;
  let timer: ReturnType<typeof setTimeout> | undefined;
  const deadline = new Promise<void>((resolve) => {
    timer = setTimeout(resolve, timeoutMs);
  });
  await Promise.race([Promise.all(pending).then(() => undefined), deadline]);
  clearTimeout(timer);
}

/**
 * Run `devteam <args> --json` once and classify the outcome.
 *
 * Resolves for every outcome; it does not throw. A caller that must branch has a
 * `result.outcome` to switch on, and TypeScript will not let it forget a case.
 */
export async function invokeDevteam(options: InvokeOptions): Promise<CliResult> {
  const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const killGraceMs = options.killGraceMs ?? KILL_GRACE_MS;
  const pipeGraceMs = options.pipeGraceMs ?? PIPE_GRACE_MS;
  const args = [...options.args, '--json'];
  if (options.declarationFile !== undefined) {
    args.unshift('--client-schemas', options.declarationFile);
  }
  const command = describe(options.binary, args);
  const startedAt = Date.now();

  let child: ReturnType<typeof spawn>;
  try {
    const env = childEnvironment(process.env, options.env ?? {});
    const launch = launchCommand(options.binary, args, env);
    child = spawn(launch.command, [...launch.args], {
      // Explicit: never a shell. See the file header.
      shell: false,
      stdio: [options.secretStdin !== undefined || options.lateStdin !== undefined ? 'pipe' : 'ignore', 'pipe', 'pipe'],
      ...(options.cwd !== undefined ? { cwd: options.cwd } : {}),
      env,
      windowsHide: true,
    });
  } catch (error) {
    // `spawn` normally reports failure through the `error` event, but it throws
    // synchronously for a few argument shapes. Both paths end in the same outcome.
    const err = error as NodeJS.ErrnoException;
    return {
      outcome: 'unavailable',
      reason: err.code === 'ENOENT' ? 'not-found' : 'spawn-failed',
      detail: `${err.code ?? 'spawn error'}: ${err.message}`,
      command,
      durationMs: Date.now() - startedAt,
    };
  }

  if (options.secretStdin !== undefined) {
    // The child may exit, or close stdin, before reading it all: EPIPE is expected then.
    // Swallowed; the exit code is the result, and no error text is surfaced.
    child.stdin?.on('error', () => undefined);
    child.stdin?.end(options.secretStdin, 'utf8');
  }

  const lateSecrets: string[] = [];
  if (options.lateStdin !== undefined) {
    const { first, rest } = options.lateStdin;
    lateSecrets.push(first);
    child.stdin?.on('error', () => undefined);
    child.stdin?.write(`${first}\n`, 'utf8');
    void rest.then(
      (value) => {
        if (value !== null) lateSecrets.push(value);
        child.stdin?.end(value === null ? undefined : `${value}\n`, 'utf8');
      },
      () => child.stdin?.end(),
    );
  }

  inFlight.set(child, {
    cancelOnQuit: options.cancelOnQuit === true,
    ended: new Promise<void>((resolve) => {
      child.once('close', () => resolve());
      child.once('error', () => resolve());
    }),
  });
  const stdoutChunks: Buffer[] = [];
  const stderrChunks: Buffer[] = [];
  let stdoutBytes = 0;
  let stderrBytes = 0;
  // A holder rather than a plain `let`: the assignment happens inside the listener below,
  // which TypeScript's control-flow analysis cannot see, so a `let` reads as `never` after
  // the `await`. Same reason `timedOutWith`'s narrowing is accidental rather than earned.
  const overflow: { which: 'stdout' | 'stderr' | null } = { which: null };
  // Capped, not unbounded: a child that never stops writing would otherwise grow the main
  // process's heap until it died, with no message. At the cap the child is killed and the
  // partial output is still reported, which is what makes the breach legible.
  const collect = (which: 'stdout' | 'stderr', chunk: Buffer): void => {
    if (overflow.which !== null) return;
    if (which === 'stdout') {
      stdoutBytes += chunk.length;
      stdoutChunks.push(chunk);
    } else {
      stderrBytes += chunk.length;
      stderrChunks.push(chunk);
    }
    if (stdoutBytes + stderrBytes <= MAX_STREAM_BYTES) return;
    overflow.which = which;
    child.kill('SIGKILL');
  };
  child.stdout?.on('data', (chunk: Buffer) => collect('stdout', chunk));
  child.stderr?.on('data', (chunk: Buffer) => collect('stderr', chunk));

  let timedOutWith: NodeJS.Signals | null = null;
  const deadline = setTimeout(() => {
    timedOutWith = 'SIGTERM';
    child.kill('SIGTERM');
    // A python process wedged in a lock wait does not always honour SIGTERM. The
    // second timer is what makes the deadline a deadline rather than a request.
    //
    // On Windows the escalation never fires, and nothing is lost by that: `kill` there is
    // `TerminateProcess`, which is immediate and cannot be caught or ignored, so the first
    // signal has already ended the process by the time this timer would run and the
    // `exitCode`/`signalCode` guard below short-circuits. The deadline is enforced on every
    // platform; only the two-step mechanism is POSIX-specific.
    const hard = setTimeout(() => {
      if (child.exitCode === null && child.signalCode === null) {
        timedOutWith = 'SIGKILL';
        child.kill('SIGKILL');
      }
    }, killGraceMs);
    hard.unref?.();
  }, timeoutMs);

  // Listeners rather than `events.once`: `once(child, 'close')` attaches its own `error`
  // listener that *rejects*, so a missing binary came back out of this function as an
  // unhandled rejection instead of the `unavailable` outcome below. Every settlement path
  // has to resolve, because this function's contract is that it does not throw.
  let exitCode: number | null = null;
  let spawnError: NodeJS.ErrnoException | null = null;
  try {
    const settled = await new Promise<{ code: number | null } | { error: NodeJS.ErrnoException }>((resolve) => {
      let done = false;
      const settle = (value: { code: number | null } | { error: NodeJS.ErrnoException }) => {
        if (done) return;
        done = true;
        resolve(value);
      };
      // On ENOENT node emits `error` and then `close`; the first one wins, which is the
      // one that carries the reason.
      child.once('error', (error: NodeJS.ErrnoException) => settle({ error }));
      child.once('close', (code) => settle({ code }));
      // `close` normally follows `exit` at once. When it does not, a descendant is holding
      // the pipes: report the child's own exit code and cut the pipes so their handles
      // are released instead of leaked for as long as the descendant lives.
      child.once('exit', (code) => {
        const cut = setTimeout(() => {
          settle({ code });
          child.stdout?.destroy();
          child.stderr?.destroy();
        }, pipeGraceMs);
        cut.unref?.();
        child.once('close', () => clearTimeout(cut));
      });
    });
    if ('error' in settled) spawnError = settled.error;
    else exitCode = settled.code;
  } finally {
    clearTimeout(deadline);
    inFlight.delete(child);
  }

  const durationMs = Date.now() - startedAt;
  const redactAll = (text: string): string =>
    [...(options.redactAlso ?? []), ...lateSecrets].reduce(redactSecret, redactSecret(text, options.secretStdin));
  const stdout = redactAll(Buffer.concat(stdoutChunks).toString('utf8'));
  const stderr = redactAll(Buffer.concat(stderrChunks).toString('utf8'));

  if (spawnError !== null) {
    // ENOENT is the first-run state a real user hits: no `devteam` where we looked.
    // EACCES is the one a developer hits: a file that exists and is not executable.
    const reason =
      spawnError.code === 'ENOENT'
        ? 'not-found'
        : spawnError.code === 'EACCES' || spawnError.code === 'EPERM'
          ? 'not-executable'
          : 'spawn-failed';
    return {
      outcome: 'unavailable',
      reason,
      detail: `${spawnError.code ?? 'spawn error'}: ${spawnError.message}`,
      command,
      durationMs,
    };
  }

  if (overflow.which !== null) {
    // Reported before the timeout and exit-code checks: the process was killed by this
    // layer, so neither its signal death nor its missing document is the real story.
    return {
      outcome: 'contract-breach',
      reason: 'stream-overflow',
      detail: `wrote more than ${MAX_STREAM_BYTES} bytes to stdout and stderr combined (overflowed on ${overflow.which}) and was killed`,
      exitCode: null,
      stdout,
      stderr,
      command,
      durationMs,
    };
  }

  if (timedOutWith !== null) {
    return {
      outcome: 'timeout',
      timeoutMs,
      signal: timedOutWith,
      stdout,
      stderr,
      command,
      durationMs,
    };
  }

  if (exitCode === null || !isDocumentedExit(exitCode)) {
    // A signal death, or a code outside the table. Either way the contract says
    // nothing about what stdout means here, so it is surfaced rather than parsed.
    return {
      outcome: 'contract-breach',
      reason: 'undocumented-exit-code',
      detail:
        exitCode === null
          ? 'the process was terminated by a signal rather than exiting'
          : `exit ${exitCode} is outside the documented set {0,1,2,3,4}`,
      exitCode,
      stdout,
      stderr,
      command,
      durationMs,
    };
  }

  const verdict = parseSingleDocument(stdout);
  if (!verdict.ok) {
    return {
      outcome: 'contract-breach',
      reason: verdict.reason,
      detail: verdict.detail,
      exitCode,
      stdout,
      stderr,
      command,
      durationMs,
    };
  }

  return {
    outcome: OUTCOME_BY_EXIT[exitCode],
    exitCode,
    document: verdict.document,
    stderr,
    command,
    durationMs,
  };
}
