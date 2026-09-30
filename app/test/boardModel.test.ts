/**
 * The board's pure derivations: durations in words, the period filter, the per-project view
 * and the kanban. No DOM, no clock — `now` is always an argument.
 */
import { describe, expect, it } from 'vitest';

import {
  boardProjectName,
  buildKanban,
  countUnshown,
  formatDuration,
  formatDurationMinutes,
  percent,
  percentLabels,
  timeInColumn,
  periodCutoff,
  stepDurations,
  viewProject,
} from '../src/renderer/boardModel.js';
import { NOW, boardProject, boardSession, boardTask, tasksOf } from './fixtures/board.js';

describe('formatDurationMinutes', () => {
  it.each([
    [0, '0s'],
    [59, '59s'],
    [60, '1m'],
    [752, '12m'],
    [7530, '2h 5m'],
    [90_061, '1d 1h'],
    [-4, '0s'],
    [Number.NaN, '0s'],
  ])('formats %s as %s', (seconds, expected) => {
    expect(formatDurationMinutes(seconds)).toBe(expected);
  });
});

describe('countUnshown', () => {
  it('sums what each session counts beyond its cards, never below zero', () => {
    const a = boardSession({ tasks: [boardTask({ key: 'a' })] });
    const b = boardSession({ session_id: 'b', tasks: [boardTask({ key: 'b' })] });
    expect(countUnshown([a, { ...b, counts: { ...b.counts, total: 4 } }])).toBe(3);
    expect(countUnshown([{ ...a, counts: { ...a.counts, total: 0 } }])).toBe(0);
  });
});

describe('formatDuration', () => {
  it.each([
    [0, '0s'],
    [45, '45s'],
    [59, '59s'],
    [60, '1m'],
    [125, '2m 5s'],
    [3600, '1h'],
    [7500, '2h 5m'],
    [86_400, '1d'],
    [97_200, '1d 3h'],
    [-5, '0s'],
    [Number.NaN, '0s'],
    [12.9, '12s'],
  ])('%s seconds reads %s', (seconds, expected) => {
    expect(formatDuration(seconds)).toBe(expected);
  });
});

describe('percent', () => {
  it('rounds, and is 0 for an empty total', () => {
    expect(percent(3, 10)).toBe(30);
    expect(percent(1, 3)).toBe(33);
    expect(percent(0, 0)).toBe(0);
  });
});

describe('percentLabels', () => {
  const c = (todo: number, in_progress: number, done: number, in_review = 0) => ({
    todo,
    in_progress,
    in_review,
    done,
    total: todo + in_progress + in_review + done,
  });

  it('always sums to 100 (largest remainder), where independent rounding gave 99', () => {
    expect(percentLabels(c(1, 1, 1))).toEqual([34, 33, 0, 33]);
    for (const counts of [c(1, 1, 1), c(1, 2, 4), c(3, 3, 1), c(7, 11, 13), c(1, 0, 6), c(5, 0, 0)]) {
      expect(percentLabels(counts).reduce((a, b) => a + b, 0), JSON.stringify(counts)).toBe(100);
    }
  });

  it('keeps exact shares exact, and is all zero for an empty board', () => {
    expect(percentLabels(c(3, 2, 5))).toEqual([30, 20, 0, 50]);
    expect(percentLabels(c(0, 0, 0))).toEqual([0, 0, 0, 0]);
  });

  it('splits four parts by largest remainder and still sums to 100', () => {
    expect(percentLabels(c(1, 1, 1, 1))).toEqual([25, 25, 25, 25]);
    for (const counts of [c(1, 1, 1, 2), c(1, 2, 4, 1), c(3, 3, 1, 7), c(7, 11, 13, 5), c(0, 0, 1, 2)]) {
      expect(percentLabels(counts).reduce((a, b) => a + b, 0), JSON.stringify(counts)).toBe(100);
    }
    expect(percentLabels({ todo: 1, in_progress: 1, in_review: 1, done: 0, total: 3 })).toEqual([34, 33, 33, 0]);
  });
});

