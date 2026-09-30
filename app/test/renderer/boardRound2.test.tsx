// @vitest-environment jsdom
/**
 * Round-2 review of the task board screen: what re-renders on the one-second tick, which
 * sessions the period leaves in the kanban's filters, recovery from a failed first read,
 * a project that loses its tasks, and the settings form's keyboard and in-flight behaviour.
 */
import './setup.js';
import '@testing-library/jest-dom/vitest';

import { act, cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type * as BoardModel from '../../src/renderer/boardModel.js';
import * as boardModel from '../../src/renderer/boardModel.js';
import { Board } from '../../src/renderer/screens/Board.js';
import type { BoardFeed, BoardProject } from '../../src/shared/api.js';
import { NOW, boardProject, boardSession, boardTask } from '../fixtures/board.js';
import { boardFeed, fakeBridge, installBridge } from './support.js';

vi.mock('../../src/renderer/boardModel.js', async (importOriginal) => {
  const original = await importOriginal<typeof BoardModel>();
  return { ...original, stepDurations: vi.fn(original.stepDurations) };
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.mocked(boardModel.stepDurations).mockClear();
});

const clock = () => NOW * 1000;

function renderBoard(feed: BoardFeed, overrides: Parameters<typeof fakeBridge>[0] = {}, boardClock: () => number = clock) {
  let push: (feed: BoardFeed) => void = () => undefined;
  const bridge = fakeBridge({
    taskBoard: vi.fn(() => Promise.resolve(feed)),
    refreshTaskBoard: vi.fn(() => Promise.resolve(feed)),
    onTaskBoard: vi.fn((listener: (feed: BoardFeed) => void) => {
      push = listener;
      return () => undefined;
    }),
    ...overrides,
  });
  installBridge(bridge);
  render(<Board clock={boardClock} />);
  return { bridge, push: (next: BoardFeed) => act(() => push(next)) };
}

async function openKanban(project: BoardProject, overrides: Parameters<typeof fakeBridge>[0] = {}, boardClock: () => number = clock) {
  const user = userEvent.setup({ advanceTimers: (ms) => void ms });
  const harness = renderBoard(boardFeed({ projects: [project] }), overrides, boardClock);
  fireEvent.click((await screen.findByText('storefront')).closest('button')!);
  await screen.findByRole('button', { name: /back to the board/i });
  return { user, ...harness };
}

const overviewCard = async (name: string) => (await screen.findByText(name)).closest('button')!;

describe('Board kanban — the one-second tick', () => {
  it('re-renders running cards only; done and ended cards are not recomputed', async () => {
    vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval'] });
    let ms = NOW * 1000;
    const project = boardProject({
      sessions: [
        boardSession({
          tasks: [
            boardTask({ key: 'run', content: 'Running one', column: 'in_progress', status: 'in_progress', status_since: NOW - 30 }),
            boardTask({ key: 'fin', content: 'Finished one', column: 'done', status: 'completed', completed_at: NOW - 100 }),
          ],
        }),
        boardSession({
          session_id: 'gone',
          status: 'ended',
          ended_at: NOW - 50,
          tasks: [boardTask({ key: 'abn', content: 'Abandoned one', column: 'in_progress', status: 'in_progress', abandoned: true })],
        }),
      ],
    });
    await openKanban(project, {}, () => ms);
    const calls = (key: string) => vi.mocked(boardModel.stepDurations).mock.calls.filter(([task]) => task.key === key).length;
    const before = { run: calls('run'), fin: calls('fin'), abn: calls('abn') };
    expect(before.run).toBeGreaterThan(0);

    for (let i = 0; i < 3; i += 1) {
      ms += 1000;
      act(() => {
        vi.advanceTimersByTime(1000);
      });
    }

    expect(calls('run')).toBeGreaterThanOrEqual(before.run + 3);
    expect(calls('fin')).toBe(before.fin);
    expect(calls('abn')).toBe(before.abn);
    const running = screen.getByText('Running one').closest('article')!;
    expect(running).toHaveTextContent('33s');
  });

  it('runs no per-second timer when no running task is on screen', async () => {
    const spy = vi.spyOn(globalThis, 'setInterval');
    await openKanban(
      boardProject({ sessions: [boardSession({ tasks: [boardTask({ key: 'fin', column: 'done', status: 'completed', completed_at: NOW - 10 })] })] }),
    );
    expect(spy.mock.calls.map((call) => call[1]).filter((ms) => ms === 1_000)).toEqual([]);
    spy.mockRestore();
  });
});

describe('Board kanban — In Review and the findings filter', () => {
  const findings = { state: 'findings', findings: 2, since: NOW - 120 } as const;
  const reviewTask = (key: string, review: typeof findings | { state: 'pending'; findings: null; since: number }) =>
    boardTask({ key, content: `Task ${key}`, column: 'in_review', status: 'in_progress', review });
  const oneSecond = (spy: { mock: { calls: unknown[][] } }) => spy.mock.calls.filter((call) => call[1] === 1_000);

  it('runs no per-second timer for a board of in-review cards alone', async () => {
    const spy = vi.spyOn(globalThis, 'setInterval');
    await openKanban(boardProject({ sessions: [boardSession({ tasks: [reviewTask('a', findings)] })] }));
    expect(oneSecond(spy)).toEqual([]);
    spy.mockRestore();
  });

  it('runs the per-second timer for an in-progress card in a live session', async () => {
    const spy = vi.spyOn(globalThis, 'setInterval');
    await openKanban(
      boardProject({ sessions: [boardSession({ tasks: [boardTask({ key: 'r', column: 'in_progress', status: 'in_progress' })] })] }),
    );
    expect(oneSecond(spy)).toHaveLength(1);
    spy.mockRestore();
  });

  it('shows "No tasks with findings" when the filter leaves every column empty, and the columns again when it is off', async () => {
    const plain = boardTask({ key: 'p', content: 'Plain todo' });
    const done = boardTask({ key: 'd', content: 'Old done', column: 'done', status: 'completed', completed_at: NOW - 30 * 86_400, status_since: NOW - 30 * 86_400 });
    const project = boardProject({
      sessions: [boardSession({ tasks: [reviewTask('f', findings), plain, done] })],
    });
    const { user } = await openKanban(project);
    expect(screen.getByText(/1 older done task is hidden/)).toBeInTheDocument();
    await user.click(screen.getByRole('checkbox', { name: /with findings/i }));
    expect(screen.getByText('Task f')).toBeInTheDocument();
    expect(screen.queryByText('No tasks with findings')).not.toBeInTheDocument();
    // The Done note is about retention; with the filter on, no done task is a candidate at all.
    expect(screen.queryByText(/older done/)).not.toBeInTheDocument();
  });

  it('shows the empty state when the period narrows away every task with findings', async () => {
    const old = boardSession({ session_id: 'old-one', last_activity_at: NOW - 20 * 86_400, tasks: [reviewTask('f', findings)] });
    const recent = boardSession({ session_id: 'recent', tasks: [boardTask({ key: 'x', content: 'Recent todo' })] });
    const { user } = await openKanban(boardProject({ sessions: [recent, old] }));
    await user.selectOptions(screen.getByLabelText('Session'), 'recent');
    await user.click(screen.getByRole('checkbox', { name: /with findings/i }));
    expect(screen.getByText('No tasks with findings')).toBeInTheDocument();
    expect(screen.queryByText('Recent todo')).not.toBeInTheDocument();
  });

  it('disables the findings checkbox, with an explanation, when the project has no findings', async () => {
    await openKanban(boardProject({ sessions: [boardSession({ tasks: [reviewTask('p', { state: 'pending', findings: null, since: NOW - 5 })] })] }));
    const box = screen.getByRole('checkbox', { name: /with findings/i });
    expect(box).toBeDisabled();
    expect(box).toHaveAccessibleDescription('No task in this project has findings.');
    expect(box.closest('span[title]')).toHaveAttribute('title', 'No task in this project has findings');
  });

  it('keeps the checkbox enabled when the project has findings', async () => {
    await openKanban(boardProject({ sessions: [boardSession({ tasks: [reviewTask('f', findings)] })] }));
    const box = screen.getByRole('checkbox', { name: /with findings/i });
    expect(box).toBeEnabled();
    expect(box).not.toHaveAccessibleDescription();
  });
});

describe('Board kanban — period narrows the session filters too', () => {
  it('lists only in-period sessions in the dropdown and the strip, and resets a selection that fell out', async () => {
    const project = boardProject({
      sessions: [
        boardSession({ session_id: 'recent-1', branch: 'recent-branch' }),
        boardSession({ session_id: 'old-0001', branch: 'old-branch', last_activity_at: NOW - 20 * 86_400 }),
      ],
    });
    const { user } = await openKanban(project);
    const select = screen.getByLabelText('Session');
    expect(within(select).queryByRole('option', { name: /old-branch/ })).not.toBeInTheDocument();
    expect(within(screen.getByRole('list', { name: 'Sessions' })).queryByText('old-branch')).not.toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText('Period'), '30d');
    expect(within(select).getByRole('option', { name: /old-branch/ })).toBeInTheDocument();
    await user.selectOptions(select, within(select).getByRole('option', { name: /old-branch/ }));
    expect(select).toHaveValue('old-0001');

    await user.selectOptions(screen.getByLabelText('Period'), '7d');
    expect(select).toHaveValue('all');
    expect(within(select).queryByRole('option', { name: /old-branch/ })).not.toBeInTheDocument();
  });
});

