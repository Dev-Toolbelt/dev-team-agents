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
import type { BoardFeed, TaskGraphResult } from '../../src/shared/api.js';
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

function feed(): BoardFeed {
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
        ],
      }),
    ],
  });
}

function renderCanvas(result: TaskGraphResult = { ok: true, graph: sampleGraph() }) {
  let pushGraph: (next: TaskGraphResult) => void = () => undefined;
  const bridge = fakeBridge({
    taskBoard: vi.fn(() => Promise.resolve(feed())),
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

    await user.selectOptions(screen.getByLabelText('Show'), 'agents');
    await waitFor(() => expect(within(canvas).queryByText('Review the API')).not.toBeInTheDocument());
    expect(within(canvas).getByText('Build the cart API').closest('[data-status]')).toHaveTextContent('+2 hidden');

    await user.selectOptions(screen.getByLabelText('Show'), 'all');
    expect(await within(canvas).findByText('Review the API')).toBeInTheDocument();
  });

  it('[spec:canvas-view#S12] offers the outline as an accessible tree, driven from the keyboard', async () => {
    const user = userEvent.setup();
    renderCanvas();
    await openCanvas(user);
    await user.click(screen.getByRole('button', { name: 'Outline' }));
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
      await user.click(screen.getByRole('button', { name: 'Outline' }));
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
    await user.click(screen.getByRole('button', { name: 'Outline' }));
    fireEvent.click(screen.getByRole('treeitem', { name: 'backend-developer: Build the cart API' }));
    await user.click(await screen.findByRole('button', { name: 'Show on board' }));
    const view = screen.getByRole('group', { name: 'View' });
    expect(within(view).getByRole('button', { name: 'Board' })).toHaveAttribute('aria-pressed', 'true');
    await waitFor(() => expect(document.activeElement).toHaveAttribute('data-card', 's1:t4'));
  });

  it('[spec:canvas-view#S10] restores a stored position on mount and forgets it on Reset layout', async () => {
    localStorage.setItem('devteam.canvas.positions.v1:proj-a', JSON.stringify({ 'span:s1:b': { x: 700, y: 400 } }));
    const user = userEvent.setup();
    renderCanvas();
    await openCanvas(user);
    const reset = screen.getByRole('button', { name: 'Reset layout' });
    expect(reset).toBeEnabled();
    await user.click(reset);
    expect(reset).toBeDisabled();
    expect(localStorage.getItem('devteam.canvas.positions.v1:proj-a')).toBeNull();
  });

  it('[spec:canvas-view#S12] reveals an agent hidden in a collapsed session, raising the level and opening its details', async () => {
    const user = userEvent.setup();
    renderCanvas();
    await openCanvas(user);
    const canvas = screen.getByRole('region', { name: 'Canvas' });
    await user.selectOptions(screen.getByLabelText('Show'), 'sessions');
    await user.click(screen.getByRole('button', { name: 'Outline' }));
    expect(within(canvas).queryByText('Check the release')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('treeitem', { name: 'qa-specialist: Check the release' }));
    expect(await within(canvas).findByText('Check the release')).toBeInTheDocument();
    expect(within(canvas).getByRole('button', { name: 'Collapse session Old session' })).toBeInTheDocument();
    expect(screen.getByLabelText('Show')).toHaveValue('turns');
    expect(await screen.findByRole('complementary', { name: 'qa-specialist' })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('treeitem', { name: 'code-reviewer: Review the API' }));
    expect(await within(canvas).findByText('Review the API')).toBeInTheDocument();
    expect(screen.getByLabelText('Show')).toHaveValue('all');
    expect(await screen.findByRole('complementary', { name: 'code-reviewer' })).toBeInTheDocument();
  });

  it('[spec:canvas-view#S8] dims everything outside the focused line and restores it on a pane click or on close', async () => {
    const user = userEvent.setup();
    renderCanvas();
    await openCanvas(user);
    const canvas = screen.getByRole('region', { name: 'Canvas' });
    const card = (text: string) => within(canvas).getByText(text).closest('[data-status]')!;
    await within(canvas).findByText('Review the API');
    await user.click(screen.getByRole('button', { name: 'Outline' }));
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

    await user.click(screen.getByRole('button', { name: 'Outline' }));
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
