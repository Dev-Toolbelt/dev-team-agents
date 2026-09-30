// @vitest-environment jsdom
/**
 * The task board screen (ADR-0018, acceptance 1, 2, 3 and 6): what the overview counts, that
 * a project without tasks is not shown, what a kanban card says about time, and that stale and
 * abandoned work is marked in words as well as colour. Read-only: no test here can edit a task.
 */
import './setup.js';
import '@testing-library/jest-dom/vitest';

import { act, cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { Board } from '../../src/renderer/screens/Board.js';
import type { BoardFeed, BoardProject } from '../../src/shared/api.js';
import { NOW, boardProject, boardSession, boardTask, tasksOf } from '../fixtures/board.js';
import { boardFeed, fakeBridge, installBridge } from './support.js';

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.restoreAllMocks();
});

const clock = () => NOW * 1000;

/** Project A: three sessions of 3, 5 and 2 tasks → 3 to do, 2 in progress, 5 done. */
function projectA(): BoardProject {
  return boardProject({
    project_id: 'proj-a',
    root: '/repo/storefront',
    sessions: [
      boardSession({ session_id: 'a1', provider: 'claude', tasks: tasksOf('a1-', 1, 1, 1) }),
      boardSession({ session_id: 'a2', provider: 'codex', branch: 'fix/cart', status: 'idle', tasks: tasksOf('a2-', 1, 1, 3) }),
      boardSession({ session_id: 'a3', provider: 'claude', status: 'ended', tasks: tasksOf('a3-', 1, 0, 1) }),
    ],
  });
}

/** Project B: two sessions of 3 and 2 tasks → 1 to do, 2 in progress, 2 done. */
function projectB(): BoardProject {
  return boardProject({
    project_id: 'proj-b',
    root: '/repo/billing',
    sessions: [
      boardSession({ session_id: 'b1', provider: 'opencode', tasks: tasksOf('b1-', 1, 1, 1) }),
      boardSession({ session_id: 'b2', provider: 'opencode', tasks: tasksOf('b2-', 0, 1, 1) }),
    ],
  });
}

function renderBoard(feed: BoardFeed, overrides: Parameters<typeof fakeBridge>[0] = {}) {
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
  render(<Board clock={clock} />);
  return { bridge, push: (next: BoardFeed) => act(() => push(next)) };
}

async function card(name: string): Promise<HTMLElement> {
  const label = await screen.findByText(name);
  return label.closest('button')!;
}

