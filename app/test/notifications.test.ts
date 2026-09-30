/**
 * The notification path in the main process: the JSON Lines stream, the operations that
 * validate what it carries, the supervisor that restarts it, and the pure helpers of
 * background mode.
 *
 * The stream tests spawn a real child — `node test/fixtures/fake-watch.mjs` — because the
 * behaviours that matter (a line split across chunks, stdin-close as the stop signal, a
 * child that must be killed) only exist across a real pipe.
 */
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

import { afterEach, describe, expect, it, vi } from 'vitest';

import { streamDevteam, type StreamEnd } from '../src/cli/stream.js';
import {
  argvProblem,
  asNotification,
  asWatchEvent,
  NOTIFICATION_ID,
  watchNotifications,
  type WatchEvent,
} from '../src/cli/operations.js';
import {
  BACKOFF_MAX_MS,
  BACKOFF_MIN_MS,
  HEALTHY_MS,
  NotificationCenter,
  WATCHDOG_MS,
  type NativeNotice,
  type NotificationCenterDeps,
} from '../src/main/notifications.js';
import { loginItemOptions, loginItemState, shouldHideOnClose, trayTitle, trayTooltip } from '../src/main/background.js';
import type { NotificationFeed, QueuedNotification } from '../src/shared/api.js';

const FAKE = join(dirname(fileURLToPath(import.meta.url)), 'fixtures', 'fake-watch.mjs');

function collect(mode: string, killGraceMs = 200) {
  const events: Record<string, unknown>[] = [];
  let resolveEnd: (end: StreamEnd) => void = () => undefined;
  const ended = new Promise<StreamEnd>((resolve) => {
    resolveEnd = resolve;
  });
  const handle = streamDevteam({
    binary: process.execPath,
    args: [FAKE, mode],
    killGraceMs,
    onEvent: (event) => events.push(event),
    onEnd: resolveEnd,
  });
  return { events, ended, handle };
}

async function until(check: () => boolean, ms = 5000): Promise<void> {
  const deadline = Date.now() + ms;
  while (!check()) {
    if (Date.now() > deadline) throw new Error('timed out waiting');
    await new Promise((resolve) => setTimeout(resolve, 10));
  }
}

describe('streamDevteam — JSON Lines over a real pipe', () => {
  it('delivers each line as an event, and ends cleanly when stdin is closed', async () => {
    const { events, ended, handle } = collect('stream');
    await until(() => events.some((e) => e['event'] === 'ready'));
    handle.stop();
    const end = await ended;
    expect(events.map((e) => e['event'])).toEqual(['notification', 'ready', 'end']);
    expect(end).toMatchObject({ kind: 'exited', code: 0 });
  });

  it('appends --json itself, after the caller’s words', async () => {
    const { events, ended } = collect('argv');
    await ended;
    expect(events[0]?.['argv']).toEqual(['--json']);
  });

  it('kills a child that sends a line that is not JSON, and says so', async () => {
    const { ended } = collect('garbage');
    const end = await ended;
    expect(end.kind).toBe('protocol');
    expect(end.kind === 'protocol' ? end.detail : '').toMatch(/not JSON/);
  });

  it('reports the exit code and the stderr tail of a child that exits on its own', async () => {
    const { ended } = collect('exit3');
    const end = await ended;
    expect(end).toMatchObject({ kind: 'exited', code: 3 });
    expect(end.kind === 'exited' ? end.stderr : '').toMatch(/layout migration/);
  });

  it('passes the CLI’s error line through as an event, and reports its exit code', async () => {
    const { events, ended } = collect('error3');
    const end = await ended;
    expect(end).toMatchObject({ kind: 'exited', code: 3 });
    expect(asWatchEvent(events[0]!)).toMatchObject({ event: 'error', exitCode: 3, message: expect.stringMatching(/layout/) });
  });

  it('lets a non-zero exit code win over an unparseable line', async () => {
    // An indented error document reads as `{` — a protocol error that used to bury the
    // exit 3 explaining it under an endless retry.
    const { ended } = collect('indented3');
    expect(await ended).toMatchObject({ kind: 'exited', code: 3 });
  });

  it('ends when the child exits even if a descendant still holds its pipes', async () => {
    const startedAt = Date.now();
    const events: Record<string, unknown>[] = [];
    const end = await new Promise<StreamEnd>((resolve) =>
      streamDevteam({
        binary: process.execPath,
        args: [FAKE, 'orphan'],
        pipeGraceMs: 200,
        onEvent: (event) => events.push(event),
        onEnd: resolve,
      }),
    );
    expect(end).toMatchObject({ kind: 'exited', code: 0 });
    expect(events.map((e) => e['event'])).toEqual(['ready']);
    expect(Date.now() - startedAt).toBeLessThan(4_000);
  });

  it('reports a binary that does not exist as spawn-failed, not as an exit', async () => {
    const end = await new Promise<StreamEnd>((resolve) =>
      streamDevteam({ binary: '/no/such/devteam', args: ['x'], onEvent: () => undefined, onEnd: resolve }),
    );
    expect(end.kind).toBe('spawn-failed');
  });
});

