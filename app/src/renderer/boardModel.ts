/**
 * The task board's pure derivations: durations in words, the period filter, and the
 * per-project view that filter produces. No React and no clock of its own — `now` is always
 * passed in — so every rule here is testable without rendering.
 *
 * The CLI derives the facts (`column`, `stale`, `abandoned`, `durations`); the board only
 * narrows and formats them. Nothing here recomputes a stale or abandoned flag.
 */

import type { BoardCounts, BoardProject, BoardSession, BoardTask } from '../shared/api.js';

export type Period = 'today' | '7d' | '30d' | 'all';

export const PERIODS: readonly { readonly value: Period; readonly label: string }[] = [
  { value: 'today', label: 'Today' },
  { value: '7d', label: 'Last 7 days' },
  { value: '30d', label: 'Last 30 days' },
  { value: 'all', label: 'All time' },
];

const DAY = 86_400;

/** Epoch seconds a period starts at, or `null` for all time. `today` is local midnight. */
export function periodCutoff(period: Period, nowSeconds: number): number | null {
  switch (period) {
    case 'all':
      return null;
    case 'today': {
      const midnight = new Date(nowSeconds * 1000);
      midnight.setHours(0, 0, 0, 0);
      return Math.floor(midnight.getTime() / 1000);
    }
    case '7d':
      return nowSeconds - 7 * DAY;
    case '30d':
      return nowSeconds - 30 * DAY;
  }
}

/**
 * `45s`, `12m 30s`, `2h 5m`, `1d 3h`: at most two units, the smaller one omitted when it
 * is zero. Whole seconds; a negative or non-finite value reads as `0s`.
 */
export function formatDuration(seconds: number): string {
  const total = Number.isFinite(seconds) ? Math.max(0, Math.floor(seconds)) : 0;
  const units: readonly [string, number][] = [
    ['d', DAY],
    ['h', 3600],
    ['m', 60],
    ['s', 1],
  ];
  for (let i = 0; i < units.length; i += 1) {
    const [name, size] = units[i]!;
    if (total < size && name !== 's') continue;
    const head = Math.floor(total / size);
    const next = units[i + 1];
    if (next === undefined) return `${head}${name}`;
    const rest = Math.floor((total % size) / next[1]);
    return rest === 0 ? `${head}${name}` : `${head}${name} ${rest}${next[0]}`;
  }
  return '0s';
}

/**
 * `formatDuration` for figures that refresh once a minute: from one minute up the seconds are
 * dropped (`12m`, `2h 5m`), since they would be a minute stale; under a minute they stay.
 */
export function formatDurationMinutes(seconds: number): string {
  const total = Number.isFinite(seconds) ? Math.max(0, Math.floor(seconds)) : 0;
  return formatDuration(total < 60 ? total : Math.floor(total / 60) * 60);
}

/**
 * A moment as date plus `HH:mm` in the viewer's locale (`02/10/2026 10:47` under pt-BR), 24-hour
 * clock. `locale` and `timeZone` exist for the tests; the app passes neither.
 */
export function formatDateTime(epochSeconds: number, locale?: string, timeZone?: string): string {
  const at = new Date(epochSeconds * 1000);
  const zone = timeZone !== undefined ? { timeZone } : {};
  // Two formatters joined by a space: one combined format puts a locale's own separator
  // (`02/10/2026, 10:47`) between the halves.
  const date = new Intl.DateTimeFormat(locale, { day: '2-digit', month: '2-digit', year: 'numeric', ...zone }).format(at);
  const time = new Intl.DateTimeFormat(locale, { hour: '2-digit', minute: '2-digit', hourCycle: 'h23', ...zone }).format(at);
  return `${date} ${time}`;
}

/** Tasks the CLI counts in these sessions that were not parsed into a card (unknown column and status). */
export function countUnshown(sessions: readonly BoardSession[]): number {
  return sessions.reduce((n, session) => n + Math.max(0, session.counts.total - session.tasks.length), 0);
}

export function percent(part: number, total: number): number {
  return total <= 0 ? 0 : Math.round((part / total) * 100);
}

