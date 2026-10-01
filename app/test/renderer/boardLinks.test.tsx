// @vitest-environment jsdom
/**
 * The PR/MR Created column, the PR/MR and issue badges, and the rule that a click sends the
 * main process ids only, never a URL.
 */
import './setup.js';
import '@testing-library/jest-dom/vitest';

import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { Board } from '../../src/renderer/screens/Board.js';
import type { BoardFeed, BoardProject } from '../../src/shared/api.js';
import { NOW, boardProject, boardSession, boardTask } from '../fixtures/board.js';
import { boardFeed, fakeBridge, installBridge } from './support.js';

afterEach(cleanup);

const clock = () => NOW * 1000;

function renderBoard(feed: BoardFeed, overrides: Parameters<typeof fakeBridge>[0] = {}) {
  const bridge = fakeBridge({
    taskBoard: vi.fn(() => Promise.resolve(feed)),
    refreshTaskBoard: vi.fn(() => Promise.resolve(feed)),
    ...overrides,
  });
  installBridge(bridge);
  render(<Board clock={clock} />);
  return bridge;
}

async function openKanban(project: BoardProject, overrides: Parameters<typeof fakeBridge>[0] = {}) {
  const bridge = renderBoard(boardFeed({ projects: [project] }), overrides);
  fireEvent.click((await screen.findByText('storefront')).closest('button')!);
  await screen.findByRole('button', { name: /^Back to Board$/ });
  return bridge;
}

const PR_URL = 'https://github.com/acme/shop/pull/45';
const MR_URL = 'https://gitlab.example.com/acme/shop/-/merge_requests/12';

function linkedProject(): BoardProject {
  return boardProject({
    sessions: [
      boardSession({
        session_id: 's1',
        prs: [{ kind: 'mr', number: 12, url: MR_URL, state: 'open', head: 'feat/x' }],
        tasks: [
          boardTask({
            key: 'pr-task',
            content: 'Ship the checkout',
            column: 'pr_created',
            status: 'completed',
            pr: { kind: 'pr', number: 45, url: PR_URL, state: 'open' },
            refs: [
              { system: 'jira', key: 'PROJ-12', url: 'https://jira.example.com/browse/PROJ-12' },
              { system: 'github', key: 'acme/shop#7', url: 'https://github.com/acme/shop/issues/7' },
            ],
          }),
          boardTask({
            key: 'mr-task',
            content: 'Fix the cart',
            column: 'pr_created',
            status: 'completed',
            pr: { kind: 'mr', number: 3, url: MR_URL, state: 'open' },
          }),
        ],
      }),
    ],
  });
}

describe('Board — PR/MR Created column', () => {
  it('renders as the fifth column, between In Review and Done', async () => {
    await openKanban(linkedProject());
    const row = screen.getByRole('group', { name: 'Kanban columns' });
    const names = within(row).getAllByRole('region').map((region) => region.getAttribute('aria-label') ?? region.textContent);
    expect(names).toHaveLength(5);
    const titles = within(row).getAllByRole('heading').map((heading) => heading.textContent);
    expect(titles.findIndex((t) => /PR\/MR Created/.test(t ?? ''))).toBe(titles.findIndex((t) => /In Review/.test(t ?? '')) + 1);
    expect(titles.findIndex((t) => /^Done/.test(t ?? ''))).toBe(titles.findIndex((t) => /PR\/MR Created/.test(t ?? '')) + 1);
  });

  it('still renders, empty, when no task has a PR (tasks go straight to Done)', async () => {
    const project = boardProject({
      sessions: [boardSession({ tasks: [boardTask({ key: 'd', column: 'done', status: 'completed', completed_at: NOW - 30 })] })],
    });
    await openKanban(project);
    const column = screen.getByRole('region', { name: /PR\/MR Created/ });
    expect(column).toBeInTheDocument();
    expect(within(column).queryAllByRole('listitem')).toHaveLength(0);
    expect(within(column).queryByRole('button', { name: /Open .* request/ })).toBeNull();
  });

  it('puts the PR tasks in it, not in Done', async () => {
    await openKanban(linkedProject());
    const column = screen.getByRole('region', { name: /PR\/MR Created/ });
    expect(within(column).getByText('Ship the checkout')).toBeInTheDocument();
    expect(within(column).getByText('Fix the cart')).toBeInTheDocument();
    expect(within(screen.getByRole('region', { name: /^Done/ })).queryByText('Ship the checkout')).toBeNull();
  });

  it('shows #N for a pull request and !N for a merge request, with accessible names', async () => {
    await openKanban(linkedProject());
    const pr = screen.getByRole('button', { name: 'Open pull request #45 in browser' });
    expect(pr).toHaveTextContent('#45');
    const mr = screen.getByRole('button', { name: 'Open merge request !3 in browser' });
    expect(mr).toHaveTextContent('!3');
  });

  it('shows Jira and GitHub issue badges', async () => {
    await openKanban(linkedProject());
    expect(screen.getByRole('button', { name: 'Open issue PROJ-12 in browser' })).toHaveTextContent('PROJ-12');
    expect(screen.getByRole('button', { name: 'Open issue acme/shop#7 in browser' })).toHaveTextContent('acme/shop#7');
  });

  it('shows a session chip PR badge', async () => {
    await openKanban(linkedProject());
    const chip = within(screen.getByRole('list', { name: 'Sessions' })).getAllByRole('listitem')[0]!;
    expect(within(chip).getByRole('button', { name: 'Open merge request !12 in browser' })).toHaveTextContent('!12');
  });
});

