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

  it('offers the findings filter from the session in view, and keeps a checked box sticky when none is left', async () => {
    const withFindings = boardSession({ session_id: 'has-one', branch: 'b-findings', tasks: [reviewTask('f', findings)] });
    const recent = boardSession({ session_id: 'recent', tasks: [boardTask({ key: 'x', content: 'Recent todo' })] });
    const { user } = await openKanban(boardProject({ sessions: [recent, withFindings] }));
    const box = () => screen.getByRole('checkbox', { name: /with findings/i });
    expect(box()).toBeEnabled();
    await user.click(box());
    expect(box()).toBeChecked();

    // Nothing in this session has findings, but the checked box is neither unchecked nor disabled.
    await user.selectOptions(screen.getByLabelText('Session'), 'recent');
    expect(box()).toBeChecked();
    expect(box()).toBeEnabled();
    expect(box()).not.toHaveAccessibleDescription();
    expect(screen.getByRole('status')).toHaveTextContent('No tasks with findings');
    expect(screen.queryByText('Recent todo')).not.toBeInTheDocument();

    // Findings coming back into view are filtered to without any further click.
    await user.selectOptions(screen.getByLabelText('Session'), 'all');
    expect(box()).toBeChecked();
    expect(screen.getByText('Task f')).toBeInTheDocument();
    expect(screen.queryByText('Recent todo')).not.toBeInTheDocument();

    // And the user, not the data, decides when it goes off.
    await user.selectOptions(screen.getByLabelText('Session'), 'recent');
    await user.click(box());
    expect(box()).not.toBeChecked();
    expect(box()).toBeDisabled();
    expect(box()).toHaveAccessibleDescription('No task in this view has findings.');
    expect(screen.getByText('Recent todo')).toBeInTheDocument();
  });

  it('keeps a checked findings box checked, enabled and focused when a watch update removes the last finding', async () => {
    const before = boardProject({ sessions: [boardSession({ tasks: [reviewTask('f', findings), boardTask({ key: 'x', content: 'Plain todo' })] })] });
    const { user, push } = await openKanban(before);
    const box = () => screen.getByRole('checkbox', { name: /with findings/i });
    await user.click(box());
    box().focus();
    expect(box()).toHaveFocus();
    expect(screen.queryByText('Plain todo')).not.toBeInTheDocument();

    const after = boardProject({ sessions: [boardSession({ tasks: [reviewTask('f', { state: 'pending', findings: null, since: NOW - 5 }), boardTask({ key: 'x', content: 'Plain todo' })] })] });
    push(boardFeed({ projects: [after] }));
    expect(box()).toBeChecked();
    expect(box()).toBeEnabled();
    expect(box()).toHaveFocus();
    expect(screen.getByRole('status')).toHaveTextContent('No tasks with findings');
    expect(screen.queryByRole('region', { name: /^To do/ })).not.toBeInTheDocument();

    await user.click(box());
    expect(box()).not.toBeChecked();
    expect(screen.getByText('Plain todo')).toBeInTheDocument();
  });

  it('disables the findings checkbox when the period leaves no findings, though the project has some', async () => {
    const old = boardSession({ session_id: 'old-one', last_activity_at: NOW - 20 * 86_400, tasks: [reviewTask('f', findings)] });
    const recent = boardSession({ session_id: 'recent', tasks: [boardTask({ key: 'x', content: 'Recent todo' })] });
    const { user } = await openKanban(boardProject({ sessions: [recent, old] }));
    expect(screen.getByRole('checkbox', { name: /with findings/i })).toBeDisabled();
    await user.selectOptions(screen.getByLabelText('Period'), '30d');
    expect(screen.getByRole('checkbox', { name: /with findings/i })).toBeEnabled();
  });

  it('disables the findings checkbox, with an explanation, when the project has no findings', async () => {
    await openKanban(boardProject({ sessions: [boardSession({ tasks: [reviewTask('p', { state: 'pending', findings: null, since: NOW - 5 })] })] }));
    const box = screen.getByRole('checkbox', { name: /with findings/i });
    expect(box).toBeDisabled();
    expect(box).toHaveAccessibleDescription('No task in this view has findings.');
    expect(box.closest('span[title]')).toHaveAttribute('title', 'No task in this view has findings');
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

  it('lays the four columns out in one row that scrolls sideways instead of stacking', async () => {
    await openKanban(boardProject({ sessions: [boardSession({ tasks: [boardTask({ key: 'a' })] })] }));
    const row = screen.getByRole('region', { name: 'Kanban columns' });
    // `relative`: the cards' absolutely positioned sr-only text must not escape the scroller and
    // widen the page (seen in a real window before the fix).
    expect(row).toHaveClass('relative', 'flex', 'overflow-x-auto');
    expect(row.className).not.toMatch(/grid-cols/);
    // Focusable, so the arrow keys scroll it when the columns do not fit.
    expect(row).toHaveAttribute('tabindex', '0');
    const columns = within(row).getAllByRole('region');
    expect(columns.map((column) => column.querySelector('h4')?.firstChild?.textContent)).toEqual([
      'To do',
      'In progress',
      'In Review',
      'Done',
    ]);
    for (const column of columns) {
      // A minimum width that never shrinks: below it, the row scrolls rather than squeezing.
      expect(column).toHaveClass('min-w-72', 'shrink-0', 'flex-col');
    }
  });

  it('scrolls the cards inside their column and keeps the heading out of the scroll', async () => {
    await openKanban(boardProject({ sessions: [boardSession({ tasks: [boardTask({ key: 'a' })] })] }));
    const todo = screen.getByRole('region', { name: /^To do/ });
    const list = within(todo).getByRole('list');
    expect(list).toHaveClass('relative', 'overflow-y-auto', 'min-h-0');
    expect(list).not.toContainElement(todo.querySelector('h4'));
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

describe('Board kanban — live figures from the CLI snapshot', () => {
  const row = (article: HTMLElement, label: RegExp) => within(article).getByText(label).parentElement!;

  it('grows the current step from as_of and shows the same figure on the headline and the hover row', async () => {
    const task = boardTask({
      key: 'live',
      content: 'Live one',
      column: 'in_progress',
      status: 'in_progress',
      status_since: NOW - 9999,
      durations: { pending: 60, in_progress: 100 },
    });
    const { user } = await openKanban({ ...boardProject({ sessions: [boardSession({ tasks: [task] })] }), as_of: NOW - 30 });
    const article = screen.getByText('Live one').closest('article')!;
    expect(within(article).getByText(/Time in this column/).parentElement).toHaveTextContent('2m 10s');
    await user.click(within(article).getByRole('button', { name: /time per step/i }));
    expect(row(article, /In progress \(now\)/)).toHaveTextContent('2m 10s');
    expect(row(article, /To do/)).toHaveTextContent('1m');
  });

  it('shows an in-review task inside an ended session as abandoned and reviewed, frozen at the CLI figure', async () => {
    const task = boardTask({
      key: 'gone',
      content: 'Left in review',
      column: 'in_review',
      status: 'in_progress',
      abandoned: true,
      durations: { pending: 10, in_progress: 50, in_review: 300 },
      review: { state: 'pending', findings: null, since: NOW - 300 },
    });
    const session = boardSession({ status: 'ended', ended_at: NOW - 100, tasks: [task] });
    await openKanban({ ...boardProject({ sessions: [session] }), as_of: NOW - 200 });
    const article = screen.getByText('Left in review').closest('article')!;
    expect(within(article).getByText('Awaiting review')).toBeInTheDocument();
    expect(within(article).getByText(/abandoned/i)).toBeInTheDocument();
    expect(within(article).getByText(/Time in this column/).parentElement).toHaveTextContent('5m');
  });
});

describe('Board kanban — review badges', () => {
  const inReview = (key: string, review: unknown) =>
    boardTask({ key, content: `Task ${key}`, column: 'in_review', status: 'in_progress', review: review as never });
  const badgeOf = (key: string) => screen.getByText(`Task ${key}`).closest('article')!;

  it('says only "In review" for an unknown review state, claiming nothing about the result', async () => {
    await openKanban(
      boardProject({ sessions: [boardSession({ tasks: [inReview('u', { state: 'unknown', findings: null, since: NOW - 60 })] })] }),
    );
    for (const key of ['u']) {
      const article = badgeOf(key);
      expect(within(article).getByText('In review')).toBeInTheDocument();
      expect(within(article).queryByText(/result not read|awaiting review|finding/i)).not.toBeInTheDocument();
      expect(within(article).getByText('In review')).not.toHaveAttribute('title');
    }
  });

  it.each([null, 0, undefined])('shows "Findings" without a number when the count is %s', async (count) => {
    await openKanban(boardProject({ sessions: [boardSession({ tasks: [inReview('f', { state: 'findings', findings: count, since: NOW - 60 })] })] }));
    const article = badgeOf('f');
    expect(within(article).getByText('Findings')).toBeInTheDocument();
    expect(article).not.toHaveTextContent(/\b0 findings|null|undefined/);
  });

  it('puts the explanation of each review badge in its text, not only in the title', async () => {
    await openKanban(
      boardProject({
        sessions: [
          boardSession({
            tasks: [
              inReview('f', { state: 'findings', findings: 2, since: NOW - 60 }),
              inReview('p', { state: 'pending', findings: null, since: NOW - 60 }),
              inReview('r', { state: 'unread', findings: null, since: NOW - 60 }),
            ],
          }),
        ],
      }),
    );
    expect(badgeOf('f')).toHaveTextContent('still to be fixed');
    expect(badgeOf('p')).toHaveTextContent('Waiting for the review result');
    expect(badgeOf('r')).toHaveTextContent('result has not been read yet');
    expect(within(badgeOf('r')).getByText('Result not read')).toBeInTheDocument();
    expect(within(badgeOf('f')).getByText(/still to be fixed/)).toHaveClass('sr-only');
  });
});

describe('Board kanban — tasks the parser could not place', () => {
  it('says how many tasks are not shown when the session counts more than it has cards', async () => {
    const session = boardSession({ tasks: [boardTask({ key: 'a', content: 'Drawn' })] });
    const counted = { ...session, counts: { ...session.counts, todo: 3, total: 3 } };
    await openKanban(boardProject({ sessions: [counted] }));
    expect(screen.getByText('2 tasks not shown')).toBeInTheDocument();
  });

  it('is silent when every counted task has a card', async () => {
    await openKanban(boardProject({ sessions: [boardSession({ tasks: [boardTask()] })] }));
    expect(screen.queryByText(/not shown/)).not.toBeInTheDocument();
  });

  it('counts only the sessions in view', async () => {
    const one = boardSession({ session_id: 'one', tasks: [boardTask({ key: 'a' })] });
    const two = boardSession({ session_id: 'two', tasks: [boardTask({ key: 'b' })] });
    const lossy = { ...two, counts: { ...two.counts, todo: 2, total: 2 } };
    const { user } = await openKanban(boardProject({ sessions: [one, lossy] }));
    expect(screen.getByText('1 task not shown')).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText('Session'), 'one');
    expect(screen.queryByText(/not shown/)).not.toBeInTheDocument();
  });
});

describe('Board kanban — durations on the minute clock', () => {
  it('drops the seconds from To do, In Review and Done cards and their step rows, from one minute up', async () => {
    const tasks = [
      boardTask({ key: 't', content: 'Todo card', status_since: NOW - 752, durations: { pending: 752 } }),
      boardTask({
        key: 'r',
        content: 'Review card',
        column: 'in_review',
        status: 'in_progress',
        durations: { pending: 65, in_progress: 100, in_review: 7530 },
        review: { state: 'pending', findings: null, since: NOW - 7530 },
      }),
      boardTask({ key: 'd', content: 'Done card', column: 'done', status: 'completed', completed_at: NOW - 100, status_since: NOW - 100, durations: { pending: 61, in_progress: 90, completed: 100 } }),
      boardTask({ key: 's', content: 'Short todo', status_since: NOW - 45, durations: { pending: 45 } }),
    ];
    const { user } = await openKanban({ ...boardProject({ sessions: [boardSession({ tasks })] }), as_of: NOW });
    const article = (text: string) => screen.getByText(text).closest('article')!;
    const inColumn = (text: string) => within(article(text)).getByText(/Time in this column/).parentElement!;
    expect(inColumn('Todo card')).toHaveTextContent('12m');
    expect(inColumn('Todo card')).not.toHaveTextContent('12m 32s');
    expect(inColumn('Review card')).toHaveTextContent('2h 5m');
    expect(inColumn('Review card')).not.toHaveTextContent('30s');
    expect(inColumn('Done card')).toHaveTextContent('1m');
    expect(inColumn('Short todo')).toHaveTextContent('45s');

    await user.click(within(article('Review card')).getByRole('button', { name: /time per step/i }));
    const steps = within(article('Review card')).getByText('In Review (now)').closest('ul')!;
    expect(steps).toHaveTextContent('1m');
    expect(steps).not.toHaveTextContent(/\d+s/);
    expect(steps).toHaveTextContent('2h 5m');
  });

  it('holds the clock at the snapshot time when the snapshot is newer than the sampled clock', async () => {
    const retention = 7 * 86_400;
    const done = boardTask({ key: 'd', content: 'Edge done', column: 'done', status: 'completed', completed_at: NOW + 1000 - retention - 10, status_since: NOW + 1000 - retention - 10 });
    await openKanban({ ...boardProject({ sessions: [boardSession({ tasks: [done] })] }), as_of: NOW + 1000 });
    expect(screen.queryByText('Edge done')).not.toBeInTheDocument();
    expect(screen.getByText(/1 older done task is hidden/)).toBeInTheDocument();
  });

  it('shows the same task while the snapshot is not ahead of the clock', async () => {
    const retention = 7 * 86_400;
    const done = boardTask({ key: 'd', content: 'Edge done', column: 'done', status: 'completed', completed_at: NOW - retention + 990, status_since: NOW - retention + 990 });
    await openKanban({ ...boardProject({ sessions: [boardSession({ tasks: [done] })] }), as_of: NOW });
    expect(screen.getByText('Edge done')).toBeInTheDocument();
  });
});

describe('Board kanban — an old CLI payload', () => {
  it('renders a project with no in_review counts, no review windows and no as_of', async () => {
    const tasks = [
      boardTask({ key: 't', content: 'Old todo' }),
      boardTask({ key: 'p', content: 'Old doing', column: 'in_progress', status: 'in_progress', status_since: NOW - 30, durations: { in_progress: 30 } }),
    ];
    const project = boardProject({ sessions: [boardSession({ tasks })] });
    const old: Record<string, unknown> = { ...project };
    delete old.as_of;
    await openKanban(old as unknown as BoardProject);
    expect(screen.getByText('Old todo')).toBeInTheDocument();
    expect(screen.getByText('Old doing').closest('article')).toHaveTextContent('30s');
    expect(within(screen.getByRole('region', { name: /^In Review/ })).getByText('Nothing here.')).toBeInTheDocument();
    expect(screen.queryByText(/not shown/)).not.toBeInTheDocument();
  });
});

describe('Board kanban — agent and failed badges', () => {
  const card = (text: string) => screen.getByText(text).closest('article')!;

  it('splits an agent task into an Agent badge and its description, and flags a failure in words', async () => {
    const tasks = [
      boardTask({ key: 'a', content: 'reviewer: check the diff', kind: 'agent', column: 'in_progress', status: 'in_progress' }),
      boardTask({ key: 'b', content: 'builder: ship it', kind: 'agent', failed: true, column: 'done', status: 'completed' }),
    ];
    await openKanban(boardProject({ sessions: [boardSession({ tasks })] }));
    const a = card('check the diff');
    expect(within(a).getByText('Agent: reviewer')).toBeInTheDocument();
    expect(within(a).queryByText('Failed')).not.toBeInTheDocument();
    const b = card('ship it');
    expect(within(b).getByText('Agent: builder')).toBeInTheDocument();
    expect(within(b).getByText('Failed')).toBeInTheDocument();
  });

  it('keeps the text whole when it does not split cleanly, and draws nothing for a plain task', async () => {
    const tasks = [
      boardTask({ key: 'a', content: 'no separator here', kind: 'agent' }),
      boardTask({ key: 'b', content: 'Fix: the thing', kind: 'todo' }),
    ];
    await openKanban(boardProject({ sessions: [boardSession({ tasks })] }));
    expect(within(card('no separator here')).getByText('Agent')).toBeInTheDocument();
    const plain = card('Fix: the thing');
    expect(within(plain).queryByText(/Agent|Failed/)).not.toBeInTheDocument();
  });
});
