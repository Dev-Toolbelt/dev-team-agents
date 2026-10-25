import { describe, expect, it } from 'vitest';

import { createSecretClipboard, settleSecretClipboard, type Timers } from '../src/main/secretClipboard.js';

function harness() {
  let text = '';
  let failReads = 0;
  const clipboard = {
    readText: () => (failReads-- > 0 ? Promise.reject(new Error('busy')) : Promise.resolve(text)),
    writeText: (next: string) => {
      text = next;
      return Promise.resolve();
    },
  };
  // Every armed timer by handle, so a handle that was lost would still be seen firing.
  const armed = new Map<number, () => void>();
  let next = 0;
  const timers: Timers = {
    setTimeout: (callback) => {
      armed.set(++next, callback);
      return next;
    },
    clearTimeout: (handle) => {
      armed.delete(handle as number);
    },
  };
  const flush = () => new Promise((resolve) => setTimeout(resolve, 0));
  const fireAll = async (): Promise<void> => {
    const due = [...armed.values()];
    armed.clear();
    due.forEach((callback) => callback());
    await flush();
  };
  return {
    clipboard,
    timers,
    fireAll,
    armed: () => armed.size,
    read: () => text,
    set: (value: string) => (text = value),
    failNextRead: () => (failReads = 1),
  };
}

describe('a copied secret on the clipboard (ADR-0046)', () => {
  it('is cleared when the timer fires and the clipboard still holds it', async () => {
    const h = harness();
    const secrets = createSecretClipboard(h.clipboard, 30_000, h.timers);
    await secrets.copy('s3cr3t');
    expect(h.read()).toBe('s3cr3t');
    await h.fireAll();
    expect(h.read()).toBe('');
    expect(secrets.hasPending()).toBe(false);
  });

  it('leaves whatever was copied since alone', async () => {
    const h = harness();
    const secrets = createSecretClipboard(h.clipboard, 30_000, h.timers);
    await secrets.copy('s3cr3t');
    h.set('something else');
    await h.fireAll();
    expect(h.read()).toBe('something else');
  });

  it('keeps one timer across overlapping copies and clears the last value', async () => {
    const h = harness();
    const secrets = createSecretClipboard(h.clipboard, 30_000, h.timers);
    await Promise.all([secrets.copy('first'), secrets.copy('second')]);
    expect(h.armed()).toBe(1);
    expect(h.read()).toBe('second');
    await h.fireAll();
    expect(h.read()).toBe('');
  });

  it('retries a clear that failed', async () => {
    const h = harness();
    const secrets = createSecretClipboard(h.clipboard, 30_000, h.timers);
    await secrets.copy('s3cr3t');
    h.failNextRead();
    await h.fireAll();
    expect(h.read()).toBe('s3cr3t');
    expect(secrets.hasPending()).toBe(true);
    expect(h.armed()).toBe(1);
    await h.fireAll();
    expect(h.read()).toBe('');
  });

  it('is cleared on quit, and a quit with nothing pending touches nothing', async () => {
    const h = harness();
    const secrets = createSecretClipboard(h.clipboard, 30_000, h.timers);
    await secrets.copy('s3cr3t');
    await settleSecretClipboard(secrets, 1_000);
    expect(h.read()).toBe('');
    h.set('later');
    await settleSecretClipboard(secrets, 1_000);
    expect(h.read()).toBe('later');
  });
});