/**
 * The five percentages of a counts row (to do, in progress, in review, PR/MR created, done), by the
 * largest-remainder method, so they always sum to 100 (independent rounding turns 1/1/1 into
 * 33+33+33). All zero when nothing counts.
 */
export function percentLabels(counts: BoardCounts): readonly [number, number, number, number, number] {
  const parts = [counts.todo, counts.in_progress, counts.in_review, counts.pr_created, counts.done] as const;
  const total = parts.reduce((a, b) => a + b, 0);
  if (total <= 0) return [0, 0, 0, 0, 0];
  const exact = parts.map((part) => (part * 100) / total);
  const floors = exact.map(Math.floor);
  let left = 100 - floors.reduce((a, b) => a + b, 0);
  const order = [0, 1, 2, 3, 4].sort((a, b) => exact[b]! - floors[b]! - (exact[a]! - floors[a]!) || a - b);
  for (const index of order) {
    if (left <= 0) break;
    floors[index]! += 1;
    left -= 1;
  }
  return [floors[0]!, floors[1]!, floors[2]!, floors[3]!, floors[4]!];
}

export const STEP_LABELS: Readonly<Record<string, string>> = {
  pending: 'To do',
  in_progress: 'In progress',
  in_review: 'In Review',
  pr_created: 'PR/MR Created',
  completed: 'Done',
  cancelled: 'Cancelled',
};

export function stepLabel(status: string): string {
  return STEP_LABELS[status] ?? status.replace(/_/g, ' ');
}

const STEP_ORDER = ['pending', 'in_progress', 'in_review', 'pr_created', 'completed', 'cancelled'];

/** The step a task is in: the review window or the PR/MR column when it is there, else the provider's own status. */
function currentStep(task: BoardTask): string {
  return task.column === 'in_review' || task.column === 'pr_created' ? task.column : task.status;
}

/**
 * The current step's figure when the CLI stamped its snapshot (`as_of`): its own number for
 * that step plus the time since it spoke, while the task runs; frozen at its number otherwise.
 * The CLI partitions a task's lifetime, so this is the whole story and no other clock enters.
 */
function liveFromSnapshot(task: BoardTask, nowSeconds: number, running: boolean, asOf: number): number {
  const base = task.durations[currentStep(task)] ?? 0;
  return running ? base + Math.max(0, nowSeconds - asOf) : base;
}

/**
 * How long a task has been in its current column. With `asOf` (the CLI's snapshot time) it is
 * the same figure `stepDurations` shows on the current row, so headline and hover agree. Without
 * it (an older CLI) a running task grows from its column's start; anything else stopped growing
 * when its session ended (or, without an end time, at the session's last activity).
 */
export function timeInColumn(
  session: BoardSession,
  task: BoardTask,
  nowSeconds: number,
  running: boolean,
  asOf?: number,
): number {
  if (asOf !== undefined) return liveFromSnapshot(task, nowSeconds, running, asOf);
  const until = running ? nowSeconds : (session.ended_at ?? session.last_activity_at);
  return Math.max(0, until - (task.column === 'in_review' && task.review !== null ? task.review.since : task.status_since));
}

/**
 * Time per step, in the order a task moves through them. With `asOf`, only the current step
 * is live (CLI figure plus time since `as_of`) and every other row stays at the CLI's figure.
 * Without it (an older CLI), the current row is read from `currentSeconds` (see `timeInColumn`)
 * when longer than the CLI's figure, minus review time when the step is `in_progress`, since
 * `status_since` predates any review window the task came back from.
 */
export function stepDurations(
  task: BoardTask,
  nowSeconds: number,
  running: boolean,
  currentSeconds?: number,
  asOf?: number,
): readonly { readonly status: string; readonly label: string; readonly seconds: number; readonly current: boolean }[] {
  const merged: Record<string, number> = { ...task.durations };
  const step = currentStep(task);
  if (asOf !== undefined) {
    merged[step] = liveFromSnapshot(task, nowSeconds, running, asOf);
  } else {
    const since = task.column === 'in_review' && task.review !== null ? task.review.since : task.status_since;
    let live = currentSeconds ?? (running ? nowSeconds - since : undefined);
    if (live !== undefined && step === 'in_progress') live = Math.max(0, live - (merged['in_review'] ?? 0));
    if (live !== undefined) merged[step] = Math.max(merged[step] ?? 0, live);
  }
  const statuses = Object.keys(merged).sort((a, b) => rank(a) - rank(b));
  return statuses
    .filter((status) => (merged[status] ?? 0) > 0 || status === step)
    .map((status) => ({
      status,
      label: stepLabel(status),
      seconds: merged[status] ?? 0,
      current: status === step,
    }));
}