describe('timeInColumn', () => {
  const task = boardTask({ status: 'in_progress', column: 'in_progress', status_since: NOW - 1000 });

  it('grows with the clock while the session runs', () => {
    expect(timeInColumn(boardSession({ tasks: [task] }), task, NOW, true)).toBe(1000);
    expect(timeInColumn(boardSession({ tasks: [task] }), task, NOW + 60, true)).toBe(1060);
  });

  it('stops at the session end, or at its last activity when it has no end time', () => {
    const ended = boardSession({ status: 'ended', ended_at: NOW - 400, last_activity_at: NOW - 500, tasks: [task] });
    expect(timeInColumn(ended, task, NOW + 9999, false)).toBe(600);
    const silent = boardSession({ status: 'ended', ended_at: null, last_activity_at: NOW - 500, tasks: [task] });
    expect(timeInColumn(silent, task, NOW + 9999, false)).toBe(500);
  });

  it('feeds the same figure into the per-step list', () => {
    const ended = boardSession({ status: 'ended', ended_at: NOW - 400, tasks: [task] });
    const inColumn = timeInColumn(ended, task, NOW + 5000, false);
    expect(stepDurations(task, NOW + 5000, false, inColumn).find((s) => s.current)?.seconds).toBe(600);
  });
});

describe('in review', () => {
  const review = boardTask({
    key: 'rv',
    column: 'in_review',
    status: 'in_progress',
    status_since: NOW - 5000,
    review: { state: 'findings', findings: 2, since: NOW - 300 },
    durations: { pending: 60, in_progress: 900, in_review: 120 },
  });

  it('measures time in column from review.since, not from the provider status change', () => {
    expect(timeInColumn(boardSession({ tasks: [review] }), review, NOW, true)).toBe(300);
    const noReview = { ...review, review: null };
    expect(timeInColumn(boardSession({ tasks: [noReview] }), noReview, NOW, true)).toBe(5000);
  });

  it('lists In Review between In progress and Done, when it has time', () => {
    const steps = stepDurations({ ...review, durations: { ...review.durations, completed: 0 } }, NOW, true);
    expect(steps.map((s) => [s.label, s.seconds])).toEqual([
      ['To do', 60],
      ['In progress', 900],
      ['In Review', 300],
    ]);
    expect(steps.find((s) => s.current)?.label).toBe('In Review');
  });

  it('keeps provider-status rows frozen while in review: only In Review is live, and the rows sum to the lifetime', () => {
    const task = boardTask({
      key: 'sum',
      column: 'in_review',
      status: 'in_progress',
      created_at: NOW - 1200,
      status_since: NOW - 1000,
      review: { state: 'pending', findings: null, since: NOW - 300 },
      durations: { pending: 200, in_progress: 700, in_review: 0, completed: 0 },
    });
    const at = (later: number) => stepDurations(task, NOW + later, true, timeInColumn(boardSession({ tasks: [task] }), task, NOW + later, true));
    const first = at(0);
    const later = at(600);
    const row = (steps: typeof first, label: string) => steps.find((s) => s.label === label)?.seconds;
    expect(row(later, 'To do')).toBe(row(first, 'To do'));
    expect(row(later, 'In progress')).toBe(row(first, 'In progress'));
    expect(row(first, 'In Review')).toBe(300);
    expect(row(later, 'In Review')).toBe(900);
    expect(first.reduce((n, s) => n + s.seconds, 0)).toBe(1200);
    expect(later.filter((s) => s.current).map((s) => s.label)).toEqual(['In Review']);
  });

  it('does not count a past review window as in-progress time when the task returns to in progress', () => {
    const task = boardTask({
      column: 'in_progress',
      status: 'in_progress',
      status_since: NOW - 1000,
      durations: { pending: 0, in_progress: 100, in_review: 400 },
    });
    const steps = stepDurations(task, NOW, true, NOW - task.status_since);
    expect(steps.find((s) => s.label === 'In progress')?.seconds).toBe(600);
    expect(steps.find((s) => s.label === 'In Review')?.seconds).toBe(400);
  });

  it('drops an empty In Review step for a task that is not in review', () => {
    const task = boardTask({ status: 'completed', column: 'done', durations: { in_progress: 10, in_review: 0, completed: 0 } });
    expect(stepDurations(task, NOW, false).map((s) => s.label)).toEqual(['In progress', 'Done']);
  });

  it('puts in-review tasks in their own column and filters to findings only', () => {
    const clean = boardTask({ key: 'clean', column: 'in_review', status: 'in_progress', review: { state: 'pending', findings: null, since: NOW - 10 } });
    const project = boardProject({ sessions: [boardSession({ tasks: [review, clean, boardTask({ key: 'plain' })] })] });
    const filters = { sessionId: 'all', period: 'all', hideOldDone: true, retentionDays: 7 } as const;
    expect(buildKanban(project, filters, NOW).in_review.map((i) => i.task.key)).toEqual(['rv', 'clean']);
    const only = buildKanban(project, { ...filters, onlyFindings: true }, NOW);
    expect(only.in_review.map((i) => i.task.key)).toEqual(['rv']);
    expect(only.todo).toHaveLength(0);
  });

  it('recomputes with_findings and in_review counts for a narrower period', () => {
    const old = boardSession({ session_id: 'old', last_activity_at: NOW - 20 * 86_400, tasks: [review] });
    const recent = boardSession({ session_id: 'recent', tasks: [boardTask({ key: 'x' })] });
    const project = boardProject({ sessions: [recent, old] });
    expect(viewProject(project, 'all', NOW)).toMatchObject({ withFindings: 1, counts: { in_review: 1 } });
    expect(viewProject(project, '7d', NOW)).toMatchObject({ withFindings: 0, counts: { in_review: 0 } });
  });
});

