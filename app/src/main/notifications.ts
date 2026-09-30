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
/** First restart delay; doubles to `BACKOFF_MAX_MS`. Reset once a child stays healthy. */
export const BACKOFF_MIN_MS = 1_000;
export const BACKOFF_MAX_MS = 60_000;
/**
 * How long a child must run after `ready` before the backoff resets. Resetting on `ready`
 * itself let a child that crashes right after it restart every second, forever.
 */
export const HEALTHY_MS = 30_000;
/**
 * A backlog longer than this — what piled up while the app was not running — is shown
 * as one summary banner instead of one each. Every record still lands in the bell.
 */
export const BACKLOG_BANNER_LIMIT = 3;
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
  private healthyTimer: unknown = null;
  /** Records sent before this stream's `ready`: the backlog, shown together. */
  private backlog: QueuedNotification[] = [];
  private streamReady = false;
  /** Set by the stream's `error` event: the CLI's own words for why it is ending. */
  private streamError: string | null = null;
  /** A spawn is awaiting `startStream`; a second `start()` must not begin another. */
  private spawning = false;
  /**
   * Acks run one at a time. Each is a CLI process taking the same store lock; a burst of
   * them contended for it, a loser only logged its failure, and that record came back as
   * a duplicate on the next launch.
   */
  private ackChain: Promise<void> = Promise.resolve();
  private readonly seenIds = new Set<string>();
  /**
   * Bumped by every spawn, restart and stop. `startStream` is async, so a restart that
   * lands while a spawn is still awaiting it found no handle to stop — and both children
   * then ran. A spawn whose generation is stale by the time its child exists stops that
   * child at once, and a stale child's events and exit are ignored.
   */
  private generation = 0;
  private readonly setTimer: (fn: () => void, ms: number) => unknown;
  private readonly clearTimer: (handle: unknown) => void;

  constructor(private readonly deps: NotificationCenterDeps) {
    this.setTimer = deps.setTimer ?? ((fn, ms) => setTimeout(fn, ms));
    this.clearTimer = deps.clearTimer ?? ((handle) => clearTimeout(handle as NodeJS.Timeout));
  }

  snapshot(): NotificationFeed {
    return this.feed;
  }

  /** Start the stream. Idempotent: a running or starting stream is left as it is. */
  async start(): Promise<void> {
    this.stopped = false;
    if (this.handle !== null || this.spawning) return;
    await this.spawn();
  }

  /** Stop for good (app quitting). Closes the child's stdin, which ends `watch`. */
  stop(): void {
    this.stopped = true;
    this.generation += 1;
    // A spawn still pending is now stale and will not clear this itself.
    this.spawning = false;
    this.clearRetry();
    this.clearWatchdog();
    this.clearHealthy();
    this.handle?.stop();
    this.handle = null;
  }

  /** Re-resolve happened, or the user asked: drop the current child and start again now. */
  async restart(): Promise<void> {
    this.generation += 1;
    this.handle?.stop();
    this.handle = null;
    this.clearRetry();
    this.clearHealthy();
    this.backoff = BACKOFF_MIN_MS;
    this.stopped = false;
    // Straight to `spawn`, not `start`: a spawn still pending is superseded by the
    // generation bump above, and `start` would wait on it instead.
    await this.spawn();
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
    this.generation += 1;
    const generation = this.generation;
    const current = () => generation === this.generation && !this.stopped;
    this.streamReady = false;
    this.streamError = null;
    this.update({ status: this.feed.status === 'retrying' ? 'retrying' : 'starting' });
    let handle: StreamHandle | null;
    this.spawning = true;
    try {
      handle = await this.deps.startStream({
        onEvent: (event) => {
          if (current()) this.onEvent(event);
        },
        onInvalid: (detail) => this.deps.log?.(`notifications: ignored an event: ${detail}`),
        onEnd: (end) => {
          if (current()) this.onEnd(end);
        },
      });
    } catch (error) {
      if (current()) this.scheduleRetry(`the notification stream could not start: ${String(error)}`);
      return;
    } finally {
      if (generation === this.generation) this.spawning = false;
    }
    if (!current()) {
      // Superseded while it was starting: this child has no one left to report to.
      handle?.stop();
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
        this.streamReady = true;
        this.update({ status: 'live', detail: null });
        this.flushBacklog();
        // Healthy only once it has stayed up: then the next failure starts from the
        // shortest delay again.
        this.clearHealthy();
        this.healthyTimer = this.setTimer(() => {
          this.healthyTimer = null;
          this.backoff = BACKOFF_MIN_MS;
        }, HEALTHY_MS);
        return;
      case 'heartbeat':
        return;
      case 'end':
        return; // `onEnd` follows when the process closes.
      case 'error':
        this.streamError = event.hint === null ? event.message : `${event.message} ${event.hint}`;
        return;
      case 'notification':
        if (this.streamReady) void this.deliver([event.notification]);
        else this.backlog.push(event.notification);
        return;
    }
  }

  private onEnd(end: StreamEnd): void {
    this.clearWatchdog();
    this.clearHealthy();
    this.handle = null;
    // A stream that died mid-backlog still had records to show.
    this.flushBacklog();
    if (this.stopped) return;
    if (end.kind === 'exited' && end.code === 3) {
      // Environment: typically a store whose layout migration this app may not run.
      // Retrying cannot fix it; saying so can. Under `--json` the reason arrives as the
      // stream's `error` event; stderr is the fallback.
      const reason = this.streamError ?? lastLine(end.stderr) ?? 'environment error (exit 3)';
      this.deps.log?.(`notifications: stream unavailable, not retrying: ${reason}`);
      this.update({ status: 'unavailable', detail: `devteam could not watch notifications: ${reason}` });
      return;
    }
    const said = this.streamError === null ? '' : `: ${this.streamError}`;
    const why =
      end.kind === 'exited'
        ? `the notification stream stopped (exit ${end.code ?? end.signal ?? '?'})${said}`
        : end.kind === 'protocol'
          ? `the notification stream sent something unexpected: ${end.detail}`
          : `the notification stream could not start: ${end.detail}`;
    this.scheduleRetry(why);
  }

  private scheduleRetry(detail: string): void {
    if (this.stopped) return;
    const delay = this.backoff;
    this.backoff = Math.min(this.backoff * 2, BACKOFF_MAX_MS);
    // The banner is transient; a crash loop that leaves no line anywhere is undiagnosable
    // in a packaged build.
    this.deps.log?.(`notifications: ${detail}; retrying in ${Math.round(delay / 1000)} s`);
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

  private clearHealthy(): void {
    if (this.healthyTimer !== null) this.clearTimer(this.healthyTimer);
    this.healthyTimer = null;
  }

  private flushBacklog(): void {
    if (this.backlog.length === 0) return;
    const backlog = this.backlog;
    this.backlog = [];
    void this.deliver(backlog);
  }

  // ── one notification ──────────────────────────────────────────────────────

  /**
   * Show and acknowledge `records`: one banner each, or — for a backlog longer than
   * `BACKLOG_BANNER_LIMIT` — one summary banner for all of them.
   */
  private async deliver(records: readonly QueuedNotification[]): Promise<void> {
    // A stream restart replays the unseen backlog; an ack that has not landed yet would
    // otherwise show the same notification twice.
    const fresh = records.filter((record) => !this.seenIds.has(record.id));
    if (fresh.length === 0) return;
    for (const record of fresh) this.seenIds.add(record.id);

    const items: AppNotification[] = await Promise.all(
      fresh.map(async (record) => ({
        ...record,
        projectName: await this.deps.projectName(record.projectId).catch(() => 'a project'),
      })),
    );
    // Newest first by the record's own time, not by when its name resolved: concurrent
    // deliveries finish in any order.
    this.update({
      items: [...items, ...this.feed.items].sort(byNewest).slice(0, FEED_LIMIT),
      unread: this.feed.unread + items.length,
    });

    if (!this.feed.paused && this.deps.nativeSupported()) {
      if (items.length > BACKLOG_BANNER_LIMIT) this.deps.showNative(summaryNotice(items, this.deps.openProject));
      else for (const item of items) this.deps.showNative(singleNotice(item, this.deps.openProject));
    }
    // Acknowledged whether or not a banner was shown: it is in the bell either way, and
    // an unacknowledged record would be replayed by every future stream.
    for (const item of items) this.enqueueAck(item.id);
  }

  private enqueueAck(id: string): void {
    this.ackChain = this.ackChain.then(() =>
      this.deps.ack(id).then(
        () => undefined,
        (error: unknown) => {
          this.deps.log?.(`notifications: could not acknowledge ${id}: ${String(error)}`);
        },
      ),
    );
  }

  /** Resolves once every acknowledgement queued so far has run. */
  acksSettled(): Promise<void> {
    return this.ackChain;
  }

  private update(patch: Partial<NotificationFeed>): void {
    this.feed = { ...this.feed, ...patch };
    this.deps.onFeedChange(this.feed);
  }
}