function rank(status: string): number {
  const index = STEP_ORDER.indexOf(status);
  return index === -1 ? STEP_ORDER.length : index;
}

/** A session is running while it is not ended; only then does a task's current step keep growing. */
export function isRunning(session: BoardSession, task: BoardTask): boolean {
  return session.status !== 'ended' && task.column !== 'done';
}

// ── the per-project view under a period filter ────────────────────────────────

export interface ProjectView {
  readonly project: BoardProject;
  readonly sessions: readonly BoardSession[];
  readonly providers: readonly string[];
  readonly sessionsTotal: number;
  readonly sessionsActive: number;
  readonly counts: BoardCounts;
  readonly stale: number;
  readonly abandoned: number;
  readonly withFindings: number;
}

function sumCounts(sessions: readonly BoardSession[]): BoardCounts {
  const counts = { todo: 0, in_progress: 0, in_review: 0, pr_created: 0, done: 0, total: 0 };
  for (const session of sessions) {
    counts.todo += session.counts.todo;
    counts.in_progress += session.counts.in_progress;
    counts.in_review += session.counts.in_review;
    counts.pr_created += session.counts.pr_created;
    counts.done += session.counts.done;
    counts.total += session.counts.total;
  }
  return counts;
}

/** Sessions whose last activity falls inside the period. */
export function sessionsInPeriod(project: BoardProject, period: Period, nowSeconds: number): readonly BoardSession[] {
  const cutoff = periodCutoff(period, nowSeconds);
  return cutoff === null ? project.sessions : project.sessions.filter((session) => session.last_activity_at >= cutoff);
}

/**
 * The project as the period sees it, or `null` when nothing in it has a task in that
 * period. Over all time the CLI's own project figures are used as they are; a narrower
 * period recomputes them from the sessions that remain.
 */
export function viewProject(project: BoardProject, period: Period, nowSeconds: number): ProjectView | null {
  const sessions = sessionsInPeriod(project, period, nowSeconds);
  const whole = sessions.length === project.sessions.length;
  const counts = whole ? project.counts : sumCounts(sessions);
  if (counts.total === 0) return null;
  const tasks = sessions.flatMap((session) => session.tasks);
  const providers = whole && project.providers.length > 0 ? project.providers : [...new Set(sessions.map((s) => s.provider))];
  return {
    project,
    sessions,
    providers,
    sessionsTotal: whole ? project.sessions_total : sessions.length,
    sessionsActive: whole ? project.sessions_active : sessions.filter((s) => s.status === 'active').length,
    counts,
    stale: whole ? project.stale : tasks.filter((task) => task.stale).length,
    abandoned: whole ? project.abandoned : tasks.filter((task) => task.abandoned).length,
    withFindings: whole ? project.with_findings : tasks.filter(hasFindings).length,
  };
}

/** Tasks in review with findings among the sessions given. */
export function countFindings(sessions: readonly BoardSession[]): number {
  return sessions.reduce((n, session) => n + session.tasks.filter(hasFindings).length, 0);
}

/** A task sitting in review with findings to fix. */
export function hasFindings(task: BoardTask): boolean {
  return task.column === 'in_review' && task.review?.state === 'findings';
}

// ── the kanban ────────────────────────────────────────────────────────────────

export interface KanbanFilters {
  /** A session id, or `all`. */
  readonly sessionId: string;
  readonly period: Period;
  /** Hide done tasks completed longer ago than `retentionDays`. */
  readonly hideOldDone: boolean;
  readonly retentionDays: number;
  /** Only tasks in review with findings. Optional so a caller that predates the filter keeps working. */
  readonly onlyFindings?: boolean;
  /**
   * Hide a "Direct work" card left in To Do — a turn that only read, a question nobody came back
   * to — once its last turn is older than this. Hidden, never deleted: a new turn brings it back.
   * Optional: a caller that predates it hides nothing.
   */
  readonly directTodoTtlHours?: number;
}