describe('Board — link clicks send ids, never a URL', () => {
  it('a task PR badge calls the preload API with ids only', async () => {
    const bridge = await openKanban(linkedProject());
    fireEvent.click(screen.getByRole('button', { name: 'Open pull request #45 in browser' }));
    expect(bridge.openTaskLink).toHaveBeenCalledTimes(1);
    expect(bridge.openTaskLink).toHaveBeenCalledWith({
      project_id: 'proj-a',
      session_id: 's1',
      task_key: 'pr-task',
      link: { type: 'pr', index: 0 },
    });
  });

  it('issue badges send their index, and a session chip sends task_key null', async () => {
    const bridge = await openKanban(linkedProject());
    fireEvent.click(screen.getByRole('button', { name: 'Open issue acme/shop#7 in browser' }));
    expect(bridge.openTaskLink).toHaveBeenLastCalledWith({
      project_id: 'proj-a',
      session_id: 's1',
      task_key: 'pr-task',
      link: { type: 'ref', index: 1 },
    });
    const chip = within(screen.getByRole('list', { name: 'Sessions' })).getAllByRole('listitem')[0]!;
    fireEvent.click(within(chip).getByRole('button', { name: /merge request !12/ }));
    expect(bridge.openTaskLink).toHaveBeenLastCalledWith({
      project_id: 'proj-a',
      session_id: 's1',
      task_key: null,
      link: { type: 'pr', index: 0 },
    });
  });

  it('never puts a URL in any request, and renders no anchor to one', async () => {
    const bridge = await openKanban(linkedProject());
    for (const button of screen.getAllByRole('button', { name: /^Open (pull|merge) request|^Open issue/ })) fireEvent.click(button);
    expect(bridge.openTaskLink).toHaveBeenCalled();
    expect(JSON.stringify(vi.mocked(bridge.openTaskLink).mock.calls)).not.toMatch(/https?:|github\.com|gitlab|jira/);
    expect(document.querySelector('a[href]')).toBeNull();
  });
});

describe('Board overview — pr_created counts', () => {
  it('shows the PR/MR Created count and bar segment, and names it in the bar label', async () => {
    renderBoard(boardFeed({ projects: [linkedProject()] }));
    const card = (await screen.findByText('storefront')).closest('button')!;
    expect(within(card).getByText('PR/MR Created').closest('div')?.textContent).toContain('2');
    const bar = within(card).getByRole('img', { name: '0 to do, 0 in progress, 0 in review, 2 PR/MR created, 0 done' });
    expect([...bar.children].map((seg) => (seg as HTMLElement).style.flexGrow)).toEqual(['0', '0', '0', '2', '0']);
  });
});