describe('Board overview', () => {
  it('shows exactly the projects that have tasks, with their counts, percentages and providers', async () => {
    renderBoard(boardFeed({ projects: [projectA(), projectB()] }));

    const a = await card('storefront');
    expect(a).toHaveTextContent('3 sessions (1 active)');
    expect(a).toHaveTextContent('10 tasks');
    const aFigures = within(a);
    expect(aFigures.getByText('To do').closest('div')).toHaveTextContent('3 (30%)');
    expect(aFigures.getByText('In progress').closest('div')).toHaveTextContent('2 (20%)');
    expect(aFigures.getByText('Done').closest('div')).toHaveTextContent('5 (50%)');
    expect(aFigures.getByRole('img', { name: '3 to do, 2 in progress, 5 done' })).toBeInTheDocument();
    expect(aFigures.getByRole('img', { name: 'Claude Code' })).toBeInTheDocument();
    expect(aFigures.getByRole('img', { name: 'Codex' })).toBeInTheDocument();
    expect(aFigures.queryByRole('img', { name: 'opencode' })).not.toBeInTheDocument();

    const b = await card('billing');
    expect(b).toHaveTextContent('2 sessions (2 active)');
    expect(b).toHaveTextContent('5 tasks');
    expect(within(b).getByText('To do').closest('div')).toHaveTextContent('1 (20%)');
    expect(within(b).getByText('In progress').closest('div')).toHaveTextContent('2 (40%)');
    expect(within(b).getByText('Done').closest('div')).toHaveTextContent('2 (40%)');
    expect(within(b).getByRole('img', { name: 'opencode' })).toBeInTheDocument();

    expect(screen.getAllByRole('listitem').length).toBeGreaterThanOrEqual(2);
    expect(screen.getByRole('list', { name: 'Projects with tasks' }).children).toHaveLength(2);
  });

  it('does not show a project that has no tasks', async () => {
    const empty = boardProject({ project_id: 'proj-empty', root: '/repo/quiet', sessions: [] });
    renderBoard(boardFeed({ projects: [projectA(), empty] }));
    await card('storefront');
    expect(screen.queryByText('quiet')).not.toBeInTheDocument();
  });

  it('says so when no project has tasks', async () => {
    renderBoard(boardFeed({ projects: [] }));
    expect(await screen.findByText(/No project has tasks yet/)).toBeInTheDocument();
  });

  it('names a project by the app’s own name, and never by its id', async () => {
    renderBoard(boardFeed({ projects: [boardProject({ project_id: 'c0ffee-uuid', root: '/repo/storefront' })] }), {
      projectNames: vi.fn(() => Promise.resolve({ 'c0ffee-uuid': 'The Shop' })),
    });
    expect(await screen.findByText('The Shop')).toBeInTheDocument();
    expect(screen.queryByText(/c0ffee-uuid/)).not.toBeInTheDocument();
  });

  it('narrows to the period: an old session drops out of the counts, and a project with nothing left disappears', async () => {
    const oldOnly = boardProject({
      project_id: 'proj-old',
      root: '/repo/legacy',
      sessions: [boardSession({ session_id: 'o', last_activity_at: NOW - 40 * 86_400, tasks: tasksOf('o-', 2, 0, 0) })],
    });
    const user = userEvent.setup();
    renderBoard(boardFeed({ projects: [projectA(), oldOnly] }));
    await card('storefront');
    expect(screen.queryByText('legacy')).not.toBeInTheDocument(); // default period is 7 days
    await user.selectOptions(screen.getByLabelText('Period'), 'all');
    expect(await screen.findByText('legacy')).toBeInTheDocument();
  });

  it('badges stale and abandoned counts in words', async () => {
    const project = boardProject({
      sessions: [
        boardSession({
          tasks: [
            boardTask({ key: 's', column: 'in_progress', status: 'in_progress', stale: true }),
            boardTask({ key: 'x', abandoned: true }),
            boardTask({ key: 'y', abandoned: true }),
          ],
        }),
      ],
    });
    renderBoard(boardFeed({ projects: [project] }));
    const c = await card('storefront');
    expect(within(c).getByText('1 stale')).toBeInTheDocument();
    expect(within(c).getByText('2 abandoned')).toBeInTheDocument();
  });

  it('applies a pushed update without a reload', async () => {
    const { push } = renderBoard(boardFeed({ projects: [projectA()] }));
    await card('storefront');
    push(boardFeed({ projects: [projectA(), projectB()] }));
    expect(await card('billing')).toBeInTheDocument();
  });

  it('reports a stream that cannot run, instead of an empty board', async () => {
    renderBoard(boardFeed({ status: 'unavailable', detail: 'devteam could not watch tasks: store is ahead' }));
    expect(await screen.findByText('The task board is off')).toBeInTheDocument();
    expect(screen.getByText(/store is ahead/)).toBeInTheDocument();
  });

  it('refresh asks the main process for a one-shot list and shows its answer', async () => {
    const user = userEvent.setup();
    const { bridge } = renderBoard(boardFeed({ projects: [] }), {
      refreshTaskBoard: vi.fn(() => Promise.resolve(boardFeed({ projects: [projectB()] }))),
    });
    await screen.findByText(/No project has tasks yet/);
    await user.click(screen.getByRole('button', { name: /refresh/i }));
    expect(bridge.refreshTaskBoard).toHaveBeenCalled();
    expect(await card('billing')).toBeInTheDocument();
  });
});