describe('periodCutoff', () => {
  it('is null for all time, a fixed span back for 7 and 30 days, and local midnight for today', () => {
    expect(periodCutoff('all', NOW)).toBeNull();
    expect(periodCutoff('7d', NOW)).toBe(NOW - 7 * 86_400);
    expect(periodCutoff('30d', NOW)).toBe(NOW - 30 * 86_400);
    const midnight = periodCutoff('today', NOW)!;
    expect(midnight).toBeLessThanOrEqual(NOW);
    expect(NOW - midnight).toBeLessThan(86_400 + 3600);
    expect(new Date(midnight * 1000).getHours()).toBe(0);
  });
});

describe('stepDurations', () => {
  it('lists steps in the order a task moves through them, dropping empty ones', () => {
    const task = boardTask({ status: 'completed', column: 'done', durations: { completed: 0, in_progress: 300, pending: 120 } });
    const steps = stepDurations(task, NOW, false);
    expect(steps.map((s) => [s.label, s.seconds])).toEqual([
      ['To do', 120],
      ['In progress', 300],
      ['Done', 0],
    ]);
    expect(steps.find((s) => s.current)?.label).toBe('Done');
  });

  it('reads the running step live when that is longer than the CLI figure', () => {
    const task = boardTask({ status: 'in_progress', column: 'in_progress', status_since: NOW - 900, durations: { pending: 60, in_progress: 100 } });
    expect(stepDurations(task, NOW, true).find((s) => s.current)?.seconds).toBe(900);
    expect(stepDurations(task, NOW, false).find((s) => s.current)?.seconds).toBe(100);
  });
});

describe('viewProject', () => {
  const recent = boardSession({ session_id: 'recent', last_activity_at: NOW - 60, tasks: tasksOf('r', 1, 1, 1) });
  const old = boardSession({
    session_id: 'old',
    provider: 'codex',
    last_activity_at: NOW - 20 * 86_400,
    tasks: tasksOf('o', 2, 0, 0).map((t, i) => (i === 0 ? { ...t, stale: true } : t)),
  });
  const project = boardProject({ sessions: [recent, old] });

  it('over all time uses the CLI’s own project figures', () => {
    const view = viewProject(project, 'all', NOW)!;
    expect(view.counts).toEqual(project.counts);
    expect(view.sessionsTotal).toBe(2);
    expect(view.providers).toEqual(['claude', 'codex']);
    expect(view.stale).toBe(1);
  });

  it('a narrower period recomputes from the sessions that remain', () => {
    const view = viewProject(project, '7d', NOW)!;
    expect(view.counts).toEqual({ todo: 1, in_progress: 1, in_review: 0, done: 1, total: 3 });
    expect(view.sessionsTotal).toBe(1);
    expect(view.providers).toEqual(['claude']);
    expect(view.stale).toBe(0);
  });

  it('is null when nothing in the project falls inside the period', () => {
    expect(viewProject(boardProject({ sessions: [old] }), 'today', NOW)).toBeNull();
  });
});

