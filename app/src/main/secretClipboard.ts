/**
 * Putting a copied secret on the clipboard and taking it off again (ADR-0046).
 *
 * The value is written by the main process and never sent to the renderer. After
 * `clearAfterMs` the clipboard is emptied — but only if it still holds that value, so
 * whatever the person copied since is left alone. Only a digest is kept for that comparison;
 * the plaintext itself lingers in this process only until it is garbage-collected.
 *
 * Copies and clears run one at a time, so overlapping copies cannot lose track of which
 * value is on the clipboard. A clear that fails is retried after another `clearAfterMs`.
 *
 * No `electron` import: the clipboard and the timers are injected, so a test drives both.
 */

import { createHash } from 'node:crypto';

/** Electron's clipboard, which is asynchronous. */
export interface ClipboardLike {
  readText(): Promise<string>;
  writeText(text: string): Promise<void>;
}

export interface Timers {
  readonly setTimeout: (callback: () => void, ms: number) => unknown;
  readonly clearTimeout: (handle: unknown) => void;
}

export interface SecretClipboard {
  copy(value: string): Promise<void>;
  /** Whether a copied secret may still be on the clipboard. Quitting waits for `clearNow` then. */
  hasPending(): boolean;
  /** Clear now if the clipboard still holds the last copied secret. For quitting. */
  clearNow(): Promise<void>;
}

/**
 * For quitting: clear a pending secret, giving up after `timeoutMs` so a stuck clipboard
 * cannot hold the app open. Never rejects.
 */
export function settleSecretClipboard(secrets: SecretClipboard, timeoutMs: number): Promise<void> {
  if (!secrets.hasPending()) return Promise.resolve();
  return new Promise((resolve) => {
    const timer = setTimeout(resolve, timeoutMs);
    void secrets
      .clearNow()
      .catch(() => undefined)
      .finally(() => {
        clearTimeout(timer);
        resolve();
      });
  });
}

const digest = (text: string): string => createHash('sha256').update(text, 'utf8').digest('hex');

const NODE_TIMERS: Timers = {
  setTimeout: (callback, ms) => {
    const handle = setTimeout(callback, ms);
    // A pending clear must not keep the app alive; quitting calls `clearNow` instead.
    handle.unref();
    return handle;
  },
  clearTimeout: (handle) => clearTimeout(handle as NodeJS.Timeout),
};

export function createSecretClipboard(clipboard: ClipboardLike, clearAfterMs: number, timers: Timers = NODE_TIMERS): SecretClipboard {
  let pending: { handle: unknown; readonly digest: string } | null = null;
  let queue: Promise<void> = Promise.resolve();

  const serially = (task: () => Promise<void>): Promise<void> => {
    const run = queue.then(task, task);
    queue = run.catch(() => undefined);
    return run;
  };

  const clear = (): Promise<void> =>
    serially(async () => {
      const current = pending;
      if (current === null) return;
      timers.clearTimeout(current.handle);
      try {
        if (digest(await clipboard.readText()) === current.digest) await clipboard.writeText('');
      } catch (error) {
        // Still tracked: the next timer, copy or quit tries again.
        if (pending === current) current.handle = timers.setTimeout(onTimer, clearAfterMs);
        throw error;
      }
      if (pending === current) pending = null;
    });

  // A failed clear has nowhere to be reported; `clear` has already re-armed the timer.
  const onTimer = (): void => void clear().catch(() => undefined);

  return {
    copy: (value) =>
      serially(async () => {
        if (pending !== null) timers.clearTimeout(pending.handle);
        // Tracked before the write, so a quit that arrives during it still clears.
        pending = { handle: timers.setTimeout(onTimer, clearAfterMs), digest: digest(value) };
        await clipboard.writeText(value);
      }),
    hasPending: () => pending !== null,
    clearNow: clear,
  };
}