describe('notification operations — what reaches argv and the UI', () => {
  const raw = {
    id: '1790000000-42-7',
    ts: 1790000000,
    project_id: 'proj-1',
    session_id: 's1',
    level: 'warning',
    code: 'context.warning',
    message: 'm',
    dedupe_key: '',
    expires_at: 0,
    seen: false,
  };

  it('camel-cases a well-formed record', () => {
    expect(asNotification(raw)).toMatchObject({ id: raw.id, projectId: 'proj-1', level: 'warning', seen: false });
  });

  it('rejects an id that is not the hook’s shape, an unknown level and an empty message', () => {
    expect(typeof asNotification({ ...raw, id: '--all' })).toBe('string');
    expect(typeof asNotification({ ...raw, level: 'fatal' })).toBe('string');
    expect(typeof asNotification({ ...raw, message: '  ' })).toBe('string');
  });

  it('only ever acks by one well-formed id — never a flag, never --all', () => {
    expect(NOTIFICATION_ID.test('1790000000-42-7')).toBe(true);
    expect(NOTIFICATION_ID.test('--all')).toBe(false);
    expect(argvProblem(['notifications', 'ack', '--all'])).not.toBeNull();
    expect(argvProblem(['notifications', 'ack', '1790000000-42-7'])).toBeNull();
    expect(argvProblem(['notifications', 'ack', 'a', 'b'])).not.toBeNull();
  });

  it('types every event the stream sends, and names one it does not know', () => {
    expect(asWatchEvent({ event: 'ready', projects: 2 })).toEqual({ event: 'ready', projects: 2 });
    expect(asWatchEvent({ event: 'end', reason: 'sigterm' })).toEqual({ event: 'end', reason: 'sigterm' });
    expect(asWatchEvent({ event: 'notification', notification: raw })).toMatchObject({ event: 'notification' });
    expect(typeof asWatchEvent({ event: 'surprise' })).toBe('string');
  });

  it('starts watch through the same allow-list run() enforces, with the declaration', () => {
    const spawnStream = vi.fn(() => ({ stop: () => undefined, pid: 1 }));
    watchNotifications(
      { binary: '/bin/devteam', cwd: '/app', declarationFile: '/app/schemas.json' },
      { onEvent: () => undefined, onInvalid: () => undefined, onEnd: () => undefined },
      spawnStream,
    );
    expect(spawnStream).toHaveBeenCalledWith(
      expect.objectContaining({ args: ['notifications', 'watch'], declarationFile: '/app/schemas.json' }),
    );
  });
});

// ── the supervisor ────────────────────────────────────────────────────────────