describe('Project kanban', () => {
  async function openKanban(project: BoardProject = projectA(), overrides: Parameters<typeof fakeBridge>[0] = {}) {
    const user = userEvent.setup();
    const harness = renderBoard(boardFeed({ projects: [project] }), overrides);
    await user.click(await card('storefront'));
    await screen.findByRole('button', { name: /back to the board/i });
    return { user, ...harness };
  }

  it('lays tasks out in To do, In progress and Done', async () => {
    await openKanban();
    const todo = screen.getByRole('region', { name: /^To do/ });
    const doing = screen.getByRole('region', { name: /^In progress/ });
    const done = screen.getByRole('region', { name: /^Done/ });
    expect(within(todo).getAllByRole('listitem').filter((li) => li.hasAttribute('tabindex'))).toHaveLength(3);
    expect(within(doing).getAllByRole('listitem').filter((li) => li.hasAttribute('tabindex'))).toHaveLength(2);
    expect(within(done).getAllByRole('listitem').filter((li) => li.hasAttribute('tabindex'))).toHaveLength(5);
    expect(within(todo).getByText('a1- task 1')).toBeInTheDocument();
    expect(within(doing).getByText('a1- task 2')).toBeInTheDocument();
    expect(within(done).getByText('a1- task 3')).toBeInTheDocument();
  });

  it('shows the time in the current column, and the time spent per step on the card', async () => {
    const task = boardTask({
      key: 'k',
      content: 'Ship it',
      status: 'completed',
      column: 'done',
      created_at: NOW - 4000,
      status_since: NOW - 125,
      completed_at: NOW - 125,
      durations: { pending: 120, in_progress: 3900, completed: 0 },
    });
    await openKanban(boardProject({ sessions: [boardSession({ tasks: [task] })] }));
    const item = screen.getByText('Ship it').closest('li')!;
    expect(item).toHaveTextContent('2m 5s');
    // Reachable from the keyboard: focusable, and described by the per-step panel.
    expect(item).toHaveAttribute('tabindex', '0');
    const panel = document.getElementById(item.getAttribute('aria-describedby')!)!;
    expect(panel).toHaveTextContent('Time per step');
    expect(panel).toHaveTextContent('To do');
    expect(panel).toHaveTextContent('2m');
    expect(panel).toHaveTextContent('In progress');
    expect(panel).toHaveTextContent('1h 5m');
    // Revealed by hover and by focus, never by hover alone.
    expect(panel.className).toContain('group-hover:block');
    expect(panel.className).toContain('group-focus-within:block');
  });

  it('a task can be focused with the keyboard', async () => {
    const { user } = await openKanban();
    const item = screen.getByText('a1- task 1').closest('li')!;
    await user.tab(); // back button
    item.focus();
    expect(item).toHaveFocus();
  });

  it('keeps the running step live between snapshots', async () => {
    vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval'] });
    let ms = NOW * 1000;
    const task = boardTask({
      key: 'k',
      content: 'Running task',
      status: 'in_progress',
      column: 'in_progress',
      status_since: NOW - 60,
      durations: { pending: 10, in_progress: 60 },
    });
    installBridge(
      fakeBridge({ taskBoard: vi.fn(() => Promise.resolve(boardFeed({ projects: [boardProject({ sessions: [boardSession({ tasks: [task] })] })] }))) }),
    );
    render(<Board clock={() => ms} />);
    fireEvent.click(await card('storefront'));
    const item = (await screen.findByText('Running task')).closest('li')!;
    expect(item).toHaveTextContent('1m');
    ms += 5 * 60_000;
    act(() => {
      vi.advanceTimersByTime(1_000);
    });
    expect(item).toHaveTextContent('6m');
  });

  it('filters to one session', async () => {
    const { user } = await openKanban();
    await user.selectOptions(screen.getByLabelText('Session'), 'a3');
    const todo = screen.getByRole('region', { name: /^To do/ });
    expect(within(todo).getAllByRole('listitem').filter((li) => li.hasAttribute('tabindex'))).toHaveLength(1);
    expect(within(todo).getByText('a3- task 1')).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: /copy resume command/i })).toHaveLength(1);
  });

  it('hides done tasks older than the retention, and says so; unticking shows them', async () => {
    const old = boardTask({ key: 'o', content: 'Ancient chore', status: 'completed', column: 'done', completed_at: NOW - 30 * 86_400, status_since: NOW - 30 * 86_400 });
    const fresh = boardTask({ key: 'n', content: 'Fresh chore', status: 'completed', column: 'done', completed_at: NOW - 60, status_since: NOW - 60 });
    const { user } = await openKanban(boardProject({ sessions: [boardSession({ tasks: [old, fresh], last_activity_at: NOW - 60 })] }));
    expect(screen.getByText('Fresh chore')).toBeInTheDocument();
    expect(screen.queryByText('Ancient chore')).not.toBeInTheDocument();
    expect(screen.getByText('1 older done task is hidden')).toBeInTheDocument();
    await user.click(screen.getByRole('checkbox', { name: /hide done older than 7 days/i }));
    expect(screen.getByText('Ancient chore')).toBeInTheDocument();
  });

  it('marks stale and abandoned tasks in words on the card', async () => {
    await openKanban(
      boardProject({
        sessions: [
          boardSession({
            tasks: [
              boardTask({ key: 's', content: 'Slow one', column: 'in_progress', status: 'in_progress', stale: true }),
              boardTask({ key: 'a', content: 'Left behind', abandoned: true }),
            ],
          }),
        ],
      }),
    );
    expect(within(screen.getByText('Slow one').closest('li')!).getByText('Stale')).toBeInTheDocument();
    expect(within(screen.getByText('Left behind').closest('li')!).getByText('Abandoned')).toBeInTheDocument();
  });

  it('shows each session with its status in words, provider and counts', async () => {
    await openKanban();
    const sessions = within(screen.getByRole('list', { name: 'Sessions' })).getAllByRole('listitem');
    expect(sessions).toHaveLength(3);
    expect(sessions[0]).toHaveTextContent('Claude Code');
    expect(sessions[0]).toHaveTextContent('Active');
    expect(sessions[1]).toHaveTextContent('Codex');
    expect(sessions[1]).toHaveTextContent('fix/cart');
    expect(sessions[1]).toHaveTextContent('Idle');
    expect(sessions[2]).toHaveTextContent('Ended');
    expect(sessions[1]).toHaveTextContent('1 to do · 1 in progress · 3 done');
  });

  it('copies a session’s resume command through the main process, naming the session, not supplying text', async () => {
    const copy = vi.fn(() => Promise.resolve({ copied: true, command: 'cd x' } as const));
    const { user } = await openKanban(projectA(), { copyResumeCommand: copy });
    const buttons = screen.getAllByRole('button', { name: /copy resume command/i });
    await user.click(buttons[1]!);
    expect(copy).toHaveBeenCalledWith({ projectId: 'proj-a', sessionId: 'a2' });
    expect(await screen.findByText('Resume command copied')).toBeInTheDocument();
  });

  it('says why nothing was copied, and disables the button for a session with no resume command', async () => {
    const copy = vi.fn(() => Promise.resolve({ copied: false, message: 'no resume command' } as const));
    const project = boardProject({
      sessions: [
        boardSession({ session_id: 'ok' }),
        boardSession({ session_id: 'none', resume_command: null, branch: 'no-resume' }),
      ],
    });
    const { user } = await openKanban(project, { copyResumeCommand: copy });
    const buttons = screen.getAllByRole('button', { name: /copy resume command/i });
    expect(buttons[1]).toBeDisabled();
    await user.click(buttons[0]!);
    expect(await screen.findByText('no resume command')).toBeInTheDocument();
  });

  it('goes back to the board', async () => {
    const { user } = await openKanban();
    await user.click(screen.getByRole('button', { name: /back to the board/i }));
    expect(await card('storefront')).toBeInTheDocument();
  });

  it('falls back to the board when the project stops having tasks', async () => {
    const { user, push } = await openKanban();
    void user;
    push(boardFeed({ projects: [projectB()] }));
    expect(await card('billing')).toBeInTheDocument();
    expect(screen.getByText('That project no longer has tasks.')).toBeInTheDocument();
  });
});

