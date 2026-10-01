/**
 * The task board: supervises `devteam tasks watch`, keeps the latest snapshot of every
 * project that has tasks, and pushes the merged feed to the renderer.
 *
 * Same shape and same reasons as `notifications.ts` — one long-lived child in the main
 * process rather than polling `tasks list`, a doubling restart backoff that only resets
 * once a child has stayed healthy, a heartbeat watchdog, and exit 3 as "retrying cannot
 * fix this". It differs in one place: the stream carries **state**, not events. Each
 * `snapshot` replaces one project; a project that no longer has tasks arrives as a
 * removal. A restarted stream re-sends every project before `ready`, so those are held
 * apart and swapped in at `ready` — a project that vanished while the stream was down
 * disappears then, instead of lingering forever.
 *
 * Imports nothing from `electron`; `index.ts` injects the native pieces.
 */

import type { StreamEnd, StreamHandle } from '../cli/stream.js';
import { TaskStreamRefused, type TaskWatchEvent } from '../cli/operations.js';
import type { BoardFeed, BoardProject, BoardSettings, BoardStreamStatus, OperationResult, ProjectId } from '../shared/api.js';

export const BOARD_BACKOFF_MIN_MS = 1_000;
export const BOARD_BACKOFF_MAX_MS = 60_000;
/** A child must stay up this long after `ready` before the backoff resets. */
export const BOARD_HEALTHY_MS = 30_000;
/** `watch` sends a heartbeat every 30 s; silence for three of them means it is hung. */
export const BOARD_WATCHDOG_MS = 90_000;

export interface TaskBoardDeps {
  /** Start the stream; `null` when there is no CLI to run it with yet. */
  readonly startStream: (handlers: {
    readonly onEvent: (event: TaskWatchEvent) => void;
    readonly onInvalid: (detail: string) => void;
    readonly onEnd: (end: StreamEnd) => void;
  }) => Promise<StreamHandle | null>;
  /** One-shot `tasks list`, for a manual refresh. */
  readonly list: () => Promise<OperationResult<{ readonly projects: readonly BoardProject[] }>>;
  readonly onChange: (feed: BoardFeed) => void;
  readonly setTimer?: (fn: () => void, ms: number) => unknown;
  readonly clearTimer?: (handle: unknown) => void;
  readonly log?: (message: string) => void;
}

export class TaskBoard {
  private status: BoardStreamStatus = 'starting';
  private detail: string | null = null;
  private projects = new Map<ProjectId, BoardProject>();
  /** Snapshots received before this stream's `ready`; they replace `projects` at `ready`. */
  private incoming: Map<ProjectId, BoardProject> | null = null;
  private handle: StreamHandle | null = null;
  private stopped = false;
  /** Terminal: set when the app is quitting; nothing may spawn a child afterwards. */
  private disposed = false;
  /** Bumped whenever the stream changes `projects`; a `refresh` that raced it yields. */
  private streamRevision = 0;
  private backoff = BOARD_BACKOFF_MIN_MS;
  private retryTimer: unknown = null;
  private watchdogTimer: unknown = null;
  private healthyTimer: unknown = null;
  private streamError: string | null = null;
  private spawning = false;
  private refreshing: Promise<BoardFeed> | null = null;
  /** Bumped by every spawn, restart and stop; a stale child's events and exit are ignored. */
  private generation = 0;
  private readonly setTimer: (fn: () => void, ms: number) => unknown;
  private readonly clearTimer: (handle: unknown) => void;

  constructor(private readonly deps: TaskBoardDeps) {
    this.setTimer = deps.setTimer ?? ((fn, ms) => setTimeout(fn, ms));
    this.clearTimer = deps.clearTimer ?? ((handle) => clearTimeout(handle as NodeJS.Timeout));
  }

  snapshot(): BoardFeed {
    const projects = [...this.projects.values()].sort((a, b) => b.last_activity_at - a.last_activity_at);
    return { status: this.status, detail: this.detail, projects };
  }

  async start(): Promise<void> {
    if (this.disposed) return;
    this.stopped = false;
    if (this.handle !== null || this.spawning) return;
    await this.spawn();
  }

  stop(): void {
    this.stopped = true;
    this.generation += 1;
    this.spawning = false;
    this.clearRetry();
    this.clearWatchdog();
    this.clearHealthy();
    this.handle?.stop();
    this.handle = null;
  }

  /** The app is quitting: stop, and refuse every later `start` or `restart`. */
  dispose(): void {
    this.disposed = true;
    this.stop();
  }

  /** The CLI or the stale threshold changed: drop the child and start again now. */
  async restart(): Promise<void> {
    if (this.disposed) return;
    this.generation += 1;
    this.handle?.stop();
    this.handle = null;
    this.clearRetry();
    this.clearWatchdog();
    this.clearHealthy();
    this.backoff = BOARD_BACKOFF_MIN_MS;
    this.stopped = false;
    await this.spawn();
  }

  /** A one-shot `tasks list` that replaces every snapshot. A failure leaves them as they were. */
  refresh(): Promise<BoardFeed> {
    // Overlapping calls share one `list`: two answers could otherwise land out of order.
    this.refreshing ??= this.doRefresh().finally(() => {
      this.refreshing = null;
    });
    return this.refreshing;
  }

  private async doRefresh(): Promise<BoardFeed> {
    const revision = this.streamRevision;
    const result = await this.deps.list().catch(() => null);
    if (result !== null && result.ok && revision !== this.streamRevision) {
      // The stream applied newer snapshots while `list` was running; this answer is older.
      this.deps.log?.('task board: refresh skipped, the stream delivered newer data meanwhile');
    } else if (result !== null && result.ok) {
      this.projects = new Map(result.data.projects.map((project) => [project.project_id, project] as const));
      this.emit();
    } else if (result !== null) {
      this.deps.log?.(`task board: refresh failed: ${result.message}`);
    }
    return this.snapshot();
  }