describe('Board — recovery and disappearance', () => {
  it('a push after a failed first read retires the load-failure alert', async () => {
    const { push } = renderBoard(boardFeed(), { taskBoard: vi.fn(() => Promise.reject(new Error('ipc closed'))) });
    expect(await screen.findByRole('alert')).toHaveTextContent('could not be loaded');
    push(boardFeed({ projects: [boardProject()] }));
    expect(await overviewCard('storefront')).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('a project that loses all its tasks leaves the kanban, tells so with no other project, and does not pull the user back', async () => {
    const { push } = await openKanban(boardProject());
    push(boardFeed({ projects: [] }));
    expect(await screen.findByText('That project no longer has tasks.')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /back to the board/i })).not.toBeInTheDocument();

    push(boardFeed({ projects: [boardProject()] }));
    expect(await overviewCard('storefront')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /back to the board/i })).not.toBeInTheDocument();
  });
});

describe('Board — accessibility and overflow', () => {
  it('column counts are read as text with the right plural', async () => {
    await openKanban(
      boardProject({
        sessions: [boardSession({ tasks: [boardTask({ key: 'a' }), boardTask({ key: 'b', column: 'in_progress', status: 'in_progress' })] })],
      }),
    );
    expect(within(screen.getByRole('region', { name: /^To do/ })).getByText('1 task')).toHaveClass('sr-only');
    expect(within(screen.getByRole('region', { name: /^Done/ })).getByText('0 tasks')).toHaveClass('sr-only');
    expect(screen.queryByText('1 tasks')).not.toBeInTheDocument();
  });

  it('lets an unbroken task text wrap instead of overflowing the column', async () => {
    const content = 'x'.repeat(300);
    await openKanban(boardProject({ sessions: [boardSession({ tasks: [boardTask({ content })] })] }));
    expect(screen.getByText(content)).toHaveClass('break-words');
  });

  it('submits the settings with Enter and ignores a second submit while saving', async () => {
    let finish: (value: { ok: true; settings: { staleAfterMinutes: number; doneRetentionDays: number } }) => void = () => undefined;
    const setBoardSettings = vi.fn(
      () =>
        new Promise<{ ok: true; settings: { staleAfterMinutes: number; doneRetentionDays: number } }>((resolve) => {
          finish = resolve;
        }),
    );
    const user = userEvent.setup();
    renderBoard(boardFeed({ projects: [] }), { setBoardSettings });
    await user.click(await screen.findByRole('button', { name: /board settings/i }));
    const dialog = await screen.findByRole('dialog', { name: 'Board settings' });
    const stale = within(dialog).getByLabelText('Stale after (minutes)');
    await user.click(stale);
    await user.keyboard('{Enter}');
    expect(setBoardSettings).toHaveBeenCalledTimes(1);
    expect(within(dialog).getByRole('button', { name: 'Save' })).toBeDisabled();
    await user.keyboard('{Enter}');
    expect(setBoardSettings).toHaveBeenCalledTimes(1);
    await act(() => {
      finish({ ok: true, settings: { staleAfterMinutes: 60, doneRetentionDays: 7 } });
      return Promise.resolve();
    });
    expect(screen.queryByRole('dialog', { name: 'Board settings' })).not.toBeInTheDocument();
  });
});
