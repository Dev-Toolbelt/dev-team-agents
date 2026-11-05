/**
 * The canvas: runs `devteam tasks graph` for a project on demand, and keeps it fresh while a
 * renderer is subscribed to that project.
 *
 * Unlike the board there is no stream: the graph is a one-shot read. A subscribed project is
 * re-read when the board reports a change for it (debounced, because one turn writes many
 * records) and on a slow poll, which catches what the board does not see (trace-only changes:
 * tokens, a last output). One read per project at a time; a change that lands during a read
 * queues exactly one more. A generation guard drops the answer of a read that was overtaken by
 * an unsubscribe or a dispose.
 *
 * Imports nothing from `electron`; `index.ts` injects the native pieces.
 */

import type {
  BoardFeed,
  BoardProject,
  OperationResult,
  ProjectId,
  TaskGraph,
  TaskGraphResult,
  TaskGraphUpdate,
} from '../shared/api.js';

export const GRAPH_DEBOUNCE_MS = 500;
export const GRAPH_POLL_MS = 10_000;

export interface TaskGraphDeps {
  /** One `tasks graph` for the project; `null` when there is no CLI to run it with. */
  readonly run: (projectId: ProjectId) => Promise<OperationResult<TaskGraph> | null>;
  /** A subscribed project's result changed. */
  readonly onChange: (update: TaskGraphUpdate) => void;
  readonly setTimer?: (fn: () => void, ms: number) => unknown;
  readonly clearTimer?: (handle: unknown) => void;
  readonly log?: (message: string) => void;
}

/**
 * An older CLI has no `graph` subcommand (or no `--project` on it): argparse's own wording,
 * which the CLI routes into a usage error document.
 */
const UNSUPPORTED = /invalid choice|unrecognized arguments/i;

/** What the renderer is told; the CLI's own message is kept as the detail. */
export function toTaskGraphResult(result: OperationResult<TaskGraph> | null): TaskGraphResult {
  if (result === null) return { ok: false, reason: 'unavailable', detail: 'No devteam CLI was found.' };
  if (result.ok) return { ok: true, graph: result.data };
  if (result.kind === 'unavailable') return { ok: false, reason: 'unavailable', detail: result.message };
  if (result.kind === 'usage' && UNSUPPORTED.test(result.message)) {
    return { ok: false, reason: 'unsupported', detail: 'The installed devteam CLI cannot draw the canvas yet; update it.' };
  }
  return { ok: false, reason: 'error', detail: result.hint === undefined ? result.message : `${result.message} ${result.hint}` };
}

interface Entry {
  subscribers: number;
  cached: TaskGraphResult | null;
  /** Serialized `cached`, so a poll that changed nothing pushes nothing. */
  cachedKey: string | null;
  inflight: Promise<TaskGraphResult> | null;
  /** A change arrived during the read in flight: read once more when it lands. */
  again: boolean;
  /** Bumped by unsubscribe-to-zero and dispose; a read of an older generation is dropped. */
  generation: number;
  debounce: unknown;
  poll: unknown;
}

export class TaskGraphRunner {
  private readonly entries = new Map<ProjectId, Entry>();
  /** The board's last project objects; a project whose object changed has a new snapshot. */
  private boardProjects = new Map<ProjectId, BoardProject>();
  private disposed = false;
  private readonly setTimer: (fn: () => void, ms: number) => unknown;
  private readonly clearTimer: (handle: unknown) => void;

  constructor(private readonly deps: TaskGraphDeps) {
    this.setTimer = deps.setTimer ?? ((fn, ms) => setTimeout(fn, ms));
    this.clearTimer = deps.clearTimer ?? ((handle) => clearTimeout(handle as NodeJS.Timeout));
  }

  /** The cached result of a subscribed project; otherwise a fresh read (nothing keeps an unwatched one fresh). */
  get(projectId: ProjectId): Promise<TaskGraphResult> {
    const entry = this.entries.get(projectId);
    if (entry === undefined || entry.subscribers === 0) return this.readOnce(projectId);
    if (entry.cached !== null) return Promise.resolve(entry.cached);
    return entry.inflight ?? this.read(projectId, entry);
  }

  subscribe(projectId: ProjectId): void {
    if (this.disposed) return;
    const entry = this.entry(projectId);
    entry.subscribers += 1;
    if (entry.subscribers > 1) return;
    this.armPoll(projectId, entry);
    // A cached answer may be old: the first subscriber always gets a fresh read.
    void this.refresh(projectId);
  }