describe('buildKanban', () => {
  const doneOld = boardTask({ key: 'old', column: 'done', status: 'completed', completed_at: NOW - 30 * 86_400, status_since: NOW - 30 * 86_400 });
  const doneNew = boardTask({ key: 'new', column: 'done', status: 'completed', completed_at: NOW - 60, status_since: NOW - 60 });
  const doing = boardTask({ key: 'doing', column: 'in_progress', status: 'in_progress' });
  const later = boardTask({ key: 'later', created_at: NOW - 10 });
  const first = boardTask({ key: 'first', created_at: NOW - 500 });
  const a = boardSession({ session_id: 'a', tasks: [later, first, doneOld, doneNew, doing] });
  const b = boardSession({ session_id: 'b', tasks: [boardTask({ key: 'b1' })] });
  const project = boardProject({ sessions: [a, b] });
  const filters = { sessionId: 'all', period: 'all', hideOldDone: true, retentionDays: 7 } as const;

  it('puts each task in its column, oldest first, done newest first', () => {
    const view = buildKanban(project, { ...filters, hideOldDone: false }, NOW);
    expect(view.todo.map((i) => i.task.key)).toEqual(['b1', 'first', 'later']);
    expect(view.in_progress.map((i) => i.task.key)).toEqual(['doing']);
    expect(view.done.map((i) => i.task.key)).toEqual(['new', 'old']);
  });

  it('hides done tasks older than the retention and says how many', () => {
    const view = buildKanban(project, filters, NOW);
    expect(view.done.map((i) => i.task.key)).toEqual(['new']);
    expect(view.hiddenDone).toBe(1);
  });

  it('never hides a task that is not done, however old', () => {
    const ancient = boardTask({ key: 'ancient', created_at: 1, status_since: 1 });
    const view = buildKanban(boardProject({ sessions: [boardSession({ tasks: [ancient] })] }), filters, NOW);
    expect(view.todo).toHaveLength(1);
  });

  it('filters to one session', () => {
    const view = buildKanban(project, { ...filters, sessionId: 'b' }, NOW);
    expect(view.todo.map((i) => i.task.key)).toEqual(['b1']);
    expect(view.in_progress).toHaveLength(0);
  });

  it('filters by period on the session’s last activity', () => {
    const stale = boardSession({ session_id: 'c', last_activity_at: NOW - 40 * 86_400, tasks: [boardTask({ key: 'c1' })] });
    const view = buildKanban(boardProject({ sessions: [a, stale] }), { ...filters, period: '30d' }, NOW);
    expect(view.todo.map((i) => i.task.key)).not.toContain('c1');
  });
});

describe('boardProjectName', () => {
  it('prefers the app’s name, then the directory’s basename, never a bare id when a root exists', () => {
    const project = boardProject({ project_id: 'uuid-1', root: '/repo/storefront/' });
    expect(boardProjectName(project, { 'uuid-1': 'Shop' })).toBe('Shop');
    expect(boardProjectName(project, {})).toBe('storefront');
    expect(boardProjectName(boardProject({ project_id: 'uuid-1', root: '' }), {})).toBe('uuid-1');
  });
});

describe('live figures from the CLI snapshot (as_of)', () => {
  const session = boardSession();
  const headlineAndRow = (task: ReturnType<typeof boardTask>, later: number, running = true, asOf = NOW) => {
    const headline = timeInColumn(session, task, NOW + later, running, asOf);
    const steps = stepDurations(task, NOW + later, running, headline, asOf);
    return { headline, steps, current: steps.find((s) => s.current)! };
  };

  it('a task reviewed in two windows: In Review carries both, In progress is frozen, headline equals the row', () => {
    const task = boardTask({
      column: 'in_review',
      status: 'in_progress',
      status_since: NOW - 9000,
      review: { state: 'pending', findings: null, since: NOW - 50 },
      durations: { pending: 60, in_progress: 400, in_review: 350 },
    });
    const at = headlineAndRow(task, 40);
    expect(at.current).toMatchObject({ status: 'in_review', seconds: 390 });
    expect(at.headline).toBe(390);
    expect(at.steps.find((s) => s.status === 'in_progress')?.seconds).toBe(400);
    expect(headlineAndRow(task, 100).steps.find((s) => s.status === 'pending')?.seconds).toBe(60);
  });

  it('reopening after a review: In progress grows from its own figure and In Review stays frozen', () => {
    const task = boardTask({
      column: 'in_progress',
      status: 'in_progress',
      status_since: NOW - 9000,
      durations: { pending: 60, in_progress: 400, in_review: 350 },
    });
    const at = headlineAndRow(task, 25);
    expect(at.current).toMatchObject({ status: 'in_progress', seconds: 425 });
    expect(at.headline).toBe(425);
    expect(at.steps.find((s) => s.status === 'in_review')?.seconds).toBe(350);
  });

  it('a task that is not running is frozen at the CLI figure however late the clock reads', () => {
    const task = boardTask({ column: 'in_progress', status: 'in_progress', durations: { in_progress: 400 } });
    const at = headlineAndRow(task, 99_999, false);
    expect(at.current.seconds).toBe(400);
    expect(at.headline).toBe(400);
  });

  it('never runs backwards when the clock reads earlier than as_of', () => {
    const task = boardTask({ column: 'in_progress', status: 'in_progress', durations: { in_progress: 400 } });
    expect(headlineAndRow(task, -500).headline).toBe(400);
  });

  it('falls back to the status_since arithmetic without as_of', () => {
    const task = boardTask({ column: 'in_progress', status: 'in_progress', status_since: NOW - 1000, durations: { in_progress: 100 } });
    expect(timeInColumn(session, task, NOW, true)).toBe(1000);
  });
});