  // ── the stream ────────────────────────────────────────────────────────────

  private async spawn(): Promise<void> {
    if (this.stopped || this.disposed) return;
    this.generation += 1;
    const generation = this.generation;
    const current = () => generation === this.generation && !this.stopped;
    this.incoming = new Map();
    this.streamError = null;
    // A restart keeps the data-bearing status: flipping to `starting` would flash "Waiting
    // for the first snapshot" over a board that still has its last good snapshots.
    if (this.status !== 'live' && this.status !== 'retrying') this.set({ status: 'starting' });
    let handle: StreamHandle | null;
    this.spawning = true;
    try {
      handle = await this.deps.startStream({
        onEvent: (event) => {
          if (current()) this.onEvent(event);
        },
        onInvalid: (detail) => this.deps.log?.(`task board: ignored an event: ${detail}`),
        onEnd: (end) => {
          if (current()) this.onEnd(end);
        },
      });
    } catch (error) {
      if (current() && error instanceof TaskStreamRefused) {
        // Deterministic: the same argv is refused on every retry, so do not loop.
        this.set({ status: 'unavailable', detail: `The task stream could not be started: ${error.message}.` });
        return;
      }
      if (current()) this.scheduleRetry(`the task stream could not start: ${String(error)}`);
      return;
    } finally {
      if (generation === this.generation) this.spawning = false;
    }
    if (!current()) {
      handle?.stop();
      return;
    }
    if (handle === null) {
      this.set({ status: 'unavailable', detail: 'No devteam CLI was found, so there is nothing to watch.' });
      return;
    }
    this.handle = handle;
    this.armWatchdog();
  }

  private onEvent(event: TaskWatchEvent): void {
    this.armWatchdog();
    switch (event.event) {
      case 'snapshot':
        if (this.incoming !== null) this.incoming.set(event.project.project_id, event.project);
        else {
          this.streamRevision += 1;
          this.projects.set(event.project.project_id, event.project);
          this.emit();
        }
        return;
      case 'removed':
        if (this.incoming !== null) this.incoming.delete(event.projectId);
        else if (this.projects.delete(event.projectId)) {
          this.streamRevision += 1;
          this.emit();
        }
        return;
      case 'ready':
        if (this.incoming !== null) {
          this.streamRevision += 1;
          this.projects = this.incoming;
          this.incoming = null;
        }
        this.set({ status: 'live', detail: null });
        this.clearHealthy();
        this.healthyTimer = this.setTimer(() => {
          this.healthyTimer = null;
          this.backoff = BOARD_BACKOFF_MIN_MS;
        }, BOARD_HEALTHY_MS);
        return;
      case 'heartbeat':
      case 'end':
        return; // `onEnd` follows when the process closes.
      case 'error':
        this.streamError = event.hint === null ? event.message : `${event.message} ${event.hint}`;
        return;
    }
  }

  private onEnd(end: StreamEnd): void {
    this.clearWatchdog();
    this.clearHealthy();
    this.handle = null;
    // A stream that died before `ready` never got to replace the last good snapshots.
    this.incoming = null;
    if (this.stopped) return;
    if (end.kind === 'exited' && end.code === 3) {
      const reason = this.streamError ?? lastLine(end.stderr) ?? 'environment error (exit 3)';
      this.set({ status: 'unavailable', detail: `devteam could not watch tasks: ${reason}` });
      return;
    }
    const said = this.streamError === null ? '' : `: ${this.streamError}`;
    const why =
      end.kind === 'exited'
        ? `the task stream stopped (exit ${end.code ?? end.signal ?? '?'})${said}`
        : end.kind === 'protocol'
          ? `the task stream sent something unexpected: ${end.detail}`
          : `the task stream could not start: ${end.detail}`;
    this.scheduleRetry(why);
  }

  private scheduleRetry(detail: string): void {
    if (this.stopped) return;
    const delay = this.backoff;
    this.backoff = Math.min(this.backoff * 2, BOARD_BACKOFF_MAX_MS);
    this.set({ status: 'retrying', detail: `${detail}. Retrying in ${Math.round(delay / 1000)} s.` });
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
      this.deps.log?.('task board: no event in 90 s — restarting the stream');
      this.handle?.stop();
    }, BOARD_WATCHDOG_MS);
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

  private set(patch: { readonly status?: BoardStreamStatus; readonly detail?: string | null }): void {
    if (patch.status !== undefined) this.status = patch.status;
    if (patch.detail !== undefined) this.detail = patch.detail;
    else if (patch.status === 'live' || patch.status === 'starting') this.detail = null;
    this.emit();
  }

  private emit(): void {
    this.deps.onChange(this.snapshot());
  }
}

export interface BoardSettingsStore {
  readonly read: () => Promise<BoardSettings>;
  readonly write: (settings: BoardSettings) => Promise<void>;
  readonly restartStream: () => void;
}

/**
 * Persist the board settings and apply them. `--stale-after` is an argument of the running
 * child, so only a changed stale threshold needs a new stream; a retention-only save must
 * leave the stream alone (a restart would blank "live" for nothing).
 */
export async function saveBoardSettings(store: BoardSettingsStore, next: BoardSettings): Promise<BoardSettings> {
  const previous = await store.read();
  await store.write(next);
  if (previous.staleAfterMinutes !== next.staleAfterMinutes) store.restartStream();
  return store.read();
}

function lastLine(text: string): string | null {
  const lines = text.trim().split(/\r?\n/).filter((line) => line.trim() !== '');
  const last = lines[lines.length - 1];
  return last === undefined ? null : last.replace(/^devteam: (error: )?/, '');
}
