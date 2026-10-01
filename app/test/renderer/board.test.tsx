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
    expect(aFigures.getByRole('img', { name: '3 to do, 2 in progress, 0 in review, 5 done' })).toBeInTheDocument();
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

  it('shows four counts, a four-segment bar and an N-with-findings badge', async () => {
    const findings = { state: 'findings', findings: 2, since: NOW - 60 } as const;
    const project = boardProject({
      sessions: [
        boardSession({
          tasks: [
            boardTask({ key: 'a' }),
            boardTask({ key: 'b', column: 'in_review', status: 'in_progress', review: findings }),
            boardTask({ key: 'c', column: 'in_review', status: 'in_progress', review: findings }),
            boardTask({ key: 'd', column: 'in_review', status: 'in_progress', review: { state: 'pending', findings: null, since: NOW - 5 } }),
          ],
        }),
      ],
    });
    renderBoard(boardFeed({ projects: [project] }));
    const c = await card('storefront');
    expect(within(c).getByText('In Review').closest('div')?.textContent).toContain('3');
    expect(within(c).getByText('In Review').closest('div')?.textContent).toContain('(75%)');
    const bar = within(c).getByRole('img', { name: '1 to do, 0 in progress, 3 in review, 0 done' });
    expect([...bar.children].map((seg) => (seg as HTMLElement).style.flexGrow)).toEqual(['1', '0', '3', '0', '0']);
    expect(within(c).getByText('2 with findings')).toBeInTheDocument();
  });

  it('shows no findings badge when nothing has findings, and tolerates a CLI without the fields', async () => {
    const project = boardProject({ sessions: [boardSession()] });
    const legacy = JSON.parse(JSON.stringify(project)) as Record<string, unknown>;
    delete legacy['with_findings'];
    renderBoard(boardFeed({ projects: [legacy as unknown as BoardProject] }));
    const c = await card('storefront');
    expect(within(c).queryByText(/with findings/)).not.toBeInTheDocument();
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
    await screen.findByRole('button', { name: /^Back to Board$/ });
    return { user, ...harness };
  }

  it('lays tasks out in To do, In progress and Done', async () => {
    await openKanban();
    const todo = screen.getByRole('region', { name: /^To do/ });
    const doing = screen.getByRole('region', { name: /^In progress/ });
    const done = screen.getByRole('region', { name: /^Done/ });
    expect(within(todo).getAllByRole('article')).toHaveLength(3);
    expect(within(doing).getAllByRole('article')).toHaveLength(2);
    expect(within(done).getAllByRole('article')).toHaveLength(5);
    expect(within(todo).getByText('a1- task 1')).toBeInTheDocument();
    expect(within(doing).getByText('a1- task 2')).toBeInTheDocument();
    expect(within(done).getByText('a1- task 3')).toBeInTheDocument();
  });

  it('lays tasks out in four columns, In Review between In progress and Done', async () => {
    await openKanban(boardProject({ sessions: [boardSession({ tasks: tasksOf('k-', 1, 1, 1, 2) })] }));
    const columns = [/^To do/, /^In progress/, /^In Review/, /^Done/].map((name) => screen.getByRole('region', { name }));
    columns.slice(1).forEach((column, i) => {
      expect(columns[i]!.compareDocumentPosition(column) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    });
    expect(within(screen.getByRole('region', { name: /^In Review/ })).getAllByRole('article')).toHaveLength(2);
  });

  it('badges review state in words, counts findings, and times the card from review.since', async () => {
    await openKanban(
      boardProject({
        sessions: [
          boardSession({
            tasks: [
              boardTask({ key: 'f', content: 'Has findings', column: 'in_review', status: 'in_progress', status_since: NOW - 9000, review: { state: 'findings', findings: 3, since: NOW - 120 } }),
              boardTask({ key: 'f1', content: 'One finding', column: 'in_review', status: 'in_progress', review: { state: 'findings', findings: 1, since: NOW - 60 } }),
              boardTask({ key: 'p', content: 'Waiting', column: 'in_review', status: 'in_progress', review: { state: 'pending', findings: null, since: NOW - 60 } }),
              boardTask({ key: 'u', content: 'Unread', column: 'in_review', status: 'in_progress', review: { state: 'unread', findings: null, since: NOW - 60 } }),
            ],
          }),
        ],
      }),
    );
    const article = (text: string) => screen.getByText(text).closest('article')!;
    expect(within(article('Has findings')).getByText('3 findings')).toBeInTheDocument();
    expect(within(article('Has findings')).getByText(/Time in this column/).parentElement).toHaveTextContent('2m');
    expect(within(article('One finding')).getByText('1 finding')).toBeInTheDocument();
    expect(within(article('Waiting')).getByText('Awaiting review')).toBeInTheDocument();
    expect(within(article('Unread')).getByText('Result not read')).toBeInTheDocument();
  });

  it('lists In Review in the per-step durations', async () => {
    const { user } = await openKanban(
      boardProject({
        sessions: [
          boardSession({
            tasks: [
              boardTask({ key: 'r', content: 'Under review', column: 'in_review', status: 'in_progress', durations: { pending: 60, in_progress: 600, in_review: 30 }, review: { state: 'pending', findings: null, since: NOW - 120 } }),
            ],
          }),
        ],
      }),
    );
    await user.click(screen.getByRole('button', { name: /time per step, under review/i }));
    const steps = screen.getByText('In Review (now)').closest('ul')!;
    expect(within(steps).getByText('In progress')).toBeInTheDocument();
    expect(within(steps).getByText('2m').closest('li')).toHaveTextContent('In Review (now)');
  });

  it('filters to tasks with findings', async () => {
    const { user } = await openKanban(
      boardProject({
        sessions: [
          boardSession({
            tasks: [
              boardTask({ key: 'f', content: 'Has findings', column: 'in_review', status: 'in_progress', review: { state: 'findings', findings: 2, since: NOW - 60 } }),
              boardTask({ key: 'p', content: 'Waiting', column: 'in_review', status: 'in_progress', review: { state: 'pending', findings: null, since: NOW - 60 } }),
              boardTask({ key: 't', content: 'Plain todo' }),
            ],
          }),
        ],
      }),
    );
    expect(screen.getByText('Waiting')).toBeInTheDocument();
    await user.click(screen.getByRole('checkbox', { name: /with findings/i }));
    expect(screen.getByText('Has findings')).toBeInTheDocument();
    expect(screen.queryByText('Waiting')).not.toBeInTheDocument();
    expect(screen.queryByText('Plain todo')).not.toBeInTheDocument();
    await user.click(screen.getByRole('checkbox', { name: /with findings/i }));
    expect(screen.getByText('Plain todo')).toBeInTheDocument();
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
    const { user } = await openKanban(boardProject({ sessions: [boardSession({ last_activity_at: NOW, tasks: [task] })] }));
    const item = screen.getByText('Ship it').closest('article')!;
    expect(item).toHaveTextContent('2m');
    expect(item).not.toHaveTextContent('2m 5s');
    expect(item).toHaveAccessibleName('Ship it');
    // A disclosure, not a hover tooltip: closed until asked, opened by a real button.
    const toggle = within(item).getByRole('button', { name: /time per step/i });
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    const panel = document.getElementById(toggle.getAttribute('aria-controls')!)!;
    expect(panel).not.toBeVisible();
    await user.click(toggle);
    expect(toggle).toHaveAttribute('aria-expanded', 'true');
    expect(panel).toBeVisible();
    expect(panel).toHaveTextContent('To do');
    expect(panel).toHaveTextContent('2m');
    expect(panel).toHaveTextContent('In progress');
    expect(panel).toHaveTextContent('1h 5m');
    // Escape closes it and hands focus back to the button.
    await user.keyboard('{Escape}');
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    expect(panel).not.toBeVisible();
    expect(toggle).toHaveFocus();
  });

  it('has one tab stop per card, no tabindex on a plain list item, and a name on every card', async () => {
    await openKanban();
    const cards = screen.getAllByRole('article');
    expect(cards).toHaveLength(10);
    for (const card of cards) {
      expect(card.closest('li')).not.toHaveAttribute('tabindex');
      expect(card).not.toHaveAttribute('tabindex');
      expect(card).toHaveAccessibleName(/task \d/);
      expect(within(card).getAllByRole('button')).toHaveLength(1);
    }
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
    const item = (await screen.findByText('Running task')).closest('article')!;
    expect(item).toHaveTextContent('1m');
    ms += 5 * 60_000;
    act(() => {
      vi.advanceTimersByTime(1_000);
    });
    expect(item).toHaveTextContent('6m');
  });

  it('names a session by its title in the strip and the selector, and by its short id without one', async () => {
    const long = 'Refactor the checkout flow and its payment retries end to end';
    const titled = boardSession({ session_id: 'titled-session', title: long, branch: 'feat/checkout' });
    const plain = boardSession({ session_id: 'plain1234-session', title: null, branch: 'fix/cart', provider: 'codex' });
    await openKanban(boardProject({ sessions: [titled, plain] }));
    const rows = within(screen.getByRole('list', { name: 'Sessions' })).getAllByRole('listitem');
    const shown = within(rows[0]!).getByText(long);
    expect(shown).toHaveAttribute('title', long);
    expect(shown).toHaveClass('truncate');
    expect(rows[1]).not.toHaveTextContent('plain1234');
    const options = within(screen.getByLabelText('Session')).getAllByRole('option').map((o) => o.textContent);
    expect(options).toContain('Refactor the checkout flow and its payme… · Claude Code · feat/checkout');
    expect(options).toContain('Codex · fix/cart · plain123');
  });

  it('filters to one session', async () => {
    const { user } = await openKanban();
    await user.selectOptions(screen.getByLabelText('Session'), 'a3');
    const todo = screen.getByRole('region', { name: /^To do/ });
    expect(within(todo).getAllByRole('article')).toHaveLength(1);
    expect(within(todo).getByText('a3- task 1')).toBeInTheDocument();
    expect(screen.getAllByRole('listitem').filter((li) => li.closest('[aria-label="Sessions"]'))).toHaveLength(1);
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
    expect(within(screen.getByText('Slow one').closest('article')!).getByText('Stale')).toBeInTheDocument();
    expect(within(screen.getByText('Left behind').closest('article')!).getByText('Abandoned')).toBeInTheDocument();
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

  it('lays the sessions out as compact chips, the counts in each chip’s tooltip', async () => {
    await openKanban();
    const list = screen.getByRole('list', { name: 'Sessions' });
    expect(list).toHaveClass('flex', 'flex-wrap');
    const codex = within(list).getAllByRole('listitem')[1]!;
    expect(codex).toHaveAttribute('title', expect.stringContaining('1 to do · 1 in progress · 3 done'));
    // The counts are not drawn on screen: they are text for a screen reader only.
    expect(within(codex).getByText('1 to do · 1 in progress · 3 done')).toHaveClass('sr-only');
  });

  it('offers no resume-command button on a session', async () => {
    await openKanban();
    expect(screen.queryByRole('button', { name: /resume/i })).not.toBeInTheDocument();
  });

  it('shows the project name without its path', async () => {
    await openKanban();
    expect(screen.getByRole('heading', { level: 3, name: 'storefront' })).toBeInTheDocument();
    expect(screen.queryByText('/repo/storefront')).not.toBeInTheDocument();
  });

  it('tints the Done column as the positive end of the flow, and only that one', async () => {
    await openKanban();
    expect(screen.getByRole('region', { name: /^Done/ })).toHaveAttribute('data-tone', 'positive');
    expect(screen.getByRole('region', { name: /^To do/ })).not.toHaveAttribute('data-tone');
  });

  it('returns to the overview when the tab is left and shown again', async () => {
    const user = userEvent.setup();
    installBridge(fakeBridge({ taskBoard: vi.fn(() => Promise.resolve(boardFeed({ projects: [projectA()] }))) }));
    const { rerender } = render(<Board clock={clock} active />);
    await user.click(await card('storefront'));
    await screen.findByRole('button', { name: /^Back to Board$/ });
    rerender(<Board clock={clock} active={false} />);
    rerender(<Board clock={clock} active />);
    expect(screen.queryByRole('button', { name: /^Back to Board$/ })).not.toBeInTheDocument();
    expect(await card('storefront')).toBeInTheDocument();
  });

  it('goes back to the board', async () => {
    const { user } = await openKanban();
    await user.click(screen.getByRole('button', { name: /^Back to Board$/ }));
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

describe('Board — timers and time in column', () => {
  afterEach(() => vi.restoreAllMocks());

  function intervals(spy: { mock: { calls: unknown[][] } }): number[] {
    return spy.mock.calls.map((call) => call[1] as number).filter((ms) => ms === 1_000 || ms === 60_000);
  }

  it('does not tick while the tab is hidden, re-samples on activation, and ticks each second only in the kanban', async () => {
    const spy = vi.spyOn(globalThis, 'setInterval');
    let ms = NOW * 1000;
    installBridge(fakeBridge({ taskBoard: vi.fn(() => Promise.resolve(boardFeed({ projects: [projectA()] }))) }));
    const view = render(<Board active={false} clock={() => ms} />);
    await card('storefront');
    expect(intervals(spy)).toEqual([]);

    ms += 10 * 60_000;
    view.rerender(<Board active clock={() => ms} />);
    expect(intervals(spy)).toEqual([60_000]); // the overview: once a minute, never every second

    fireEvent.click(await card('storefront'));
    await screen.findByRole('button', { name: /^Back to Board$/ });
    expect(intervals(spy)).toEqual([60_000, 60_000, 1_000]); // kanban: filters each minute, running cards each second

    spy.mockClear();
    view.rerender(<Board active={false} clock={() => ms} />);
    expect(intervals(spy)).toEqual([]);
  });

  it('measures a task in an ended session to the session end, and freezes the step list at the same figure', async () => {
    vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval'] });
    let ms = NOW * 1000;
    const task = boardTask({
      key: 'k',
      content: 'Abandoned work',
      status: 'in_progress',
      column: 'in_progress',
      abandoned: true,
      status_since: NOW - 1000,
      durations: { pending: 10, in_progress: 100 },
    });
    const session = boardSession({ status: 'ended', ended_at: NOW - 100, last_activity_at: NOW - 120, tasks: [task] });
    installBridge(fakeBridge({ taskBoard: vi.fn(() => Promise.resolve(boardFeed({ projects: [boardProject({ sessions: [session] })] }))) }));
    render(<Board clock={() => ms} />);
    fireEvent.click(await card('storefront'));
    const item = (await screen.findByText('Abandoned work')).closest('article')!;
    expect(item).toHaveTextContent('15m'); // 900 s: NOW-100 minus NOW-1000
    fireEvent.click(within(item).getByRole('button', { name: /time per step/i }));
    expect(item).toHaveTextContent('In progress (now)15m');
    ms += 60 * 60_000;
    act(() => {
      vi.advanceTimersByTime(1_000);
    });
    expect(item).toHaveTextContent('15m');
    expect(item).not.toHaveTextContent('1h');
  });
});

describe('Board — loading, failures and races', () => {
  it('shows a loading state, not the empty-state copy, until the stream is live', async () => {
    renderBoard(boardFeed({ status: 'starting', projects: [] }));
    expect(await screen.findByText('Loading the task board…')).toBeInTheDocument();
    expect(screen.queryByText(/No project has tasks yet/)).not.toBeInTheDocument();
  });

  it('says it is reconnecting when the stream is retrying with nothing to show', async () => {
    renderBoard(boardFeed({ status: 'retrying', detail: 'the task stream stopped (exit 1). Retrying in 1 s.', projects: [] }));
    expect(await screen.findByText('Reconnecting to the task stream…')).toBeInTheDocument();
    expect(screen.queryByText(/No project has tasks yet/)).not.toBeInTheDocument();
  });

  it('a push that arrives before the first read answers is not overwritten by it', async () => {
    let resolveInitial: (feed: BoardFeed) => void = () => undefined;
    let push: (feed: BoardFeed) => void = () => undefined;
    installBridge(
      fakeBridge({
        taskBoard: vi.fn(() => new Promise<BoardFeed>((resolve) => (resolveInitial = resolve))),
        onTaskBoard: vi.fn((listener: (feed: BoardFeed) => void) => {
          push = listener;
          return () => undefined;
        }),
      }),
    );
    render(<Board clock={clock} />);
    act(() => push(boardFeed({ projects: [projectB()] })));
    await card('billing');
    resolveInitial(boardFeed({ projects: [projectA()] }));
    await act(() => Promise.resolve());
    expect(screen.getByText('billing')).toBeInTheDocument();
    expect(screen.queryByText('storefront')).not.toBeInTheDocument();
  });

  it('a failed first read becomes an error state, not an empty board', async () => {
    renderBoard(boardFeed(), { taskBoard: vi.fn(() => Promise.reject(new Error('ipc closed'))) });
    expect(await screen.findByRole('alert')).toHaveTextContent('The task board could not be loaded: ipc closed');
    expect(screen.queryByText(/No project has tasks yet/)).not.toBeInTheDocument();
    expect(screen.queryByText('Loading the task board…')).not.toBeInTheDocument();
  });

  it('survives failed name and settings reads', async () => {
    renderBoard(boardFeed({ projects: [projectA()] }), {
      projectNames: vi.fn(() => Promise.reject(new Error('no names'))),
      boardSettings: vi.fn(() => Promise.reject(new Error('no settings'))),
    });
    expect(await card('storefront')).toBeInTheDocument();
  });

  it('a failed refresh is reported and the board stays', async () => {
    const user = userEvent.setup();
    renderBoard(boardFeed({ projects: [projectA()] }), {
      refreshTaskBoard: vi.fn(() => Promise.reject(new Error('main is gone'))),
    });
    await card('storefront');
    await user.click(screen.getByRole('button', { name: /refresh/i }));
    expect(await screen.findByRole('alert')).toHaveTextContent('could not be refreshed: main is gone');
    expect(screen.getByText('storefront')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /refresh/i })).toBeEnabled();
  });

  it('a failed save is shown in the settings form', async () => {
    const user = userEvent.setup();
    renderBoard(boardFeed({ projects: [] }), { setBoardSettings: vi.fn(() => Promise.reject(new Error('ipc closed'))) });
    await user.click(await screen.findByRole('button', { name: /board settings/i }));
    const dialog = await screen.findByRole('dialog', { name: 'Board settings' });
    await user.click(within(dialog).getByRole('button', { name: 'Save' }));
    expect(await within(dialog).findByRole('alert')).toHaveTextContent('could not be saved: ipc closed');
  });
});

describe('Board — one period, honest percentages', () => {
  it('has a single Period control, shared by the overview and the kanban', async () => {
    const user = userEvent.setup();
    const old = boardSession({ session_id: 'o', last_activity_at: NOW - 20 * 86_400, tasks: [boardTask({ key: 'ancient', content: 'Ancient chore' })] });
    renderBoard(boardFeed({ projects: [boardProject({ root: '/repo/storefront', sessions: [boardSession({ tasks: [boardTask({ key: 'n', content: 'New chore' })] }), old] })] }));
    await user.click(await card('storefront'));
    await screen.findByRole('button', { name: /^Back to Board$/ });
    expect(screen.getAllByLabelText('Period')).toHaveLength(1);
    expect(screen.queryByText('Ancient chore')).not.toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText('Period'), '30d');
    expect(screen.getByText('Ancient chore')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /^Back to Board$/ }));
    expect(screen.getByLabelText('Period')).toHaveValue('30d');
  });

  it('percentages of 1/1/1 sum to 100 and the bar is proportional to the counts', async () => {
    renderBoard(boardFeed({ projects: [boardProject({ sessions: [boardSession({ tasks: tasksOf('x-', 1, 1, 1) })] })] }));
    const c = await card('storefront');
    const shares = ['To do', 'In progress', 'In Review', 'Done'].map((label) => {
      const text = within(c).getByText(label).closest('div')?.textContent ?? '';
      return Number(/\((\d+)%\)/.exec(text)![1]);
    });
    expect(shares.reduce((a, b) => a + b, 0)).toBe(100);
    const bar = within(c).getByRole('img', { name: '1 to do, 1 in progress, 0 in review, 1 done' });
    expect([...bar.children].map((seg) => (seg as HTMLElement).style.flexGrow)).toEqual(['1', '1', '0', '0', '1']);
  });
});
