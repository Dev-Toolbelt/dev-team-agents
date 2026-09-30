/**
 * A long-running `devteam` child whose `--json` stdout is JSON Lines.
 *
 * `invoke.ts` runs a command to completion and reads one document. `devteam
 * notifications watch` never completes on its own: it streams one compact document per
 * event until its stdin closes or it is sent SIGTERM. This is the other half of that
 * contract, under the same rules as `invoke.ts` — no shell, the minimal environment,
 * `--json` added here, the schema declaration on every call.
 *
 * **Stopping is closing stdin.** The CLI treats EOF on stdin as "the reader is gone" and
 * ends with `{"event": "end", "reason": "stdin-closed"}`. That is also what happens for
 * free when this process dies without cleaning up: the pipe closes and the watcher exits,
 * rather than polling the disk forever for nobody. SIGTERM, then SIGKILL, back it up.
 *
 * Imports nothing from `electron`.
 */

import { spawn } from 'node:child_process';

import { childEnvironment, KILL_GRACE_MS, PIPE_GRACE_MS, type InvokeOptions } from './invoke.js';

/** A single event line longer than this is a runaway; the child is killed. */
export const MAX_LINE_BYTES = 1024 * 1024;
/** See `fail` below: time for a failing CLI to exit with its own code before it is killed. */
export const PROTOCOL_GRACE_MS = 1_000;

export type StreamEnd =
  | { readonly kind: 'exited'; readonly code: number | null; readonly signal: NodeJS.Signals | null; readonly stderr: string }
  | { readonly kind: 'spawn-failed'; readonly detail: string }
  | { readonly kind: 'protocol'; readonly detail: string };

export interface StreamOptions extends Pick<InvokeOptions, 'binary' | 'cwd' | 'env' | 'declarationFile'> {
  readonly args: readonly string[];
  /** Called once per parsed line, in order. A line that is not a JSON object ends the stream. */
  readonly onEvent: (event: Record<string, unknown>) => void;
  /** Called exactly once, however the stream ended. */
  readonly onEnd: (end: StreamEnd) => void;
  readonly killGraceMs?: number;
  /** How long a child that sent an unparseable line has to exit on its own. */
  readonly protocolGraceMs?: number;
  /** See `PIPE_GRACE_MS` in `invoke.ts`. */
  readonly pipeGraceMs?: number;
}

export interface StreamHandle {
  /** Ask the child to stop: close its stdin, then SIGTERM and SIGKILL if it does not. */
  readonly stop: () => void;
  readonly pid: number | undefined;
}

export function streamDevteam(options: StreamOptions): StreamHandle {
  const args = [...options.args, '--json'];
  if (options.declarationFile !== undefined) args.unshift('--client-schemas', options.declarationFile);
  const killGraceMs = options.killGraceMs ?? KILL_GRACE_MS;
  const protocolGraceMs = options.protocolGraceMs ?? PROTOCOL_GRACE_MS;
  const pipeGraceMs = options.pipeGraceMs ?? PIPE_GRACE_MS;

  let ended = false;
  const finish = (end: StreamEnd): void => {
    if (ended) return;
    ended = true;
    options.onEnd(end);
  };

  let child: ReturnType<typeof spawn>;
  try {
    child = spawn(options.binary, args, {
      shell: false,
      stdio: ['pipe', 'pipe', 'pipe'],
      ...(options.cwd !== undefined ? { cwd: options.cwd } : {}),
      env: childEnvironment(process.env, options.env ?? {}),
      windowsHide: true,
    });
  } catch (error) {
    const err = error as NodeJS.ErrnoException;
    queueMicrotask(() => finish({ kind: 'spawn-failed', detail: `${err.code ?? 'spawn error'}: ${err.message}` }));
    return { stop: () => undefined, pid: undefined };
  }

  let buffered = '';
  let stderr = '';
  let protocolError: string | null = null;
  const timers: NodeJS.Timeout[] = [];

  const kill = (): void => {
    if (child.exitCode !== null || child.signalCode !== null) return;
    child.kill('SIGTERM');
    timers.push(
      setTimeout(() => {
        if (child.exitCode === null && child.signalCode === null) child.kill('SIGKILL');
      }, killGraceMs),
    );
  };

  const fail = (detail: string): void => {
    if (protocolError !== null) return;
    protocolError = detail;
    // Not at once: a CLI that is failing prints its error and exits with the code that
    // explains it, and killing it first would replace that code with our signal. A
    // child still running after the grace period is killed.
    timers.push(setTimeout(kill, protocolGraceMs));
  };

  child.stdout?.setEncoding('utf8');
  child.stdout?.on('data', (chunk: string) => {
    buffered += chunk;
    let newline = buffered.indexOf('\n');
    while (newline !== -1) {
      const line = buffered.slice(0, newline).trim();
      buffered = buffered.slice(newline + 1);
      newline = buffered.indexOf('\n');
      if (line === '' || protocolError !== null) continue;
      let parsed: unknown;
      try {
        parsed = JSON.parse(line);
      } catch {
        fail(`a line on stdout was not JSON: ${line.slice(0, 200)}`);
        continue;
      }
      if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
        fail('a line on stdout was not a JSON object');
        continue;
      }
      options.onEvent(parsed as Record<string, unknown>);
    }
    if (Buffer.byteLength(buffered) > MAX_LINE_BYTES) {
      // A runaway gets no grace period: the buffer would keep growing through it.
      fail(`an event line exceeded ${MAX_LINE_BYTES} bytes`);
      buffered = '';
      kill();
    }
  });
  child.stderr?.setEncoding('utf8');
  child.stderr?.on('data', (chunk: string) => {
    // A tail is enough to explain an exit; the stream itself never needs stderr.
    stderr = (stderr + chunk).slice(-8192);
  });
  // A write to a closed stdin after the child exits is expected, not an error.
  child.stdin?.on('error', () => undefined);

  child.on('error', (error: NodeJS.ErrnoException) => {
    finish({ kind: 'spawn-failed', detail: `${error.code ?? 'spawn error'}: ${error.message}` });
  });
  const conclude = (code: number | null, signal: NodeJS.Signals | null): void => {
    for (const timer of timers) clearTimeout(timer);
    // A child that exited non-zero on its own is reported by its exit code, even after
    // an unparseable line: the code is the CLI's stated reason (3 = an environment it
    // cannot fix), and a protocol error would bury it under a generic retry. A SIGTERM
    // we sent ends `watch` with 0, so this cannot mask a protocol error we reacted to.
    const exitedWithReason = code !== null && code !== 0 && signal === null;
    if (protocolError !== null && !exitedWithReason) finish({ kind: 'protocol', detail: protocolError });
    else finish({ kind: 'exited', code, signal, stderr });
  };
  child.on('close', conclude);
  // A descendant that inherited the pipes keeps `close` from ever firing after the CLI is
  // gone, and the supervisor would then wait on a stream that has already ended. See
  // `PIPE_GRACE_MS` in `invoke.ts`.
  child.on('exit', (code, signal) => {
    const cut = setTimeout(() => {
      conclude(code, signal);
      child.stdout?.destroy();
      child.stderr?.destroy();
    }, pipeGraceMs);
    cut.unref?.();
    child.once('close', () => clearTimeout(cut));
  });

  return {
    pid: child.pid,
    stop: () => {
      child.stdin?.end();
      timers.push(setTimeout(kill, killGraceMs));
    },
  };
}