  unsubscribe(projectId: ProjectId): void {
    const entry = this.entries.get(projectId);
    if (entry === undefined || entry.subscribers === 0) return;
    entry.subscribers -= 1;
    if (entry.subscribers > 0) return;
    this.idle(entry);
    // Keep nothing for a project nobody watches: the next `get` reads afresh.
    this.entries.delete(projectId);
  }

  subscribed(projectId: ProjectId): boolean {
    return (this.entries.get(projectId)?.subscribers ?? 0) > 0;
  }

  /** The board pushed a feed: re-read every subscribed project whose snapshot changed. */
  boardChanged(feed: BoardFeed): void {
    const next = new Map(feed.projects.map((project) => [project.project_id, project] as const));
    const changed = new Set<ProjectId>();
    for (const [id, project] of next) if (this.boardProjects.get(id) !== project) changed.add(id);
    for (const id of this.boardProjects.keys()) if (!next.has(id)) changed.add(id);
    this.boardProjects = next;
    for (const id of changed) this.schedule(id);
  }

  /** Re-read a subscribed project after the debounce; a burst of changes costs one read. */
  schedule(projectId: ProjectId): void {
    const entry = this.entries.get(projectId);
    if (this.disposed || entry === undefined || entry.subscribers === 0) return;
    if (entry.debounce !== null) this.clearTimer(entry.debounce);
    entry.debounce = this.setTimer(() => {
      entry.debounce = null;
      void this.refresh(projectId);
    }, GRAPH_DEBOUNCE_MS);
  }

  dispose(): void {
    this.disposed = true;
    for (const entry of this.entries.values()) this.idle(entry);
    this.entries.clear();
  }

  private entry(projectId: ProjectId): Entry {
    let entry = this.entries.get(projectId);
    if (entry === undefined) {
      entry = { subscribers: 0, cached: null, cachedKey: null, inflight: null, again: false, generation: 0, debounce: null, poll: null };
      this.entries.set(projectId, entry);
    }
    return entry;
  }

  private refresh(projectId: ProjectId): Promise<TaskGraphResult> | null {
    const entry = this.entries.get(projectId);
    if (this.disposed || entry === undefined) return null;
    if (entry.inflight !== null) {
      entry.again = true;
      return entry.inflight;
    }
    return this.read(projectId, entry);
  }

  /** A read for a project nobody watches: answered, never cached. */
  private readOnce(projectId: ProjectId): Promise<TaskGraphResult> {
    return this.deps
      .run(projectId)
      .then(toTaskGraphResult, (error: unknown): TaskGraphResult => ({ ok: false, reason: 'error', detail: String(error) }));
  }

  private read(projectId: ProjectId, entry: Entry): Promise<TaskGraphResult> {
    const generation = entry.generation;
    const current = (): boolean => !this.disposed && this.entries.get(projectId) === entry && entry.generation === generation;
    const pending = this.readOnce(projectId)
      .then((result) => {
        if (!current()) return result;
        entry.inflight = null;
        this.store(projectId, entry, result);
        if (entry.again) {
          entry.again = false;
          if (entry.subscribers > 0) void this.read(projectId, entry);
        }
        return result;
      });
    entry.inflight = pending;
    return pending;
  }

  private store(projectId: ProjectId, entry: Entry, result: TaskGraphResult): void {
    // A failed re-read keeps the last good graph on screen; the failure is logged, not pushed.
    if (!result.ok && entry.cached?.ok === true && result.reason === 'error') {
      this.deps.log?.(`task graph: re-read of ${projectId} failed: ${result.detail ?? 'unknown error'}`);
      return;
    }
    const key = JSON.stringify(result);
    if (key === entry.cachedKey) return;
    entry.cached = result;
    entry.cachedKey = key;
    if (entry.subscribers > 0) this.deps.onChange({ projectId, result });
  }

  private armPoll(projectId: ProjectId, entry: Entry): void {
    if (entry.poll !== null) this.clearTimer(entry.poll);
    entry.poll = this.setTimer(() => {
      entry.poll = null;
      if (this.disposed || entry.subscribers === 0 || this.entries.get(projectId) !== entry) return;
      void this.refresh(projectId);
      this.armPoll(projectId, entry);
    }, GRAPH_POLL_MS);
  }

  private idle(entry: Entry): void {
    entry.generation += 1;
    entry.subscribers = 0;
    entry.inflight = null;
    entry.again = false;
    if (entry.debounce !== null) this.clearTimer(entry.debounce);
    if (entry.poll !== null) this.clearTimer(entry.poll);
    entry.debounce = null;
    entry.poll = null;
  }
}