function byNewest(a: AppNotification, b: AppNotification): number {
  return b.ts - a.ts;
}

function singleNotice(item: AppNotification, openProject: (projectId: ProjectId) => void): NativeNotice {
  return {
    title: `${LEVEL_PREFIX[item.level]}${item.projectName}`,
    body: item.message,
    persistent: item.level === 'critical',
    onClick: () => openProject(item.projectId),
  };
}

/** One banner for a backlog: how many, from which projects; a click opens the newest. */
function summaryNotice(items: readonly AppNotification[], openProject: (projectId: ProjectId) => void): NativeNotice {
  const newest = [...items].sort(byNewest)[0]!;
  const projects = [...new Set(items.map((item) => item.projectName))];
  const where =
    projects.length <= 3 ? projects.join(', ') : `${projects.slice(0, 3).join(', ')} and ${projects.length - 3} more`;
  const critical = items.some((item) => item.level === 'critical');
  return {
    title: `${critical ? LEVEL_PREFIX.critical : ''}${items.length} notifications`,
    body: `From ${where}. They are all in the bell.`,
    persistent: critical,
    onClick: () => openProject(newest.projectId),
  };
}

function lastLine(text: string): string | null {
  const lines = text.trim().split(/\r?\n/).filter((line) => line.trim() !== '');
  const last = lines[lines.length - 1];
  return last === undefined ? null : last.replace(/^devteam: (error: )?/, '');
}
