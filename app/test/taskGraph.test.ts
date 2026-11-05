/**
 * The canvas in the main process: the argv allow-list, the defensive `tasks graph` parser, the
 * mapping of a CLI answer to what the renderer is told, the per-project runner (debounce, poll,
 * coalescing, generation guard), the IPC subscription bookkeeping, and the preload surface.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { argvProblem, asTaskGraph, MAX_GRAPH_NODES } from '../src/cli/operations.js';
import { GRAPH_DEBOUNCE_MS, GRAPH_POLL_MS, TaskGraphRunner, toTaskGraphResult } from '../src/main/taskGraph.js';
import { GraphSubscriptions, graphProjectId } from '../src/main/taskGraphIpc.js';
import {
  CHANNELS,
  type BoardFeed,
  type BoardProject,
  type DevteamBridge,
  type OperationResult,
  type TaskGraph,
  type TaskGraphResult,
  type TaskGraphUpdate,
} from '../src/shared/api.js';

const invoke = vi.fn<(...args: unknown[]) => Promise<unknown>>((channel) => Promise.resolve(channel === CHANNELS.taskGraphSubscribe ? true : undefined));
const listeners = new Map<string, Set<(event: unknown, payload: unknown) => void>>();
let exposed: DevteamBridge | null = null;
vi.mock('electron', () => ({
  ipcMain: { handle: vi.fn() },
  ipcRenderer: {
    invoke: (...args: unknown[]) => invoke(...args),
    on: (channel: string, handler: (event: unknown, payload: unknown) => void) => {
      if (!listeners.has(channel)) listeners.set(channel, new Set());
      listeners.get(channel)!.add(handler);
    },
    removeListener: (channel: string, handler: (event: unknown, payload: unknown) => void) => {
      listeners.get(channel)?.delete(handler);
    },
  },
  contextBridge: {
    exposeInMainWorld: (_name: string, api: unknown) => {
      exposed = api as DevteamBridge;
    },
  },
}));

function graphBody(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    schema: 1,
    project_id: 'p1',
    as_of: 100,
    truncated: false,
    notices: [],
    groups: [
      { id: 'session:s1', kind: 'session', parent: null, label: 'S', status: 'active', prs: [], tokens: 0, usage_complete: false },
      { id: 'turn:s1:5', kind: 'turn', parent: 'session:s1', label: 'Prompt', command: null, at: 5, tokens: 0, usage_complete: false },
    ],
    nodes: [
      { id: 'main:s1', kind: 'main', group: 'session:s1', label: 'Main session', persona: null, status: 'running' },
      { id: 'span:s1:a', kind: 'agent', group: 'turn:s1:5', agent: 'qa', status: 'completed', todos: [] },
    ],
    edges: [{ id: 'e:main:s1>span:s1:a', from: 'main:s1', to: 'span:s1:a', kind: 'spawn' }],
    ...overrides,
  };
}

function parse(body: Record<string, unknown>): TaskGraph {
  const graph = asTaskGraph(body);
  if (typeof graph === 'string') throw new Error(graph);
  return graph;
}

// ── argv ──────────────────────────────────────────────────────────────────────

describe('tasks graph argv', () => {
  it('allows --project and --since, and nothing else', () => {
    expect(argvProblem(['tasks', 'graph', '--project', 'p1'])).toBeNull();
    expect(argvProblem(['tasks', 'graph', '--project', 'p1', '--since', '100'])).toBeNull();
    expect(argvProblem(['tasks', 'graph', '--path', '/x'])).toMatch(/may not be passed/);
    expect(argvProblem(['tasks', 'graph', 'extra'])).toMatch(/operand/);
  });
});

// ── the parser ────────────────────────────────────────────────────────────────

describe('asTaskGraph', () => {
  it('accepts the documented shape and fills defaults for absent keys', () => {
    const graph = parse(graphBody());
    expect(graph.groups).toHaveLength(2);
    const span = graph.nodes[1]!;
    expect(span).toMatchObject({ kind: 'agent', status: 'completed', label: null, tokens: 0, usage_complete: false, worktree: null, pr: null });
    expect(graph.groups[1]).toMatchObject({ status: null, provider: null, prs: [], started_at: null });
  });

  it('refuses only a document without a project_id', () => {
    expect(asTaskGraph({ groups: [] })).toMatch(/project_id/);
    expect(parse({ project_id: 'p1' })).toMatchObject({ schema: 1, groups: [], nodes: [], edges: [], notices: [], truncated: false });
  });

  it('never throws on hostile input', () => {
    for (const junk of [null, 1, 'x', [], { groups: 'x', nodes: {}, edges: 7, notices: 'n' }]) {
      expect(() => asTaskGraph({ project_id: 'p1', groups: junk, nodes: junk, edges: junk, notices: junk })).not.toThrow();
    }
  });

  it('drops malformed items and duplicate ids', () => {
    const graph = parse(
      graphBody({
        groups: [
          { id: 'session:s1', kind: 'session' },
          { id: 'session:s1', kind: 'session', label: 'dup' },
          { id: 'x', kind: 'canvas' },
          { kind: 'turn' },
          'junk',
        ],
        nodes: [
          { id: 'main:s1', kind: 'main', group: 'session:s1' },
          { id: 'orphan', kind: 'agent', group: 'turn:gone' },
          { kind: 'agent', group: 'session:s1' },
        ],
        edges: [
          { from: 'main:s1', to: 'main:s1', kind: 'spawn' },
          { id: 'e2', from: 'main:s1', to: 'nowhere', kind: 'spawn' },
          { id: 'e3', from: 'main:s1', to: 'main:s1', kind: 'teleport' },
        ],
      }),
    );
    expect(graph.groups.map((group) => group.id)).toEqual(['session:s1']);
    expect(graph.groups[0]!.label).toBe('session:s1');
    expect(graph.nodes.map((node) => node.id)).toEqual(['main:s1']);
    expect(graph.edges).toEqual([{ id: 'e:main:s1>main:s1', from: 'main:s1', to: 'main:s1', kind: 'spawn' }]);
  });

  it('degrades an unknown node kind to builtin and unknown statuses to null', () => {
    const graph = parse(
      graphBody({
        groups: [{ id: 'session:s1', kind: 'session', status: 'paused' }],
        nodes: [{ id: 'n', kind: 'hologram', group: 'session:s1', status: 'exploded', persona: 'wizard' }],
        edges: [],
      }),
    );
    expect(graph.groups[0]!.status).toBeNull();
    expect(graph.nodes[0]).toMatchObject({ kind: 'builtin', status: null, persona: null });
  });

  it('roots a group whose parent was dropped', () => {
    const graph = parse(graphBody({ groups: [{ id: 'turn:s1:5', kind: 'turn', parent: 'session:gone' }], nodes: [], edges: [] }));
    expect(graph.groups[0]!.parent).toBeNull();
  });

  it('[spec:canvas-view#S13] keeps the last output to one bounded line and rejects bad numbers', () => {
    const graph = parse(
      graphBody({
        nodes: [
          {
            id: 'main:s1', kind: 'main', group: 'session:s1', last_output: `line one\nline two ${'x'.repeat(300)}`,
            tokens: -5, duration_s: 'long', findings: 1.5, background: 'yes', todos: [{ key: 't', content: 'c' }, { content: 'no key' }],
          },
        ],
        edges: [],
      }),
    );
    const node = graph.nodes[0]!;
    expect(node.last_output).not.toMatch(/\n/);
    expect(node.last_output!.startsWith('line one line two')).toBe(true);
    expect(node.last_output!.length).toBe(140);
    expect(node).toMatchObject({ tokens: 0, duration_s: 0, findings: null, background: false });
    expect(node.todos).toEqual([{ key: 't', content: 'c', status: 'unknown' }]);
  });

  it('drops invisible characters that could disguise a label and breaks no line', () => {
    const hidden = `safe\u{E0041}\u{E0042}\uFE0F\u200B\u202E\u2066 text\u2028next\u2029end`;
    const graph = parse(graphBody({ nodes: [{ id: 'main:s1', kind: 'main', group: 'session:s1', label: hidden, last_output: hidden }], edges: [] }));
    expect(graph.nodes[0]!.label).toBe('safe text next end');
    expect(graph.nodes[0]!.last_output).toBe('safe text next end');
  });

  it('marks the graph truncated when a cap is hit or the CLI says so', () => {
    const nodes = Array.from({ length: MAX_GRAPH_NODES + 1 }, (_, i) => ({ id: `n${i}`, kind: 'agent', group: 'session:s1' }));
    expect(parse(graphBody({ nodes, edges: [] })).truncated).toBe(true);
    expect(parse(graphBody({ truncated: true })).truncated).toBe(true);
  });
});

// ── the answer the renderer gets ──────────────────────────────────────────────

const failure = (kind: string, message: string): OperationResult<TaskGraph> =>
  ({ ok: false, kind, message, exitCode: 2, command: 'devteam tasks graph', durationMs: 1 }) as OperationResult<TaskGraph>;

describe('toTaskGraphResult', () => {
  it('maps an older CLI without the command to unsupported', () => {
    expect(toTaskGraphResult(failure('usage', "argument tasks_command: invalid choice: 'graph'"))).toMatchObject({ ok: false, reason: 'unsupported' });
    expect(toTaskGraphResult(failure('usage', 'unrecognized arguments: --project p1'))).toMatchObject({ reason: 'unsupported' });
  });

  it('maps no CLI to unavailable and anything else to error with the CLI message', () => {
    expect(toTaskGraphResult(null)).toMatchObject({ ok: false, reason: 'unavailable' });
    expect(toTaskGraphResult(failure('unavailable', 'no cli'))).toMatchObject({ reason: 'unavailable', detail: 'no cli' });
    expect(toTaskGraphResult(failure('environment', 'store locked'))).toEqual({ ok: false, reason: 'error', detail: 'store locked' });
    expect(toTaskGraphResult(failure('usage', 'bad --since'))).toMatchObject({ reason: 'error' });
  });

  it('passes a graph through', () => {
    const graph = parse(graphBody());
    expect(toTaskGraphResult({ ok: true, outcome: 'success', data: graph, command: 'x', durationMs: 1 })).toEqual({ ok: true, graph });
  });
});

// ── the runner ────────────────────────────────────────────────────────────────

interface Timer {
  fn: () => void;
  ms: number;
  live: boolean;
}

function harness() {
  const timers: Timer[] = [];
  const updates: TaskGraphUpdate[] = [];
  const pending: { projectId: string; resolve: (r: OperationResult<TaskGraph> | null) => void }[] = [];
  let asOf = 0;
  const run = vi.fn(
    (projectId: string) =>
      new Promise<OperationResult<TaskGraph> | null>((resolve) => {
        pending.push({ projectId, resolve });
      }),
  );
  const runner = new TaskGraphRunner({
    run,
    onChange: (update) => updates.push(update),
    setTimer: (fn, ms) => {
      const timer = { fn, ms, live: true };
      timers.push(timer);
      return timer;
    },
    clearTimer: (handle) => {
      (handle as Timer).live = false;
    },
  });
  const ok = (projectId = 'p1'): OperationResult<TaskGraph> => ({
    ok: true,
    outcome: 'success',
    data: parse(graphBody({ project_id: projectId, as_of: (asOf += 1) })),
    command: 'devteam tasks graph',
    durationMs: 1,
  });
  const settle = async (result?: OperationResult<TaskGraph> | null) => {
    const next = pending.shift()!;
    next.resolve(result === undefined ? ok(next.projectId) : result);
    await new Promise((resolve) => setTimeout(resolve, 0));
  };
  const fire = (ms: number) => {
    for (const timer of timers.filter((t) => t.live && t.ms === ms)) {
      timer.live = false;
      timer.fn();
    }
  };
  return { runner, run, updates, pending, settle, fire, ok, timers };
}

const project = (id: string): BoardProject => ({ project_id: id }) as unknown as BoardProject;
const feed = (...projects: BoardProject[]): BoardFeed => ({ status: 'live', detail: null, projects });

describe('TaskGraphRunner', () => {
  it('reads on the first subscribe and pushes the result', async () => {
    const h = harness();
    h.runner.subscribe('p1');
    expect(h.run).toHaveBeenCalledTimes(1);
    await h.settle();
    expect(h.updates).toHaveLength(1);
    expect(h.updates[0]!.projectId).toBe('p1');
    expect(h.updates[0]!.result.ok).toBe(true);
  });

  it('leaves nothing cached behind a get() for a project nobody watches', async () => {
    const h = harness();
    const first = h.runner.get('p2');
    await h.settle();
    expect((await first).ok).toBe(true);
    void h.runner.get('p2');
    expect(h.run).toHaveBeenCalledTimes(2);
    await h.settle();
    expect(h.runner.subscribed('p2')).toBe(false);
    expect(h.updates).toEqual([]);
  });

  it('serves get() from the cache while subscribed, and reads afresh when not', async () => {
    const h = harness();
    h.runner.subscribe('p1');
    await h.settle();
    await h.runner.get('p1');
    expect(h.run).toHaveBeenCalledTimes(1);
    const other = h.runner.get('p2');
    expect(h.run).toHaveBeenCalledTimes(2);
    await h.settle();
    expect((await other).ok).toBe(true);
    expect(h.updates.map((u) => u.projectId)).toEqual(['p1']);
  });

  it('re-reads a changed subscribed project after the debounce, once per burst', async () => {
    const h = harness();
    h.runner.subscribe('p1');
    await h.settle();
    const a = project('p1');
    h.runner.boardChanged(feed(a));
    h.runner.boardChanged(feed(project('p1')));
    h.runner.boardChanged(feed(project('p1'), project('p2')));
    expect(h.run).toHaveBeenCalledTimes(1);
    h.fire(GRAPH_DEBOUNCE_MS);
    expect(h.run).toHaveBeenCalledTimes(2);
    expect(h.run).toHaveBeenLastCalledWith('p1');
  });

  it('ignores a feed in which the project snapshot did not change', async () => {
    const h = harness();
    h.runner.subscribe('p1');
    await h.settle();
    const same = project('p1');
    h.runner.boardChanged(feed(same));
    h.fire(GRAPH_DEBOUNCE_MS);
    await h.settle();
    h.runner.boardChanged(feed(same));
    h.fire(GRAPH_DEBOUNCE_MS);
    expect(h.run).toHaveBeenCalledTimes(2);
  });

  it('polls while subscribed and stops after the last unsubscribe', async () => {
    const h = harness();
    h.runner.subscribe('p1');
    h.runner.subscribe('p1');
    await h.settle();
    h.fire(GRAPH_POLL_MS);
    expect(h.run).toHaveBeenCalledTimes(2);
    await h.settle();
    h.runner.unsubscribe('p1');
    h.fire(GRAPH_POLL_MS);
    expect(h.run).toHaveBeenCalledTimes(3);
    await h.settle();
    h.runner.unsubscribe('p1');
    expect(h.runner.subscribed('p1')).toBe(false);
    h.fire(GRAPH_POLL_MS);
    h.runner.boardChanged(feed(project('p1')));
    h.fire(GRAPH_DEBOUNCE_MS);
    expect(h.run).toHaveBeenCalledTimes(3);
  });

  it('coalesces changes during a read into exactly one more read', async () => {
    const h = harness();
    h.runner.subscribe('p1');
    h.runner.schedule('p1');
    h.fire(GRAPH_DEBOUNCE_MS);
    h.runner.schedule('p1');
    h.fire(GRAPH_DEBOUNCE_MS);
    expect(h.run).toHaveBeenCalledTimes(1);
    await h.settle();
    expect(h.run).toHaveBeenCalledTimes(2);
    await h.settle();
    expect(h.run).toHaveBeenCalledTimes(2);
  });

  it('drops the answer of a read overtaken by an unsubscribe (generation guard)', async () => {
    const h = harness();
    h.runner.subscribe('p1');
    h.runner.unsubscribe('p1');
    await h.settle();
    expect(h.updates).toHaveLength(0);
    h.runner.subscribe('p1');
    await h.settle();
    expect(h.updates).toHaveLength(1);
  });

  it('does not push a result identical to the last one', async () => {
    const h = harness();
    h.runner.subscribe('p1');
    const same = h.ok();
    await h.settle(same);
    h.fire(GRAPH_POLL_MS);
    await h.settle(same);
    expect(h.updates).toHaveLength(1);
  });

  it('keeps the last good graph when a re-read fails, but reports unsupported', async () => {
    const h = harness();
    h.runner.subscribe('p1');
    await h.settle();
    h.fire(GRAPH_POLL_MS);
    await h.settle(failure('environment', 'flaky'));
    expect(h.updates).toHaveLength(1);
    h.fire(GRAPH_POLL_MS);
    await h.settle(failure('usage', "invalid choice: 'graph'"));
    expect(h.updates.at(-1)!.result).toMatchObject({ ok: false, reason: 'unsupported' });
  });

  it('turns a thrown run into an error result', async () => {
    const h = harness();
    h.run.mockImplementationOnce(() => Promise.reject(new Error('boom')));
    h.runner.subscribe('p1');
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(h.updates[0]!.result).toMatchObject({ ok: false, reason: 'error' });
  });

  it('does nothing after dispose', async () => {
    const h = harness();
    h.runner.subscribe('p1');
    h.runner.dispose();
    await h.settle();
    h.runner.subscribe('p1');
    h.fire(GRAPH_POLL_MS);
    expect(h.run).toHaveBeenCalledTimes(1);
    expect(h.updates).toHaveLength(0);
  });
});

// ── the IPC boundary ──────────────────────────────────────────────────────────

describe('graphProjectId', () => {
  it('accepts registry ids and refuses anything that could be a flag or worse', () => {
    expect(graphProjectId('3f2a9c1e-0b4d-4e6f-9a8b-7c6d5e4f3a2b')).toBe('3f2a9c1e-0b4d-4e6f-9a8b-7c6d5e4f3a2b');
    for (const bad of ['', '--path', 'a b', 'a\nb', '../x', 'x'.repeat(129), 7, null, {}]) {
      expect(graphProjectId(bad), JSON.stringify(bad)).toBeNull();
    }
  });
});

describe('GraphSubscriptions', () => {
  function sender(id: number) {
    const destroyed: (() => void)[] = [];
    return { id, once: (_: 'destroyed', listener: () => void) => destroyed.push(listener), destroy: () => destroyed.forEach((fn) => fn()) };
  }

  it('counts per renderer and releases everything when a renderer goes away', () => {
    const subscribe = vi.fn();
    const unsubscribe = vi.fn();
    const subs = new GraphSubscriptions({ subscribe, unsubscribe });
    const a = sender(1);
    subs.add(a, 'p1');
    subs.add(a, 'p1');
    subs.add(a, 'p2');
    subs.remove(1, 'p1');
    subs.remove(1, 'p9');
    subs.remove(2, 'p1');
    expect(subscribe).toHaveBeenCalledTimes(3);
    expect(unsubscribe).toHaveBeenCalledTimes(1);
    a.destroy();
    expect(unsubscribe.mock.calls.map(([id]) => id as string).sort()).toEqual(['p1', 'p1', 'p2']);
    subs.remove(1, 'p2');
    expect(unsubscribe).toHaveBeenCalledTimes(3);
  });

  function livingSender(id: number) {
    const handlers = new Map<string, ((details?: unknown) => void)[]>();
    const add = (event: string, listener: (details?: unknown) => void) => handlers.set(event, [...(handlers.get(event) ?? []), listener]);
    return {
      id,
      once: (event: 'destroyed', listener: () => void) => add(event, listener),
      on: (event: string, listener: (details?: unknown) => void) => add(event, listener),
      emit: (event: string, details?: unknown) => (handlers.get(event) ?? []).forEach((fn) => fn(details)),
      count: (event: string) => handlers.get(event)?.length ?? 0,
    };
  }

  it('releases a renderer that crashed or loaded a new document, but not on in-page navigation', () => {
    const unsubscribe = vi.fn();
    const subs = new GraphSubscriptions({ subscribe: vi.fn(), unsubscribe });
    const a = livingSender(1);
    subs.add(a as never, 'p1');
    a.emit('did-start-navigation', { isMainFrame: true, isSameDocument: true });
    a.emit('did-start-navigation', { isMainFrame: false, isSameDocument: false });
    expect(unsubscribe).not.toHaveBeenCalled();
    a.emit('did-start-navigation', { isMainFrame: true, isSameDocument: false });
    expect(unsubscribe).toHaveBeenCalledWith('p1');
    subs.add(a as never, 'p2');
    expect(a.count('did-start-navigation')).toBe(1);
    a.emit('render-process-gone');
    expect(unsubscribe.mock.calls.map(([id]) => id as string)).toEqual(['p1', 'p2']);
  });

  it('caps how many projects one renderer may watch', () => {
    const subs = new GraphSubscriptions({ subscribe: vi.fn(), unsubscribe: vi.fn() });
    const a = sender(1);
    for (let i = 0; i < 64; i += 1) expect(subs.add(a, `p${i}`)).toBe(true);
    expect(subs.add(a, 'one-more')).toBe(false);
    expect(subs.add(a, 'p0')).toBe(true);
  });
});

// ── the preload surface ───────────────────────────────────────────────────────

describe('preload bridge — task graph', () => {
  beforeEach(async () => {
    invoke.mockClear();
    listeners.clear();
    await import('../src/preload/index.js');
  });

  it('gets a graph by project id over its own channel', async () => {
    await exposed!.taskGraph('p1');
    expect(invoke).toHaveBeenCalledWith(CHANNELS.taskGraph, 'p1');
  });

  it('subscribes, hears only its project, and unsubscribes once', () => {
    const heard: TaskGraphResult[] = [];
    const stop = exposed!.onTaskGraph('p1', (result) => heard.push(result));
    expect(invoke).toHaveBeenCalledWith(CHANNELS.taskGraphSubscribe, 'p1');
    const push = (projectId: string): void => {
      for (const handler of listeners.get(CHANNELS.taskGraphChanged) ?? []) {
        handler({}, { projectId, result: { ok: false, reason: 'error', detail: projectId } });
      }
    };
    push('p2');
    push('p1');
    expect(heard).toEqual([{ ok: false, reason: 'error', detail: 'p1' }]);
    stop();
    stop();
    expect(invoke.mock.calls.filter(([channel]) => channel === CHANNELS.taskGraphUnsubscribe)).toHaveLength(1);
    push('p1');
    expect(heard).toHaveLength(1);
  });

  it('says so when the main process refuses or fails a subscription', async () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => undefined);
    invoke.mockResolvedValueOnce(false);
    const stop = exposed!.onTaskGraph('p1', () => undefined);
    invoke.mockRejectedValueOnce(new Error('gone'));
    const other = exposed!.onTaskGraph('p2', () => undefined);
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(warn.mock.calls.map(([line]) => String(line))).toEqual([
      expect.stringContaining('subscription for p1 was refused'),
      expect.stringContaining('subscription for p2 failed'),
    ]);
    stop();
    other();
    warn.mockRestore();
  });
});