function notification(id: string, overrides: Partial<QueuedNotification> = {}): QueuedNotification {
  return {
    id,
    level: 'warning',
    code: 'c',
    message: `message ${id}`,
    ts: 1790000000,
    projectId: 'proj-1',
    sessionId: 's1',
    expiresAt: 0,
    seen: false,
    ...overrides,
  };
}

function harness(overrides: Partial<NotificationCenterDeps> = {}) {
  type Handlers = Parameters<NotificationCenterDeps['startStream']>[0];
  const streams: { handlers: Handlers; stop: ReturnType<typeof vi.fn> }[] = [];
  const timers: { fn: () => void; ms: number; cleared: boolean }[] = [];
  const shown: NativeNotice[] = [];
  const acked: string[] = [];
  const feeds: NotificationFeed[] = [];
  const opened: string[] = [];
  const deps: NotificationCenterDeps = {
    startStream: (handlers) => {
      const stop = vi.fn();
      streams.push({ handlers, stop });
      return Promise.resolve({ stop, pid: streams.length });
    },
    ack: (id) => {
      acked.push(id);
      return Promise.resolve();
    },
    projectName: () => Promise.resolve('Storefront'),
    nativeSupported: () => true,
    showNative: (notice) => shown.push(notice),
    openProject: (id) => opened.push(id),
    onFeedChange: (feed) => feeds.push(feed),
    setTimer: (fn, ms) => {
      const timer = { fn, ms, cleared: false };
      timers.push(timer);
      return timer;
    },
    clearTimer: (timer) => {
      (timer as { cleared: boolean }).cleared = true;
    },
    ...overrides,
  };
  const center = new NotificationCenter(deps);
  const emit = (event: WatchEvent) => streams[streams.length - 1]?.handlers.onEvent(event);
  const end = (value: StreamEnd) => streams[streams.length - 1]?.handlers.onEnd(value);
  const fire = (ms: number) => {
    const timer = timers.find((t) => !t.cleared && t.ms === ms);
    if (timer === undefined) throw new Error(`no pending timer of ${ms} ms`);
    timer.cleared = true;
    timer.fn();
  };
  const flush = () => new Promise((resolve) => setTimeout(resolve, 0));
  return { center, streams, timers, shown, acked, feeds, opened, emit, end, fire, flush };
}

