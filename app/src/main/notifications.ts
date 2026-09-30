/**
 * The notification center: supervises `devteam notifications watch`, shows each record
 * as a native notification, acknowledges it, and keeps the feed the bell renders.
 *
 * **It lives in the main process on purpose.** The renderer is gone when the window is
 * closed; the main process is not (macOS keeps the app alive with no window, and phase 2
 * keeps it alive on Windows via the tray). A stream owned by the renderer would stop
 * exactly when the user is not looking — which is when a notification is worth most.
 *
 * **One long-lived child, not polling.** `watch` stats the queues itself once a second;
 * polling `list` from here would start a python process every few seconds all day.
 *
 * **Ack on display** (the user's choice): a record is acknowledged when it is shown, so
 * it is never shown twice — across a restart of the stream, of the app, or on a second
 * machine window. Paused, it is still acknowledged and still lands in the bell: pausing
 * silences the banner, it does not hide the notification.
 *
 * Imports nothing from `electron`; `index.ts` injects the native pieces, which is what
 * lets the supervisor be tested against a fake stream.
 */

import type { StreamEnd, StreamHandle } from '../cli/stream.js';
import type { WatchEvent } from '../cli/operations.js';
import type { AppNotification, NotificationFeed, ProjectId, QueuedNotification } from '../shared/api.js';

/** Items kept for the bell. */
export const FEED_LIMIT = 50;
/** First restart delay; doubles to `BACKOFF_MAX_MS`. Reset after a healthy `ready`. */
export const BACKOFF_MIN_MS = 1_000;
export const BACKOFF_MAX_MS = 60_000;
/**
 * No event at all for this long means the child is hung, not quiet: `watch` sends a
 * heartbeat every 30 s. It is restarted.
 */
export const WATCHDOG_MS = 90_000;

export interface NativeNotice {
  readonly title: string;
  readonly body: string;
  /** `critical` stays on screen until dismissed where the platform allows it. */
  readonly persistent: boolean;
  readonly onClick: () => void;
}

export interface NotificationCenterDeps {
  /** Start the stream; `null` when there is no CLI to run it with yet. */
  readonly startStream: (handlers: {
    readonly onEvent: (event: WatchEvent) => void;
    readonly onInvalid: (detail: string) => void;
    readonly onEnd: (end: StreamEnd) => void;
  }) => Promise<StreamHandle | null>;
  readonly ack: (id: string) => Promise<unknown>;
  /** The app's names for projects; the directory basename is the caller's fallback. */
  readonly projectName: (projectId: ProjectId) => Promise<string>;
  /** Whether native notifications can be shown at all on this platform/build. */
  readonly nativeSupported: () => boolean;
  readonly showNative: (notice: NativeNotice) => void;
  /** A notification was clicked: show the window on that project. */
  readonly openProject: (projectId: ProjectId) => void;
  readonly onFeedChange: (feed: NotificationFeed) => void;
  readonly setTimer?: (fn: () => void, ms: number) => unknown;
  readonly clearTimer?: (handle: unknown) => void;
  readonly log?: (message: string) => void;
}

const LEVEL_PREFIX: Readonly<Record<QueuedNotification['level'], string>> = {
  info: '',
  warning: '⚠︎ ',
  critical: '‼︎ ',
};

export class NotificationCenter {
  private feed: NotificationFeed = { status: 'starting', detail: null, items: [], unread: 0, paused: false };
  private handle: StreamHandle | null = null;
  private stopped = false;
  private backoff = BACKOFF_MIN_MS;
  private retryTimer: unknown = null;
  private watchdogTimer: unknown = null;
  private readonly seenIds = new Set<string>();
  private readonly setTimer: (fn: () => void, ms: number) => unknown;
  private readonly clearTimer: (handle: unknown) => void;

  constructor(private readonly deps: NotificationCenterDeps) {
    this.setTimer = deps.setTimer ?? ((fn, ms) => setTimeout(fn, ms));
    this.clearTimer = deps.clearTimer ?? ((handle) => clearTimeout(handle as NodeJS.Timeout));
  }

  snapshot(): NotificationFeed {
    return this.feed;
  }

  async start(): Promise<void> {
    this.stopped = false;
    await this.spawn();
  }

  /** Stop for good (app quitting). Closes the child's stdin, which ends `watch`. */
  stop(): void {
    this.stopped = true;
    this.clearRetry();
    this.clearWatchdog();
    this.handle?.stop();
    this.handle = null;
  }

  /** Re-resolve happened, or the user asked: drop the current child and start again now. */
  async restart(): Promise<void> {
    this.handle?.stop();
    this.handle = null;
    this.clearRetry();
    this.backoff = BACKOFF_MIN_MS;
    await this.start();
  }

  markRead(): NotificationFeed {
    this.update({ unread: 0 });
    return this.feed;
  }

  setPaused(paused: boolean): NotificationFeed {
    this.update({ paused });
    return this.feed;
  }

