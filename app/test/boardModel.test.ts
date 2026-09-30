/**
 * The board's pure derivations: durations in words, the period filter, the per-project view
 * and the kanban. No DOM, no clock — `now` is always an argument.
 */
import { describe, expect, it } from 'vitest';

import {
  boardProjectName,
  buildKanban,
  formatDuration,
  percent,
  periodCutoff,
  stepDurations,
  viewProject,
} from '../src/renderer/boardModel.js';
import { NOW, boardProject, boardSession, boardTask, tasksOf } from './fixtures/board.js';

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
    expect(view.counts).toEqual({ todo: 1, in_progress: 1, done: 1, total: 3 });
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
