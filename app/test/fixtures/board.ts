/**
 * Builders for the task-board payload. The types in `shared/api.ts` are the CLI's JSON
 * shape as it arrives (snake_case), so the same objects serve as a raw document in the
 * main-process tests and as a parsed one in the renderer tests.
 */
import type { BoardCounts, BoardProject, BoardSession, BoardTask } from '../../src/shared/api.js';

export const NOW = 1_790_000_000;

export function counts(todo: number, inProgress: number, done: number, inReview = 0, prCreated = 0): BoardCounts {
  return {
    todo,
    in_progress: inProgress,
    in_review: inReview,
    pr_created: prCreated,
    done,
    total: todo + inProgress + inReview + prCreated + done,
  };
}

export function boardTask(overrides: Partial<BoardTask> = {}): BoardTask {
  return {
    key: 't1',
    content: 'Write the migration',
    owner: 'main',
    agent_type: null,
    status: 'pending',
    column: 'todo',
    created_at: NOW - 600,
    status_since: NOW - 120,
    completed_at: null,
    durations: { pending: 120, in_progress: 0, completed: 0 },
    stale: false,
    abandoned: false,
    kind: 'todo',
    failed: false,
    review: null,
    worktree: null,
    turns: [],
    pr: null,
    refs: [],
    ...overrides,
  };
}

/** A session whose counts are derived from its tasks, so the two cannot disagree. */
export function boardSession(overrides: Partial<BoardSession> & { tasks?: readonly BoardTask[] } = {}): BoardSession {
  const tasks = overrides.tasks ?? [boardTask()];
  const derived = counts(
    tasks.filter((t) => t.column === 'todo').length,
    tasks.filter((t) => t.column === 'in_progress').length,
    tasks.filter((t) => t.column === 'done').length,
    tasks.filter((t) => t.column === 'in_review').length,
    tasks.filter((t) => t.column === 'pr_created').length,
  );
  return {
    session_id: 'session-aaaaaaaa',
    title: null,
    provider: 'claude',
    branch: 'feat/login',
    cwd: '/repo/storefront',
    status: 'active',
    created_at: NOW - 3600,
    last_activity_at: NOW - 60,
    ended_at: null,
    resume_command: "cd '/repo/storefront' && claude --resume 'session-aaaaaaaa'",
    counts: derived,
    prs: [],
    ...overrides,
    tasks,
  };
}

/** A project whose totals are derived from its sessions. */
export function boardProject(overrides: Partial<BoardProject> & { sessions?: readonly BoardSession[] } = {}): BoardProject {
  const sessions = overrides.sessions ?? [boardSession()];
  const total = counts(
    sessions.reduce((n, s) => n + s.counts.todo, 0),
    sessions.reduce((n, s) => n + s.counts.in_progress, 0),
    sessions.reduce((n, s) => n + s.counts.done, 0),
    sessions.reduce((n, s) => n + s.counts.in_review, 0),
    sessions.reduce((n, s) => n + s.counts.pr_created, 0),
  );
  const tasks = sessions.flatMap((s) => s.tasks);
  return {
    project_id: 'proj-a',
    root: '/repo/storefront',
    providers: [...new Set(sessions.map((s) => s.provider))],
    sessions_total: sessions.length,
    sessions_active: sessions.filter((s) => s.status === 'active').length,
    counts: total,
    stale: tasks.filter((t) => t.stale).length,
    abandoned: tasks.filter((t) => t.abandoned).length,
    with_findings: tasks.filter((t) => t.review?.state === 'findings').length,
    last_activity_at: Math.max(0, ...sessions.map((s) => s.last_activity_at)),
    link_hosts: [],
    ...overrides,
    sessions,
  };
}

/** `n` tasks split as evenly as possible across the columns, with unique keys. */
export function tasksOf(prefix: string, todo: number, inProgress: number, done: number, inReview = 0): BoardTask[] {
  const out: BoardTask[] = [];
  let index = 0;
  const make = (column: 'todo' | 'in_progress' | 'in_review' | 'pr_created' | 'done', status: string) => {
    index += 1;
    out.push(
      boardTask({
        key: `${prefix}${index}`,
        content: `${prefix} task ${index}`,
        column,
        status,
        created_at: NOW - 1000 + index,
        completed_at: column === 'done' ? NOW - 30 : null,
        status_since: NOW - 30,
        review: column === 'in_review' ? { state: 'pending', findings: null, since: NOW - 30 } : null,
      }),
    );
  };
  for (let i = 0; i < todo; i += 1) make('todo', 'pending');
  for (let i = 0; i < inProgress; i += 1) make('in_progress', 'in_progress');
  for (let i = 0; i < inReview; i += 1) make('in_review', 'in_progress');
  for (let i = 0; i < done; i += 1) make('done', 'completed');
  return out;
}

/** The one "Direct work" card of a session, with the prompts behind it (oldest first). */
export function directTask(overrides: Partial<BoardTask> = {}): BoardTask {
  return boardTask({
    key: 'direct',
    content: 'Direct work',
    kind: 'direct',
    status: 'in_progress',
    column: 'in_progress',
    turns: [
      { text: 'rename the helper', at: NOW - 300 },
      { text: '', at: NOW - 200 },
      { text: 'fix the typo in the readme', at: NOW - 100 },
    ],
    ...overrides,
  });
}