export interface KanbanItem {
  readonly session: BoardSession;
  readonly task: BoardTask;
}

export interface KanbanView {
  readonly todo: readonly KanbanItem[];
  readonly in_progress: readonly KanbanItem[];
  readonly in_review: readonly KanbanItem[];
  readonly pr_created: readonly KanbanItem[];
  readonly done: readonly KanbanItem[];
  /** Done tasks the retention setting is hiding. */
  readonly hiddenDone: number;
  /** "Direct work" cards in To Do the lifetime setting is hiding. */
  readonly hiddenDirect: number;
}

export function buildKanban(project: BoardProject, filters: KanbanFilters, nowSeconds: number): KanbanView {
  const sessions = sessionsInPeriod(project, filters.period, nowSeconds).filter(
    (session) => filters.sessionId === 'all' || session.session_id === filters.sessionId,
  );
  const items: KanbanItem[] = sessions.flatMap((session) => session.tasks.map((task) => ({ session, task })));
  const doneCutoff = nowSeconds - filters.retentionDays * DAY;
  let hiddenDone = 0;
  let hiddenDirect = 0;
  const visible = items.filter(({ task }) => {
    if (filters.onlyFindings === true && !hasFindings(task)) return false;
    if (isExpiredDirectTodo(task, filters.directTodoTtlHours, nowSeconds)) {
      hiddenDirect += 1;
      return false;
    }
    if (task.column !== 'done' || !filters.hideOldDone) return true;
    const finished = task.completed_at ?? task.status_since;
    if (finished >= doneCutoff) return true;
    hiddenDone += 1;
    return false;
  });
  const byCreated = (a: KanbanItem, b: KanbanItem) => a.task.created_at - b.task.created_at;
  return {
    todo: visible.filter((i) => i.task.column === 'todo').sort(byCreated),
    in_progress: visible.filter((i) => i.task.column === 'in_progress').sort(byCreated),
    in_review: visible.filter((i) => i.task.column === 'in_review').sort(byCreated),
    pr_created: visible.filter((i) => i.task.column === 'pr_created').sort(byCreated),
    done: visible
      .filter((i) => i.task.column === 'done')
      .sort((a, b) => (b.task.completed_at ?? b.task.status_since) - (a.task.completed_at ?? a.task.status_since)),
    hiddenDone,
    hiddenDirect,
  };
}

/** A "Direct work" card in To Do whose last turn is older than `ttlHours`. */
export function isExpiredDirectTodo(task: BoardTask, ttlHours: number | undefined, nowSeconds: number): boolean {
  if (ttlHours === undefined || task.kind !== 'direct' || task.column !== 'todo') return false;
  const lastTurn = task.turns.reduce((latest, turn) => Math.max(latest, turn.at), 0);
  return nowSeconds - Math.max(task.status_since, lastTurn) > ttlHours * 3600;
}

/** The last path segment, POSIX or Windows. */
export function basename(path: string): string {
  const trimmed = path.replace(/[/\\]+$/, '');
  const last = trimmed.split(/[/\\]/).pop();
  return last !== undefined && last !== '' ? last : path;
}

/** The app-local name, else the directory's basename, else the id — never a bare UUID when a path exists. */
export function boardProjectName(project: BoardProject, names: Readonly<Record<string, string>>): string {
  return names[project.project_id] ?? (project.root !== '' ? basename(project.root) : project.project_id);
}

/** An agent task reads `<agent>: <description>`; the badge takes the name only when that split is clean. */
export function splitAgentTask(content: string): { agent: string; title: string } | null {
  const at = content.indexOf(': ');
  if (at <= 0) return null;
  const agent = content.slice(0, at);
  const title = content.slice(at + 2).trim();
  if (title === '' || agent.length > 64 || /\s/.test(agent)) return null;
  return { agent, title };
}