describe('NotificationCenter — show, acknowledge, and never twice', () => {
  it('goes live on ready, shows each notification with the project’s name, and acks it', async () => {
    const h = harness();
    await h.center.start();
    h.emit({ event: 'ready', projects: 1 });
    h.emit({ event: 'notification', notification: notification('1-1-1', { level: 'critical' }) });
    await h.flush();
    expect(h.center.snapshot().status).toBe('live');
    expect(h.shown).toHaveLength(1);
    expect(h.shown[0]?.title).toContain('Storefront');
    expect(h.shown[0]?.title).not.toContain('proj-1');
    expect(h.shown[0]?.persistent).toBe(true);
    expect(h.acked).toEqual(['1-1-1']);
    expect(h.center.snapshot().unread).toBe(1);
  });

  it('does not show a replayed notification a second time', async () => {
    const h = harness();
    await h.center.start();
    h.emit({ event: 'ready', projects: 1 });
    h.emit({ event: 'notification', notification: notification('1-1-1') });
    h.emit({ event: 'notification', notification: notification('1-1-1') });
    await h.flush();
    expect(h.shown).toHaveLength(1);
    expect(h.center.snapshot().items).toHaveLength(1);
  });

  it('paused: no banner, but still in the bell and still acknowledged', async () => {
    const h = harness();
    await h.center.start();
    h.emit({ event: 'ready', projects: 1 });
    h.center.setPaused(true);
    h.emit({ event: 'notification', notification: notification('2-2-2') });
    await h.flush();
    expect(h.shown).toHaveLength(0);
    expect(h.center.snapshot().items.map((i) => i.id)).toEqual(['2-2-2']);
    expect(h.acked).toEqual(['2-2-2']);
  });

  it('a click opens the project it came from', async () => {
    const h = harness();
    await h.center.start();
    h.emit({ event: 'ready', projects: 1 });
    h.emit({ event: 'notification', notification: notification('3-3-3', { projectId: 'proj-9' }) });
    await h.flush();
    h.shown[0]?.onClick();
    expect(h.opened).toEqual(['proj-9']);
  });

  it('shows a backlog longer than the limit as one summary banner, with every record in the bell', async () => {
    const h = harness({ projectName: (id) => Promise.resolve(id === 'proj-2' ? 'Billing' : 'Storefront') });
    await h.center.start();
    const backlog = [1, 2, 3, 4, 5].map((n) =>
      notification(`${n}-0-0`, { ts: 1790000000 + n, projectId: n === 5 ? 'proj-2' : 'proj-1' }),
    );
    for (const record of backlog) h.emit({ event: 'notification', notification: record });
    expect(h.shown).toHaveLength(0); // nothing before ready
    h.emit({ event: 'ready', projects: 2 });
    await h.flush();
    await h.center.acksSettled();
    expect(h.shown).toHaveLength(1);
    expect(h.shown[0]?.title).toBe('5 notifications');
    expect(h.shown[0]?.body).toContain('Storefront');
    expect(h.shown[0]?.body).toContain('Billing');
    h.shown[0]?.onClick();
    expect(h.opened).toEqual(['proj-2']); // the newest
    expect(h.center.snapshot().items.map((i) => i.id)).toEqual(['5-0-0', '4-0-0', '3-0-0', '2-0-0', '1-0-0']);
    expect(h.acked).toEqual(['1-0-0', '2-0-0', '3-0-0', '4-0-0', '5-0-0']);
  });

  it('a short backlog still gets one banner per record', async () => {
    const h = harness();
    await h.center.start();
    h.emit({ event: 'notification', notification: notification('1-0-0') });
    h.emit({ event: 'notification', notification: notification('2-0-0') });
    h.emit({ event: 'ready', projects: 1 });
    await h.flush();
    expect(h.shown).toHaveLength(2);
  });

  it('runs acknowledgements one at a time, in order', async () => {
    let running = 0;
    let peak = 0;
    const order: string[] = [];
    const h = harness({
      ack: async (id) => {
        running += 1;
        peak = Math.max(peak, running);
        await new Promise((resolve) => setTimeout(resolve, 1));
        order.push(id);
        running -= 1;
      },
    });
    await h.center.start();
    h.emit({ event: 'ready', projects: 1 });
    for (const id of ['1-0-0', '2-0-0', '3-0-0']) h.emit({ event: 'notification', notification: notification(id) });
    await h.flush();
    await h.center.acksSettled();
    expect(peak).toBe(1);
    expect(order).toEqual(['1-0-0', '2-0-0', '3-0-0']);
  });

  it('orders the bell by the record’s time, not by when its name resolved', async () => {
    const h = harness({
      // The older record's name resolves last.
      projectName: (id) =>
        new Promise((resolve) => setTimeout(() => resolve(id), id === 'old' ? 5 : 0)),
    });
    await h.center.start();
    h.emit({ event: 'ready', projects: 1 });
    h.emit({ event: 'notification', notification: notification('1-0-0', { ts: 100, projectId: 'old' }) });
    h.emit({ event: 'notification', notification: notification('2-0-0', { ts: 200, projectId: 'new' }) });
    await new Promise((resolve) => setTimeout(resolve, 20));
    expect(h.center.snapshot().items.map((i) => i.id)).toEqual(['2-0-0', '1-0-0']);
  });

  it('markRead resets the unread count without dropping items', async () => {
    const h = harness();
    await h.center.start();
    h.emit({ event: 'ready', projects: 1 });
    h.emit({ event: 'notification', notification: notification('4-4-4') });
    await h.flush();
    expect(h.center.markRead()).toMatchObject({ unread: 0, items: [expect.objectContaining({ id: '4-4-4' })] });
  });
});