  // ── the stream ────────────────────────────────────────────────────────────

  private async spawn(): Promise<void> {
    if (this.stopped) return;
    this.update({ status: this.feed.status === 'retrying' ? 'retrying' : 'starting' });
    let handle: StreamHandle | null;
    try {
      handle = await this.deps.startStream({
        onEvent: (event) => this.onEvent(event),
        onInvalid: (detail) => this.deps.log?.(`notifications: ignored an event: ${detail}`),
        onEnd: (end) => this.onEnd(end),
      });
    } catch (error) {
      this.scheduleRetry(`the notification stream could not start: ${String(error)}`);
      return;
    }
    if (handle === null) {
      this.update({ status: 'unavailable', detail: 'No devteam CLI was found, so there is nothing to watch.' });
      return;
    }
    this.handle = handle;
    this.armWatchdog();
  }

  private onEvent(event: WatchEvent): void {
    this.armWatchdog();
    switch (event.event) {
      case 'ready':
        // Healthy again: the next failure starts from the shortest delay.
        this.backoff = BACKOFF_MIN_MS;
        this.update({ status: 'live', detail: null });
        return;
      case 'heartbeat':
        return;
      case 'end':
        return; // `onEnd` follows when the process closes.
      case 'notification':
        void this.deliver(event.notification);
        return;
    }
  }

  private onEnd(end: StreamEnd): void {
    this.clearWatchdog();
    this.handle = null;
    if (this.stopped) return;
    if (end.kind === 'exited' && end.code === 3) {
      // Environment: typically a store whose layout migration this app may not run.
      // Retrying cannot fix it; saying so can.
      this.update({
        status: 'unavailable',
        detail: `devteam could not watch notifications: ${lastLine(end.stderr) ?? 'environment error (exit 3)'}`,
      });
      return;
    }
    const why =
      end.kind === 'exited'
        ? `the notification stream stopped (exit ${end.code ?? end.signal ?? '?'})`
        : end.kind === 'protocol'
          ? `the notification stream sent something unexpected: ${end.detail}`
          : `the notification stream could not start: ${end.detail}`;
    this.scheduleRetry(why);
  }

  private scheduleRetry(detail: string): void {
    if (this.stopped) return;
    const delay = this.backoff;
    this.backoff = Math.min(this.backoff * 2, BACKOFF_MAX_MS);
    this.update({ status: 'retrying', detail: `${detail}. Retrying in ${Math.round(delay / 1000)} s.` });
    this.clearRetry();
    this.retryTimer = this.setTimer(() => {
      this.retryTimer = null;
      void this.spawn();
    }, delay);
  }

  private armWatchdog(): void {
    this.clearWatchdog();
    this.watchdogTimer = this.setTimer(() => {
      this.watchdogTimer = null;
      this.deps.log?.('notifications: no event in 90 s — restarting the stream');
      // Stopping makes the child exit, and `onEnd` schedules the restart.
      this.handle?.stop();
    }, WATCHDOG_MS);
  }

  private clearWatchdog(): void {
    if (this.watchdogTimer !== null) this.clearTimer(this.watchdogTimer);
    this.watchdogTimer = null;
  }

  private clearRetry(): void {
    if (this.retryTimer !== null) this.clearTimer(this.retryTimer);
    this.retryTimer = null;
  }

  // ── one notification ──────────────────────────────────────────────────────

  private async deliver(record: QueuedNotification): Promise<void> {
    // A stream restart replays the unseen backlog; an ack that has not landed yet would
    // otherwise show the same notification twice.
    if (this.seenIds.has(record.id)) return;
    this.seenIds.add(record.id);

    const projectName = await this.deps.projectName(record.projectId).catch(() => 'a project');
    const item: AppNotification = { ...record, projectName };
    this.update({
      items: [item, ...this.feed.items].slice(0, FEED_LIMIT),
      unread: this.feed.unread + 1,
    });

    if (!this.feed.paused && this.deps.nativeSupported()) {
      this.deps.showNative({
        title: `${LEVEL_PREFIX[record.level]}${projectName}`,
        body: record.message,
        persistent: record.level === 'critical',
        onClick: () => this.deps.openProject(record.projectId),
      });
    }
    // Acknowledged whether or not the banner was shown: it is in the bell either way,
    // and an unacknowledged record would be replayed by every future stream.
    await this.deps.ack(record.id).catch((error: unknown) => {
      this.deps.log?.(`notifications: could not acknowledge ${record.id}: ${String(error)}`);
    });
  }

  private update(patch: Partial<NotificationFeed>): void {
    this.feed = { ...this.feed, ...patch };
    this.deps.onFeedChange(this.feed);
  }
}

function lastLine(text: string): string | null {
  const lines = text.trim().split(/\r?\n/).filter((line) => line.trim() !== '');
  const last = lines[lines.length - 1];
  return last === undefined ? null : last.replace(/^devteam: (error: )?/, '');
}
