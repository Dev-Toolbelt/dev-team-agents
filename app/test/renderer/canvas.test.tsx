// @vitest-environment jsdom
/**
 * The canvas view (spec canvas-view): the Board/Canvas switch of a project tab, what a node says,
 * the outline fallback, collapse levels, the allow-listed PR link and the older-CLI message.
 */
import './setup.js';
import '@testing-library/jest-dom/vitest';

import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from 'vitest';

import { canvasActions } from '../../src/renderer/canvasActions.js';
import { loadPositions, savePosition } from '../../src/renderer/canvasPositions.js';
import { Board } from '../../src/renderer/screens/Board.js';
import type { BoardFeed, BoardSession, TaskGraph, TaskGraphResult } from '../../src/shared/api.js';
import { NOW, boardProject, boardSession, boardTask } from '../fixtures/board.js';
import { TURN, graphNode, sampleGraph, spawn } from '../fixtures/canvasGraph.js';
import { boardFeed, fakeBridge, installBridge } from './support.js';

// React Flow measures its pane and nodes; jsdom lays nothing out, so give elements a size and
// supply the DOMMatrix React Flow reads the viewport transform from.
const sizes: [string, PropertyDescriptor | undefined][] = [];
beforeAll(() => {
  for (const key of ['offsetWidth', 'offsetHeight', 'clientWidth', 'clientHeight'] as const) {
    sizes.push([key, Object.getOwnPropertyDescriptor(HTMLElement.prototype, key)]);
    Object.defineProperty(HTMLElement.prototype, key, { configurable: true, get: () => (key.endsWith('Width') ? 1600 : 1000) });
  }
  if (typeof (globalThis as { DOMMatrixReadOnly?: unknown }).DOMMatrixReadOnly === 'undefined') {
    (globalThis as { DOMMatrixReadOnly?: unknown }).DOMMatrixReadOnly = class {
      m22: number;
      constructor(transform?: string) {
        const scale = /scale\(([\d.]+)\)/.exec(transform ?? '')?.[1];
        this.m22 = scale === undefined ? 1 : Number(scale);
      }
    };
  }
});
afterAll(() => {
  for (const [key, descriptor] of sizes) {
    if (descriptor !== undefined) Object.defineProperty(HTMLElement.prototype, key, descriptor);
    else delete (HTMLElement.prototype as unknown as Record<string, unknown>)[key];
  }
});

afterEach(() => {
  cleanup();
  localStorage.clear();
  vi.restoreAllMocks();
});

const clock = () => NOW * 1000;
const POSITIONS = 'devteam.canvas.positions.v1:proj-a';