describe('Board settings', () => {
  it('saves both thresholds, and applies the retention to the checkbox label', async () => {
    const user = userEvent.setup();
    const { bridge } = renderBoard(boardFeed({ projects: [projectA()] }));
    await card('storefront');
    await user.click(screen.getByRole('button', { name: /board settings/i }));
    const dialog = await screen.findByRole('dialog', { name: 'Board settings' });
    const stale = within(dialog).getByLabelText('Stale after (minutes)');
    const retention = within(dialog).getByLabelText('Show done for (days)');
    expect(stale).toHaveValue(60);
    expect(retention).toHaveValue(7);
    await user.clear(stale);
    await user.type(stale, '30');
    await user.clear(retention);
    await user.type(retention, '14');
    await user.click(within(dialog).getByRole('button', { name: 'Save' }));
    expect(bridge.setBoardSettings).toHaveBeenCalledWith({ staleAfterMinutes: 30, doneRetentionDays: 14 });
    await user.click(await card('storefront'));
    expect(await screen.findByRole('checkbox', { name: /hide done older than 14 days/i })).toBeInTheDocument();
  });

  it('shows the main process’s refusal and keeps the form open', async () => {
    const user = userEvent.setup();
    renderBoard(boardFeed({ projects: [] }), {
      setBoardSettings: vi.fn(() => Promise.resolve({ ok: false, message: 'the stale threshold (minutes) must be between 5 and 1440' } as const)),
    });
    await user.click(await screen.findByRole('button', { name: /board settings/i }));
    const dialog = await screen.findByRole('dialog', { name: 'Board settings' });
    await user.click(within(dialog).getByRole('button', { name: 'Save' }));
    expect(await within(dialog).findByRole('alert')).toHaveTextContent('between 5 and 1440');
  });
});