describe('NotificationCenter — the stream is supervised', () => {
  it('restarts after an unexpected exit with a doubling backoff, reset once a child stays healthy', async () => {
    const h = harness();
    await h.center.start();
    h.end({ kind: 'exited', code: 1, signal: null, stderr: '' });
    expect(h.center.snapshot().status).toBe('retrying');
    h.fire(BACKOFF_MIN_MS);
    await h.flush();
    expect(h.streams).toHaveLength(2);
    h.end({ kind: 'exited', code: 1, signal: null, stderr: '' });
    h.fire(BACKOFF_MIN_MS * 2);
    await h.flush();
    h.emit({ event: 'ready', projects: 0 });
    h.fire(HEALTHY_MS);
    h.end({ kind: 'exited', code: 1, signal: null, stderr: '' });
    // Back to the shortest delay once the child stayed up.
    expect(() => h.fire(BACKOFF_MIN_MS)).not.toThrow();
  });

  it('does not reset the backoff for a child that dies right after ready', async () => {
    // Reset on `ready` itself, a child crashing just after it restarted every second.
    const h = harness();
    await h.center.start();
    h.end({ kind: 'exited', code: 1, signal: null, stderr: '' });
    h.fire(BACKOFF_MIN_MS);
    await h.flush();
    h.emit({ event: 'ready', projects: 0 });
    h.end({ kind: 'exited', code: 1, signal: null, stderr: '' });
    expect(() => h.fire(BACKOFF_MIN_MS * 2)).not.toThrow();
  });

  it('reports the stream’s own error event as the reason for an exit 3', async () => {
    // Under --json the CLI's explanation is a stdout line, not stderr.
    const h = harness();
    await h.center.start();
    h.emit({ event: 'error', message: 'this store needs a layout migration', hint: 'Run devteam migrate.', exitCode: 3 });
    h.end({ kind: 'exited', code: 3, signal: null, stderr: '' });
    expect(h.center.snapshot()).toMatchObject({ status: 'unavailable' });
    expect(h.center.snapshot().detail).toMatch(/layout migration Run devteam migrate\./);
  });

  it('start() while a stream runs or is starting does not begin a second one', async () => {
    const h = harness();
    await Promise.all([h.center.start(), h.center.start()]);
    await h.center.start();
    expect(h.streams).toHaveLength(1);
  });

  it('never waits longer than the cap', async () => {
    const h = harness();
    await h.center.start();
    let delay = BACKOFF_MIN_MS;
    for (let i = 0; i < 10; i += 1) {
      h.end({ kind: 'exited', code: 1, signal: null, stderr: '' });
      h.fire(delay);
      await h.flush();
      delay = Math.min(delay * 2, BACKOFF_MAX_MS);
    }
    const retries = h.timers.filter((t) => t.ms !== WATCHDOG_MS);
    expect(retries.length).toBeGreaterThan(5);
    expect(retries.every((t) => t.ms <= BACKOFF_MAX_MS)).toBe(true);
    expect(retries.some((t) => t.ms === BACKOFF_MAX_MS)).toBe(true);
  });

  it('does not retry an environment error (exit 3), and says why', async () => {
    const h = harness();
    await h.center.start();
    h.end({ kind: 'exited', code: 3, signal: null, stderr: 'devteam: error: the store needs a layout migration\n' });
    expect(h.center.snapshot()).toMatchObject({ status: 'unavailable' });
    expect(h.center.snapshot().detail).toMatch(/layout migration/);
    expect(h.timers.filter((t) => !t.cleared && t.ms === BACKOFF_MIN_MS)).toHaveLength(0);
  });

  it('restarts a child that has gone silent past the watchdog', async () => {
    const h = harness();
    await h.center.start();
    h.fire(WATCHDOG_MS);
    expect(h.streams[0]?.stop).toHaveBeenCalled();
  });

  it('reports no CLI as unavailable instead of retrying forever', async () => {
    const h = harness({ startStream: () => Promise.resolve(null) });
    await h.center.start();
    expect(h.center.snapshot().status).toBe('unavailable');
  });

  it('a restart that lands while the first start is still pending leaves exactly one child', async () => {
    // The packaged app ran two `watch` children: start() at launch, then the renderer's
    // re-resolve called restart() before the first startStream had returned.
    let release: () => void = () => undefined;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    const stops: ReturnType<typeof vi.fn>[] = [];
    let calls = 0;
    const h = harness({
      startStream: async () => {
        calls += 1;
        if (calls === 1) await gate;
        const stop = vi.fn();
        stops.push(stop);
        return { stop, pid: calls };
      },
    });
    const first = h.center.start();
    await h.center.restart();
    release();
    await first;
    expect(stops).toHaveLength(2);
    const running = stops.filter((stop) => stop.mock.calls.length === 0);
    expect(running).toHaveLength(1);
  });

  it('stop() closes the child and schedules nothing more', async () => {
    const h = harness();
    await h.center.start();
    h.center.stop();
    expect(h.streams[0]?.stop).toHaveBeenCalled();
    h.end({ kind: 'exited', code: 0, signal: null, stderr: '' });
    expect(h.center.snapshot().status).not.toBe('retrying');
  });
});