/** A node's x inside its turn frame, read from the absolute transforms React Flow renders. */
function relativeX(canvas: HTMLElement, id: string): number {
  const x = (selector: string) => Number(/translate\(([-\d.]+)px/.exec(canvas.querySelector<HTMLElement>(selector)!.style.transform)![1]);
  return x(`.react-flow__node[data-id="${id}"]`) - x('.react-flow__node[data-id^="turn:"]');
}

function feed(extra: readonly BoardSession[] = []): BoardFeed {
  return boardFeed({
    projects: [
      boardProject({
        project_id: 'proj-a',
        root: '/repo/storefront',
        sessions: [
          boardSession({
            session_id: 's1',
            provider: 'claude',
            last_activity_at: NOW - 60,
            tasks: [boardTask({ key: 't4', content: 'backend-developer: Build the cart API', kind: 'agent', status: 'in_progress', column: 'in_progress' })],
          }),
          ...extra,
        ],
      }),
    ],
  });
}

function renderCanvas(result: TaskGraphResult = { ok: true, graph: sampleGraph() }, extraSessions: readonly BoardSession[] = []) {
  let pushGraph: (next: TaskGraphResult) => void = () => undefined;
  const bridge = fakeBridge({
    taskBoard: vi.fn(() => Promise.resolve(feed(extraSessions))),
    onTaskBoard: vi.fn(() => () => undefined),
    taskGraph: vi.fn(() => Promise.resolve(result)),
    onTaskGraph: vi.fn((_projectId: string, listener: (next: TaskGraphResult) => void) => {
      pushGraph = listener;
      return () => undefined;
    }),
    openTaskLink: vi.fn(() => Promise.resolve({ ok: true as const })),
  });
  installBridge(bridge);
  render(<Board clock={clock} />);
  return { bridge, push: (next: TaskGraphResult) => act(() => pushGraph(next)) };
}

async function openCanvas(user: ReturnType<typeof userEvent.setup>) {
  const list = await screen.findByRole('list', { name: 'Projects with tasks' });
  await user.click(within(list).getByText('storefront').closest('button')!);
  const view = await screen.findByRole('group', { name: 'View' });
  await user.click(within(view).getByRole('button', { name: 'Canvas' }));
  return screen.findByRole('toolbar', { name: 'Canvas controls' });
}

/** Picks a collapse level from the toolbar's "Show" menu. */
async function chooseLevel(user: ReturnType<typeof userEvent.setup>, label: string) {
  await user.click(screen.getByRole('button', { name: /^Show: / }));
  await user.click(await screen.findByRole('menuitemradio', { name: label }));
}

describe('Canvas view', () => {
  it('[spec:canvas-view#S1] switches a project tab between its board and its canvas, keeping both mounted', async () => {
    const user = userEvent.setup();
    const { bridge } = renderCanvas();
    const list = await screen.findByRole('list', { name: 'Projects with tasks' });
    await user.click(within(list).getByText('storefront').closest('button')!);
    const view = await screen.findByRole('group', { name: 'View' });
    expect(within(view).getByRole('button', { name: 'Board' })).toHaveAttribute('aria-pressed', 'true');
    expect(bridge.taskGraph).not.toHaveBeenCalled();

    await user.click(within(view).getByRole('button', { name: 'Canvas' }));
    expect(await screen.findByRole('toolbar', { name: 'Canvas controls' })).toBeVisible();
    expect(bridge.taskGraph).toHaveBeenCalledWith('proj-a');
    expect(bridge.onTaskGraph).toHaveBeenCalledWith('proj-a', expect.any(Function));
    expect(screen.getByRole('group', { name: 'Kanban columns', hidden: true })).not.toBeVisible();

    await user.click(within(view).getByRole('button', { name: 'Board' }));
    expect(screen.getByRole('group', { name: 'Kanban columns' })).toBeVisible();
    expect(screen.getByRole('toolbar', { name: 'Canvas controls', hidden: true })).toBeInTheDocument();
  });

  it('[spec:canvas-view#S4] [spec:canvas-view#S5] draws status in words, n/a for unknown usage, and starts ended sessions collapsed', async () => {
    const user = userEvent.setup();
    renderCanvas();
    await openCanvas(user);
    const canvas = screen.getByRole('region', { name: 'Canvas' });
    expect(await within(canvas).findByText('Build the cart API')).toBeInTheDocument();
    expect(within(canvas).getByText('Failed')).toBeInTheDocument();
    expect(within(canvas).getByText('Interrupted')).toBeInTheDocument();
    expect(within(canvas).getAllByText('Running').length).toBeGreaterThan(0);
    expect(within(canvas).getByText('Coordinating 2 agents')).toBeInTheDocument();
    expect(within(canvas).getByText('Background')).toBeInTheDocument();
    // The test specialist reported no usage: n/a, never 0.
    const tests = within(canvas).getByText('Tests').closest('[data-status]')!;
    expect(tests).toHaveTextContent('n/a');
    // The ended session is a collapsed frame that says what it hides.
    expect(within(canvas).getByRole('button', { name: 'Expand session Old session' })).toBeInTheDocument();
    expect(within(canvas).queryByText('Check the release')).not.toBeInTheDocument();
  });

  it('[spec:canvas-view#S7] hides what is below the chosen level and restores it', async () => {
    const user = userEvent.setup();
    renderCanvas();
    await openCanvas(user);
    const canvas = screen.getByRole('region', { name: 'Canvas' });
    await within(canvas).findByText('Review the API');

    await chooseLevel(user, 'Top-level agents');
    await waitFor(() => expect(within(canvas).queryByText('Review the API')).not.toBeInTheDocument());
    expect(within(canvas).getByText('Build the cart API').closest('[data-status]')).toHaveTextContent('+2 hidden');

    await chooseLevel(user, 'Everything');
    expect(await within(canvas).findByText('Review the API')).toBeInTheDocument();
  });

  it('[spec:canvas-view#S12] offers the outline as an accessible tree, driven from the keyboard', async () => {
    const user = userEvent.setup();
    renderCanvas();
    await openCanvas(user);
    const tree = screen.getByRole('tree', { name: 'Canvas outline' });
    const items = within(tree).getAllByRole('treeitem');
    expect(items[0]).toHaveAccessibleName(/Session: Cart rework/);
    expect(items[0]).toHaveAttribute('aria-level', '1');
    expect(items[0]).toHaveAttribute('tabindex', '0');

    act(() => items[0]!.focus());
    await user.keyboard('{ArrowDown}');
    expect(within(tree).getByRole('treeitem', { name: 'Orchestrator' })).toHaveFocus();
    await user.keyboard('{ArrowDown}{ArrowDown}{ArrowDown}');
    const agent = within(tree).getByRole('treeitem', { name: 'backend-developer: Build the cart API' });
    expect(agent).toHaveFocus();
    expect(agent).toHaveAttribute('aria-expanded', 'true');
    await user.keyboard('{ArrowLeft}');
    expect(agent).toHaveAttribute('aria-expanded', 'false');
    expect(within(tree).queryByRole('treeitem', { name: 'code-reviewer: Review the API' })).not.toBeInTheDocument();
    await user.keyboard('{Enter}');

    const detail = await screen.findByRole('complementary', { name: 'backend-developer' });
    expect(detail).toHaveTextContent('Cart API pushed on feat/cart');
    expect(agent).toHaveAttribute('aria-selected', 'true');
  });

  it('[spec:canvas-view#S19] shows the work without the agent name repeated, and the details in reading order', async () => {
    const graph = sampleGraph();
    const nodes = graph.nodes.map((node) =>
      node.id === 'span:s1:a' ? { ...node, description: 'backend-developer: Build the cart API', model: 'claude-opus-5-5' } : node,
    );
    const user = userEvent.setup();
    renderCanvas({ ok: true, graph: { ...graph, nodes } });
    await openCanvas(user);
    const canvas = screen.getByRole('region', { name: 'Canvas' });
    expect(await within(canvas).findByText('Build the cart API')).toBeInTheDocument();
    expect(within(canvas).queryByText('backend-developer: Build the cart API')).not.toBeInTheDocument();

    const tree = screen.getByRole('tree', { name: 'Canvas outline' });
    await user.click(within(tree).getByRole('treeitem', { name: 'backend-developer: Build the cart API' }));
    const detail = await screen.findByRole('complementary', { name: 'backend-developer' });
    expect(within(detail).getByRole('heading', { level: 4 })).toHaveTextContent(/^Build the cart API$/);
    expect(within(detail).getByRole('heading', { level: 4 })).toHaveClass('text-base', 'font-semibold');
    const labels = within(detail)
      .getAllByRole('term')
      .map((term) => term.textContent);
    expect(labels.slice(0, 5)).toEqual(['Model', 'Tokens', 'Took', 'Started', 'Finished']);
    const badge = (label: string) =>
      within(detail)
        .getAllByRole('term')
        .find((term) => term.textContent === label)!
        .nextElementSibling!.querySelector('[data-slot="badge"]');
    expect(badge('Model')).toHaveTextContent('claude-opus-5-5');
    expect(badge('Tokens')).toHaveTextContent('4k');
  });

  it('[spec:canvas-view#S6] opens a PR only through the allow-listed link path', async () => {
    const user = userEvent.setup();
    const { bridge } = renderCanvas();
    await openCanvas(user);
    const canvas = screen.getByRole('region', { name: 'Canvas' });
    await user.click(await within(canvas).findByRole('button', { name: 'Open pull request #42 in browser' }));
    expect(bridge.openTaskLink).toHaveBeenCalledWith({
      project_id: 'proj-a',
      session_id: 's1',
      task_key: 't4',
      link: { type: 'pr', index: 0, expect: '42' },
    });
  });

  it('[spec:canvas-view#S6] resolves a child-session node\'s PR against the record its task lives in', async () => {
    const graph = sampleGraph();
    const nodes = graph.nodes.map((node) => (node.task_key === 't4' ? { ...node, record_id: 's1-child' } : node));
    const user = userEvent.setup();
    const { bridge } = renderCanvas({ ok: true, graph: { ...graph, nodes } });
    await openCanvas(user);
    const canvas = screen.getByRole('region', { name: 'Canvas' });
    await user.click(await within(canvas).findByRole('button', { name: 'Open pull request #42 in browser' }));
    expect(bridge.openTaskLink).toHaveBeenCalledWith(expect.objectContaining({ session_id: 's1-child', task_key: 't4' }));
  });

  it('shows a node action registered after the canvas drew, with the node\'s session context', async () => {
    const run = vi.fn();
    const user = userEvent.setup();
    renderCanvas();
    await openCanvas(user);
    const canvas = screen.getByRole('region', { name: 'Canvas' });
    expect(within(canvas).queryByRole('button', { name: 'Stop' })).toBeNull();
    let remove: () => void = () => undefined;
    act(() => {
      remove = canvasActions.register((node) => (node.task_key === 't4' ? [{ id: 'stop', label: 'Stop', run }] : []));
    });
    try {
      // React Flow shows a node's toolbar while the node is selected.
      fireEvent.click(screen.getByRole('treeitem', { name: 'backend-developer: Build the cart API' }));
      fireEvent.click(await screen.findByRole('button', { name: 'Stop' }));
      expect(run).toHaveBeenCalledWith(expect.objectContaining({ task_key: 't4' }), { projectId: 'proj-a', sessionId: 's1', recordId: null });
    } finally {
      act(() => remove());
    }
    await waitFor(() => expect(screen.queryByRole('button', { name: 'Stop' })).toBeNull());
  });

  it('[spec:canvas-view#S7] folding a grandchild by hand leaves its grandparent reading as expanded', async () => {
    const graph = sampleGraph();
    const deeper = {
      ...graph,
      nodes: [...graph.nodes, graphNode({ id: 'span:s1:a1x', group: TURN, agent: 'security-specialist', description: 'Deep check' })],
      edges: [...graph.edges, spawn('span:s1:a1', 'span:s1:a1x')],
    };
    const user = userEvent.setup();
    renderCanvas({ ok: true, graph: deeper });
    await openCanvas(user);
    const canvas = screen.getByRole('region', { name: 'Canvas' });
    fireEvent.click(await within(canvas).findByRole('button', { name: 'Collapse code-reviewer' }));
    expect(await within(canvas).findByRole('button', { name: 'Expand code-reviewer' })).toBeInTheDocument();
    // Its direct spawns are all still drawn, so the parent's toggle still offers to collapse.
    expect(within(canvas).getByRole('button', { name: 'Collapse backend-developer' })).toBeInTheDocument();
  });

  it('takes the user from a node to its board card', async () => {
    const user = userEvent.setup();
    renderCanvas();
    await openCanvas(user);
    fireEvent.click(screen.getByRole('treeitem', { name: 'backend-developer: Build the cart API' }));
    await user.click(await screen.findByRole('button', { name: 'Show on board' }));
    const view = screen.getByRole('group', { name: 'View' });
    expect(within(view).getByRole('button', { name: 'Board' })).toHaveAttribute('aria-pressed', 'true');
    await waitFor(() => expect(document.activeElement).toHaveAttribute('data-card', 's1:t4'));
  });

  it('takes the user to a card of a session the board retention hides, lifting the filter', async () => {
    const user = userEvent.setup();
    const gone = boardSession({
      session_id: 's2', provider: 'codex', status: 'ended', ended_at: NOW - 2 * 86_400, last_activity_at: NOW - 2 * 86_400,
      tasks: [boardTask({ key: 't1', content: 'qa-specialist: Check the release', kind: 'agent', status: 'completed', column: 'done', completed_at: NOW - 2 * 86_400 })],
    });
    renderCanvas(undefined, [gone]);
    await openCanvas(user);
    fireEvent.click(screen.getByRole('treeitem', { name: 'qa-specialist: Check the release' }));
    await user.click(await screen.findByRole('button', { name: 'Show on board' }));
    await waitFor(() => expect(document.activeElement).toHaveAttribute('data-card', 's2:t1'));
    expect(screen.getByRole('checkbox', { name: /hide done older than 1 day/i })).not.toBeChecked();
  });

  it('[spec:canvas-view#S10] restores a stored position on mount and forgets it on Reset layout', async () => {
    localStorage.setItem('devteam.canvas.positions.v1:proj-a', JSON.stringify({ 'span:s1:b': { x: 700, y: 400 } }));
    const user = userEvent.setup();
    renderCanvas();
    await openCanvas(user);
    const reset = screen.getByRole('button', { name: 'Reset layout' });
    expect(reset).not.toHaveAttribute('aria-disabled');
    await user.click(reset);
    expect(reset).toHaveAttribute('aria-disabled', 'true');
    expect(localStorage.getItem('devteam.canvas.positions.v1:proj-a')).toBeNull();
  });

  it('[spec:canvas-view#S12] reveals an agent hidden in a collapsed session, raising the level and opening its details', async () => {
    const user = userEvent.setup();
    renderCanvas();
    await openCanvas(user);
    const canvas = screen.getByRole('region', { name: 'Canvas' });
    await chooseLevel(user, 'Sessions only');
    expect(within(canvas).queryByText('Check the release')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('treeitem', { name: 'qa-specialist: Check the release' }));
    expect(await within(canvas).findByText('Check the release')).toBeInTheDocument();
    expect(within(canvas).getByRole('button', { name: 'Collapse session Old session' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Show: Turns' })).toBeInTheDocument();
    expect(await screen.findByRole('complementary', { name: 'qa-specialist' })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('treeitem', { name: 'code-reviewer: Review the API' }));
    expect(await within(canvas).findByText('Review the API')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Show: Everything' })).toBeInTheDocument();
    expect(await screen.findByRole('complementary', { name: 'code-reviewer' })).toBeInTheDocument();
  });

  it('[spec:canvas-view#S8] dims everything outside the focused line and restores it on a pane click or on close', async () => {
    const user = userEvent.setup();
    renderCanvas();
    await openCanvas(user);
    const canvas = screen.getByRole('region', { name: 'Canvas' });
    const card = (text: string) => within(canvas).getByText(text).closest('[data-status]')!;
    await within(canvas).findByText('Review the API');
    const focus = screen.getByRole('button', { name: 'Focus' });

    fireEvent.click(screen.getByRole('treeitem', { name: 'backend-developer: Build the cart API' }));
    await user.click(focus);
    expect(focus).toHaveAttribute('aria-pressed', 'true');
    expect(card('Cart screen')).toHaveClass('opacity-30');
    expect(card('Review the API')).not.toHaveClass('opacity-30');
    expect(card('Build the cart API')).not.toHaveClass('opacity-30');

    fireEvent.click(canvas.querySelector('.react-flow__pane')!);
    expect(focus).toHaveAttribute('aria-pressed', 'false');
    expect(card('Cart screen')).not.toHaveClass('opacity-30');
    expect(screen.queryByRole('complementary')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('treeitem', { name: 'backend-developer: Build the cart API' }));
    await user.click(focus);
    expect(card('Cart screen')).toHaveClass('opacity-30');
    await user.click(await screen.findByRole('button', { name: 'Close details' }));
    expect(focus).toHaveAttribute('aria-pressed', 'false');
    expect(card('Cart screen')).not.toHaveClass('opacity-30');
  });

  it('[spec:canvas-view#S9] shades nodes by subtree tokens while the heatmap is on and restores the status styling after', async () => {
    const user = userEvent.setup();
    renderCanvas();
    await openCanvas(user);
    const canvas = screen.getByRole('region', { name: 'Canvas' });
    await within(canvas).findByText('Review the API');
    const card = (text: string) => within(canvas).getByText(text).closest('[data-status]')!;
    const before = card('Build the cart API').className;
    expect(before).toContain('bg-[var(--canvas-role-implementation)]');
    expect(before).toContain('border-success/70');

    await user.click(screen.getByRole('button', { name: 'Token heatmap' }));
    expect(card('Build the cart API')).toHaveClass('bg-primary/50');
    expect(card('Build the cart API').className).not.toContain('canvas-role');
    expect(card('Build the cart API')).toHaveClass('border-success/70');
    expect(card('Tests')).toHaveClass('canvas-heat-unknown');
    expect(card('Build the cart API')).toHaveTextContent('highest token use');

    await user.click(screen.getByRole('button', { name: 'Token heatmap' }));
    expect(card('Build the cart API').className).toBe(before);
    expect(card('Tests')).not.toHaveClass('canvas-heat-unknown');
  });

  it('[spec:canvas-view#S10] saves a settled move, rebuilds the layout from it and grows the frame to hold it', async () => {
    const user = userEvent.setup();
    renderCanvas();
    await openCanvas(user);
    const canvas = screen.getByRole('region', { name: 'Canvas' });
    await within(canvas).findByText('Tests');
    const moved = 'span:s1:a2';
    const turn = () => canvas.querySelector<HTMLElement>('.react-flow__node[data-id^="turn:"]')!;
    const widthBefore = parseFloat(turn().style.width);
    const xBefore = relativeX(canvas, moved);

    fireEvent.click(screen.getByRole('treeitem', { name: 'backend-test-specialist: Tests' }));
    const wrapper = canvas.querySelector<HTMLElement>(`.react-flow__node[data-id="${moved}"]`)!;
    await waitFor(() => expect(wrapper).toHaveClass('selected'));
    // An arrow-key move settles at once (`dragging: false`), the same change a pointer drag ends with.
    fireEvent.keyDown(wrapper, { key: 'ArrowRight', shiftKey: true });

    await waitFor(() => expect(localStorage.getItem(POSITIONS)).not.toBeNull());
    const stored = JSON.parse(localStorage.getItem(POSITIONS)!) as Record<string, { x: number; y: number }>;
    expect(stored[moved]!.x).toBe(xBefore + 20);
    await waitFor(() => expect(parseFloat(turn().style.width)).toBe(widthBefore + 20));
    expect(relativeX(canvas, moved)).toBe(stored[moved]!.x);
    expect(screen.getByRole('button', { name: 'Reset layout' })).toBeEnabled();
  });

  it('[spec:canvas-view#S15] keeps dragged positions and the viewport across a pushed update, fitting the view only once', async () => {
    localStorage.setItem(POSITIONS, JSON.stringify({ 'span:s1:b': { x: 700, y: 400 } }));
    const user = userEvent.setup();
    const { push } = renderCanvas();
    await openCanvas(user);
    const canvas = screen.getByRole('region', { name: 'Canvas' });
    await within(canvas).findByText('Cart screen');
    const viewport = () => canvas.querySelector<HTMLElement>('.react-flow__viewport')!.style.transform;
    await new Promise((resolve) => setTimeout(resolve, 50));
    const fitted = viewport();
    expect(relativeX(canvas, 'span:s1:b')).toBe(700);

    const graph = sampleGraph();
    push({ ok: true, graph: { ...graph, nodes: graph.nodes.map((each) => (each.id === 'span:s1:b' ? { ...each, description: 'Cart screen v2' } : each)) } });
    expect(await within(canvas).findByText('Cart screen v2')).toBeInTheDocument();
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(viewport()).toBe(fitted);
    expect(relativeX(canvas, 'span:s1:b')).toBe(700);
  });

  it('[spec:canvas-view#S3] says when a session trace could not be read', async () => {
    const user = userEvent.setup();
    const graph = sampleGraph();
    renderCanvas({
      ok: true,
      graph: { ...graph, notices: ['bad_trace:s1'] },
    });
    await openCanvas(user);
    const canvas = screen.getByRole('region', { name: 'Canvas' });
    expect(await within(canvas).findByText(/Trace unreadable for this session: showing board data/)).toBeInTheDocument();
  });

  it('[spec:canvas-view#S15] follows a pushed graph without a reload', async () => {
    const user = userEvent.setup();
    const { push } = renderCanvas();
    await openCanvas(user);
    const canvas = screen.getByRole('region', { name: 'Canvas' });
    await within(canvas).findByText('Cart screen');
    const graph = sampleGraph();
    push({ ok: true, graph: { ...graph, nodes: graph.nodes.map((each) => (each.id === 'span:s1:b' ? { ...each, description: 'Cart screen v2' } : each)) } });
    expect(await within(canvas).findByText('Cart screen v2')).toBeInTheDocument();
  });

  it('[spec:canvas-view#S18] puts the controls in a vertical icon toolbar inside the canvas', async () => {
    const user = userEvent.setup();
    renderCanvas();
    const toolbar = await openCanvas(user);
    const canvas = screen.getByRole('region', { name: 'Canvas' });
    expect(canvas).toContainElement(toolbar);
    expect(toolbar).toHaveAttribute('aria-orientation', 'vertical');
    expect(toolbar.closest('.react-flow__panel')).toHaveClass('top', 'left');
    for (const name of ['Fit view', 'Zoom in', 'Zoom out', 'Focus', 'Token heatmap', 'Hide finished older than 1 day', 'Outline', 'Full screen', 'Reset layout']) {
      const button = within(toolbar).getByRole('button', { name });
      expect(button).toHaveClass('nodrag', 'nopan');
      expect(button).not.toHaveTextContent(name);
    }
    expect(within(toolbar).getByRole('button', { name: 'Focus' })).toHaveAttribute('aria-disabled', 'true');
    expect(within(toolbar).getByRole('button', { name: 'Reset layout' })).toHaveAttribute('aria-disabled', 'true');

    await user.click(within(toolbar).getByRole('button', { name: 'Show: Everything' }));
    const levels = await screen.findAllByRole('menuitemradio');
    expect(levels.map((each) => each.textContent)).toEqual(['Sessions only', 'Turns', 'Top-level agents', 'Everything']);
    expect(screen.getByRole('menuitemradio', { name: 'Everything' })).toHaveAttribute('aria-checked', 'true');
    await user.click(screen.getByRole('menuitemradio', { name: 'Turns' }));
    expect(within(toolbar).getByRole('button', { name: 'Show: Turns' })).toBeInTheDocument();
  });

  it('[spec:canvas-view#S18] explains every toolbar button in a tooltip, on focus and on hover, disabled ones included', async () => {
    const user = userEvent.setup();
    renderCanvas();
    const toolbar = await openCanvas(user);
    const hints: [string, string][] = [
      ['Fit view', 'Fit view'],
      ['Zoom in', 'Zoom in'],
      ['Zoom out', 'Zoom out'],
      ['Show: Everything', 'Show: Everything'],
      ['Focus', 'Focus: select an agent to focus on it'],
      ['Token heatmap', 'Token heatmap: shade agents by the tokens of their subtree'],
      ['Hide finished older than 1 day', 'Hiding ended sessions and finished turns older than 1 day'],
      ['Outline', 'Outline: the canvas as a keyboard-navigable list'],
      ['Full screen', 'Full screen'],
      ['Reset layout', 'Reset layout: put every moved node back'],
    ];
    for (const [name, hint] of hints) {
      const button = within(toolbar).getByRole('button', { name });
      act(() => button.focus());
      const tooltip = await screen.findByRole('tooltip');
      expect(tooltip).toHaveTextContent(hint);
      expect(button).toHaveAttribute('aria-describedby', tooltip.id);
    }

    // The disabled Focus button stays reachable, explains itself and ignores a press.
    const focus = within(toolbar).getByRole('button', { name: 'Focus' });
    act(() => focus.focus());
    expect(await screen.findByRole('tooltip')).toHaveTextContent('Focus: select an agent to focus on it');
    await user.keyboard('{Enter}');
    expect(focus).toHaveAttribute('aria-pressed', 'false');
    act(() => focus.blur());
    await waitFor(() => expect(screen.queryByRole('tooltip')).not.toBeInTheDocument());

    await user.hover(within(toolbar).getByRole('button', { name: 'Reset layout' }));
    expect(await screen.findByRole('tooltip')).toHaveTextContent('Reset layout: put every moved node back');
  });

  it('hides a session that ended more than a day ago, and the toolbar toggle brings it back', async () => {
    const user = userEvent.setup();
    const graph = sampleGraph();
    const aged: TaskGraph = {
      ...graph,
      groups: graph.groups.map((each) => (each.id === 'session:s2' ? { ...each, started_at: NOW - 200_000, ended_at: NOW - 190_000 } : each)),
    };
    renderCanvas({ ok: true, graph: aged });
    const toolbar = await openCanvas(user);
    expect(screen.queryByText('Old session')).not.toBeInTheDocument();
    const toggle = within(toolbar).getByRole('button', { name: 'Hide finished older than 1 day' });
    expect(toggle).toHaveAttribute('aria-pressed', 'true');
    act(() => toggle.focus());
    expect(await screen.findByRole('tooltip')).toHaveTextContent('Hiding ended sessions and finished turns older than 1 day (1 hidden)');
    await user.click(toggle);
    expect(toggle).toHaveAttribute('aria-pressed', 'false');
    expect(await screen.findAllByText('Old session')).not.toHaveLength(0);
  });

  it('offers to show finished sessions when the retention hides every one', async () => {
    const user = userEvent.setup();
    const graph = sampleGraph();
    const ended: TaskGraph = {
      ...graph,
      groups: graph.groups.map((each) => (each.kind === 'session' ? { ...each, status: 'ended' as const, started_at: NOW - 200_000, ended_at: NOW - 190_000 } : each)),
      // No open PR/MR either: that would keep its session on the canvas.
      nodes: graph.nodes.map((each) => ({ ...each, pr: null })),
    };
    renderCanvas({ ok: true, graph: ended });
    const list = await screen.findByRole('list', { name: 'Projects with tasks' });
    await user.click(within(list).getByText('storefront').closest('button')!);
    await user.click(within(await screen.findByRole('group', { name: 'View' })).getByRole('button', { name: 'Canvas' }));
    expect(await screen.findByText(/finished more than 1 day ago and is hidden/)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Show finished sessions' }));
    expect(await screen.findByRole('toolbar', { name: 'Canvas controls' })).toBeInTheDocument();
  });

  it('[spec:canvas-view#S18] gives the toolbar one Tab stop and moves through it with Up, Down, Home and End', async () => {
    const user = userEvent.setup();
    renderCanvas();
    const toolbar = await openCanvas(user);
    const button = (name: string | RegExp) => within(toolbar).getByRole('button', { name });
    const tabStops = () => within(toolbar).getAllByRole('button').filter((each) => each.tabIndex === 0);
    expect(tabStops()).toEqual([button('Fit view')]);

    act(() => button('Fit view').focus());
    await user.keyboard('{ArrowDown}');
    expect(button('Zoom in')).toHaveFocus();
    expect(tabStops()).toEqual([button('Zoom in')]);
    await user.keyboard('{End}');
    expect(button('Reset layout')).toHaveFocus();
    await user.keyboard('{ArrowDown}');
    expect(button('Fit view')).toHaveFocus();
    await user.keyboard('{ArrowUp}');
    expect(button('Reset layout')).toHaveFocus();
    await user.keyboard('{ArrowUp}{ArrowUp}{ArrowUp}{ArrowUp}{ArrowUp}');
    expect(button('Focus')).toHaveFocus();
    await user.keyboard('{Home}');
    expect(button('Fit view')).toHaveFocus();

    // Tab leaves the toolbar from wherever it is, and comes back to the button it left.
    await user.keyboard('{End}{ArrowUp}');
    expect(button('Full screen')).toHaveFocus();
    await user.tab();
    expect(toolbar).not.toContainElement(document.activeElement as HTMLElement);
    await user.tab({ shift: true });
    expect(button('Full screen')).toHaveFocus();

    // Down on the Show trigger opens its menu and leaves the toolbar's focus alone.
    await user.keyboard('{Home}{ArrowDown}{ArrowDown}{ArrowDown}');
    const show = button(/^Show: /);
    const focus = button('Focus');
    expect(show).toHaveFocus();
    await user.keyboard('{ArrowDown}');
    expect(await screen.findByRole('menu')).toBeInTheDocument();
    expect(focus).not.toHaveFocus();
    expect(focus).toHaveAttribute('tabindex', '-1');
    expect(show).toHaveAttribute('tabindex', '0');
    await user.keyboard('{Escape}');
    await waitFor(() => expect(screen.queryByRole('menu')).not.toBeInTheDocument());
    await waitFor(() => expect(show).toHaveFocus());
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
  });

  it('[spec:canvas-view#S12] opens the outline by default, to the right of the canvas, and toggles it', async () => {
    const user = userEvent.setup();
    renderCanvas();
    await openCanvas(user);
    const canvas = screen.getByRole('region', { name: 'Canvas' });
    const outline = screen.getByRole('button', { name: 'Outline' });
    expect(outline).toHaveAttribute('aria-pressed', 'true');
    const tree = screen.getByRole('tree', { name: 'Canvas outline' });
    expect(canvas.compareDocumentPosition(tree) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(canvas).not.toContainElement(tree);

    await user.click(outline);
    expect(outline).toHaveAttribute('aria-pressed', 'false');
    expect(screen.queryByRole('tree', { name: 'Canvas outline' })).not.toBeInTheDocument();
    await user.click(outline);
    expect(screen.getByRole('tree', { name: 'Canvas outline' })).toBeInTheDocument();
  });

  describe('full screen', () => {
    const restore: (() => void)[] = [];
    afterEach(() => {
      while (restore.length > 0) restore.pop()!();
    });
    /** Replaces `key` on `target` for this test only. */
    function stub(target: object, key: string, descriptor: PropertyDescriptor) {
      const was = Object.getOwnPropertyDescriptor(target, key);
      Object.defineProperty(target, key, { configurable: true, ...descriptor });
      restore.push(() => {
        if (was !== undefined) Object.defineProperty(target, key, was);
        else delete (target as Record<string, unknown>)[key];
      });
    }

    it('[spec:canvas-view#S16] lays the canvas and its panels over the whole window and back, without the Fullscreen API', async () => {
      // The session refuses the `fullscreen` permission, so the API must never be the path.
      const request = vi.fn(() => Promise.resolve());
      stub(HTMLElement.prototype, 'requestFullscreen', { value: request });
      const user = userEvent.setup();
      renderCanvas();
      await openCanvas(user);
      const canvas = screen.getByRole('region', { name: 'Canvas' });
      const container = canvas.closest<HTMLElement>('[data-full-screen]')!;
      expect(container).toHaveAttribute('data-full-screen', 'off');

      await user.click(screen.getByRole('button', { name: 'Full screen' }));
      expect(request).not.toHaveBeenCalled();
      expect(container).toHaveAttribute('data-full-screen', 'overlay');
      expect(container).toHaveClass('fixed', 'inset-0', 'z-50', 'bg-background');
      expect(container).toContainElement(canvas);
      expect(container).toContainElement(screen.getByRole('tree', { name: 'Canvas outline' }));
      // Modal: the dialog names itself, and what it covers leaves the tab order.
      expect(screen.getByRole('dialog', { name: 'Canvas full screen' })).toBe(container);
      expect(container).toHaveAttribute('aria-modal', 'true');
      const covered = Array.from(document.body.querySelectorAll('[inert]'));
      expect(covered.length).toBeGreaterThan(0);
      expect(covered.some((each) => each.contains(container))).toBe(false);

      await user.click(screen.getByRole('button', { name: 'Exit full screen' }));
      expect(document.body.querySelector('[inert]')).toBeNull();
      expect(screen.queryByRole('dialog', { name: 'Canvas full screen' })).not.toBeInTheDocument();
      expect(container).toHaveAttribute('data-full-screen', 'off');
      expect(container).not.toHaveClass('fixed');
      expect(screen.getByRole('button', { name: 'Full screen' })).toBeInTheDocument();
    });

    it('[spec:canvas-view#S16] leaves full screen on Esc', async () => {
      const user = userEvent.setup();
      renderCanvas();
      await openCanvas(user);
      const container = screen.getByRole('region', { name: 'Canvas' }).closest<HTMLElement>('[data-full-screen]')!;
      await user.click(screen.getByRole('button', { name: 'Full screen' }));
      expect(container).toHaveAttribute('data-full-screen', 'overlay');
      await user.keyboard('{Escape}');
      expect(container).toHaveAttribute('data-full-screen', 'off');
      expect(screen.getByRole('button', { name: 'Full screen' })).toBeInTheDocument();
    });

    it('[spec:canvas-view#S16] closes an open Show menu on Esc before leaving full screen', async () => {
      const user = userEvent.setup();
      renderCanvas();
      await openCanvas(user);
      const container = screen.getByRole('region', { name: 'Canvas' }).closest<HTMLElement>('[data-full-screen]')!;
      await user.click(screen.getByRole('button', { name: 'Full screen' }));

      await user.click(screen.getByRole('button', { name: /^Show: / }));
      expect(await screen.findByRole('menu')).toBeInTheDocument();
      await user.keyboard('{Escape}');
      await waitFor(() => expect(screen.queryByRole('menu')).not.toBeInTheDocument());
      expect(container).toHaveAttribute('data-full-screen', 'overlay');
      await user.keyboard('{Escape}');
      expect(container).toHaveAttribute('data-full-screen', 'off');
    });

    it('[spec:canvas-view#S16] leaves full screen when nothing is left to show', async () => {
      const user = userEvent.setup();
      const { push } = renderCanvas();
      await openCanvas(user);
      await user.click(screen.getByRole('button', { name: 'Full screen' }));

      push({ ok: true, graph: { ...sampleGraph(), groups: [] } });
      expect(screen.queryByRole('toolbar', { name: 'Canvas controls' })).not.toBeInTheDocument();
      expect(document.body.querySelector('[inert]')).toBeNull();
      push({ ok: true, graph: sampleGraph() });
      expect(await screen.findByRole('button', { name: 'Full screen' })).toBeInTheDocument();
      expect(screen.getByRole('region', { name: 'Canvas' }).closest('[data-full-screen]')).toHaveAttribute('data-full-screen', 'off');
    });
  });

  it('[spec:canvas-view#S17] marks an ended session frame green with the word Ended', async () => {
    const user = userEvent.setup();
    renderCanvas();
    await openCanvas(user);
    const canvas = screen.getByRole('region', { name: 'Canvas' });
    await within(canvas).findByText('Old session');
    const frame = canvas.querySelector<HTMLElement>('[data-kind="session"][data-session-status="ended"]')!;
    expect(frame).toHaveClass('border-success/70');
    const chip = within(frame).getByText('Ended').closest('[data-slot="session-status"]')!;
    expect(chip).toHaveClass('text-[var(--canvas-success-text)]');
    expect(chip.querySelector('svg')).not.toBeNull();
  });

  it('[spec:canvas-view#S17] marks an idle session and its idle main node as waiting', async () => {
    const graph = sampleGraph();
    const idle: TaskGraphResult = {
      ok: true,
      graph: {
        ...graph,
        groups: graph.groups.map((each) => (each.id === 'session:s1' ? { ...each, status: 'idle' } : each)),
        nodes: graph.nodes.map((each) => (each.id === 'main:s1' ? { ...each, status: 'idle' } : each)),
      },
    };
    const user = userEvent.setup();
    renderCanvas(idle);
    await openCanvas(user);
    const canvas = screen.getByRole('region', { name: 'Canvas' });
    await within(canvas).findByText('Cart rework');
    const frame = canvas.querySelector<HTMLElement>('[data-kind="session"][data-session-status="idle"]')!;
    expect(frame).toHaveClass('border-warning');
    const chip = within(frame).getByText('Idle · waiting').closest('[data-slot="session-status"]')!;
    expect(chip).toHaveTextContent(/waiting for input or has paused/);

    const main = canvas.querySelector<HTMLElement>('.react-flow__node[data-id="main:s1"] [data-status]')!;
    expect(main).toHaveAttribute('data-status', 'idle');
    expect(main).toHaveClass('border-warning');
    expect(within(main).getByText('Idle · waiting')).toHaveClass('text-[var(--canvas-warning-text)]');
  });

  it('[spec:canvas-view#S14] says when the installed CLI has no graph command', async () => {
    const user = userEvent.setup();
    renderCanvas({ ok: false, reason: 'unsupported', detail: null });
    const list = await screen.findByRole('list', { name: 'Projects with tasks' });
    await user.click(within(list).getByText('storefront').closest('button')!);
    await user.click(within(screen.getByRole('group', { name: 'View' })).getByRole('button', { name: 'Canvas' }));
    expect(await screen.findByText('The installed devteam CLI does not support the canvas')).toBeInTheDocument();
    await user.click(within(screen.getByRole('group', { name: 'View' })).getByRole('button', { name: 'Board' }));
    expect(screen.getByRole('group', { name: 'Kanban columns' })).toBeVisible();
  });
});

describe('canvasPositions', () => {
  it('treats a stored __proto__ key as data, never as the prototype', () => {
    localStorage.setItem('devteam.canvas.positions.v1:p', '{"__proto__": {"x": 1, "y": 2}, "n": {"x": 3, "y": 4}}');
    const loaded = loadPositions('p');
    expect(Object.keys(loaded)).toEqual(['n']);
    expect(Object.getPrototypeOf(loaded)).toBeNull();
    expect(Object.keys(savePosition('p', '__proto__', { x: 5, y: 6 }))).toEqual(['n']);
    expect(({} as Record<string, unknown>)['x']).toBeUndefined();
    localStorage.clear();
  });
});