describe('background mode — the pure decisions', () => {
  it('reports the OS answer, not the choice, for a packaged macOS build', () => {
    expect(loginItemState(true, { openAtLogin: false, status: 'requires-approval' }, 'darwin', true)).toMatchObject({
      openAtLogin: true,
      loginItemStatus: 'requires-approval',
    });
    expect(loginItemState(true, { openAtLogin: false, status: 'not-registered' }, 'darwin', true).detail).toMatch(
      /not signed/,
    );
  });

  it('says a development build cannot register anything', () => {
    expect(loginItemState(false, { openAtLogin: false }, 'darwin', false).loginItemStatus).toBe('unsupported');
  });

  it('reads openAtLogin on Windows, and flags a choice the OS did not record', () => {
    expect(loginItemState(true, { openAtLogin: true }, 'win32', true).loginItemStatus).toBe('enabled');
    expect(loginItemState(true, { openAtLogin: false }, 'win32', true).detail).toMatch(/did not record/);
  });

  it('hides on close unless the app is really quitting', () => {
    expect(shouldHideOnClose(false, true, 'win32')).toBe(true);
    expect(shouldHideOnClose(true, true, 'win32')).toBe(false);
    expect(shouldHideOnClose(true, true, 'darwin')).toBe(false);
  });

  it('closes instead of hiding when nothing could bring the window back', () => {
    // No tray on Windows: hidden would be an invisible process. macOS keeps the Dock.
    expect(shouldHideOnClose(false, false, 'win32')).toBe(false);
    expect(shouldHideOnClose(false, false, 'linux')).toBe(false);
    expect(shouldHideOnClose(false, false, 'darwin')).toBe(true);
  });

  it('registers and reads back the Windows login item with the same args', () => {
    // Read back without `--hidden`, Windows reported `openAtLogin: false` right after
    // a successful registration.
    expect(loginItemOptions('win32')).toEqual({ args: ['--hidden'] });
    expect(loginItemOptions('darwin')).toEqual({});
  });

  it('renders the tray count and tooltip', () => {
    expect(trayTitle(0)).toBe('');
    expect(trayTitle(3)).toBe('3');
    expect(trayTitle(150)).toBe('99+');
    expect(trayTooltip('Dev Team Agents', 2, true)).toBe('Dev Team Agents — 2 new notifications — notifications paused');
  });
});

afterEach(() => {
  vi.restoreAllMocks();
});
