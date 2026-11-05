/**
 * The canvas model (ADR-0063, spec canvas-view): deterministic layout, collapse levels, user
 * overrides, focus, heat and the label rules that keep unknown usage from reading as zero.
 */
import { describe, expect, it } from 'vitest';

import {
  NODE_WIDTH,
  defaultCollapsed,
  effectiveCollapsed,
  explicitlyExpanded,
  filterGraphByPeriod,
  focusSet,
  frameTokensLabel,
  heatTone,
  indexGraph,
  layoutGraph,
  nodeTokensLabel,
  outlineTree,
  revealPlan,
  roleFamily,
  statusTone,
  traceProblems,
  visibleGraph,
  type LayoutBox,
} from '../src/renderer/canvasModel.js';
import type { TaskGraph } from '../src/shared/api.js';
import { NOW } from './fixtures/board.js';
import { TURN, sampleGraph } from './fixtures/canvasGraph.js';

const ALL = { level: 'all' as const, collapsed: new Set<string>() };

function box(boxes: readonly LayoutBox[], id: string): LayoutBox {
  const found = boxes.find((each) => each.id === id);
  if (found === undefined) throw new Error(`no box ${id}`);
  return found;
}

function shuffled(graph: TaskGraph): TaskGraph {
  return { ...graph, groups: [...graph.groups].reverse(), nodes: [...graph.nodes].reverse(), edges: [...graph.edges].reverse() };
}

describe('layoutGraph', () => {
  it('[spec:canvas-view#S11] lays the same data out in the same place, whatever the input order', () => {
    const first = layoutGraph(sampleGraph(), ALL);
    const second = layoutGraph(shuffled(sampleGraph()), ALL);
    const byId = (boxes: readonly LayoutBox[]) => Object.fromEntries(boxes.map((each) => [each.id, each]));
    expect(byId(second.boxes)).toEqual(byId(first.boxes));
    expect(layoutGraph(sampleGraph(), ALL)).toEqual(first);
  });

  it('puts parents before children, with children positioned inside their frame', () => {
    const { boxes } = layoutGraph(sampleGraph(), ALL);
    const seen = new Set<string>();
    for (const each of boxes) {
      if (each.parent !== null) expect(seen.has(each.parent)).toBe(true);
      seen.add(each.id);
    }
    const turn = box(boxes, TURN);
    expect(turn.parent).toBe('session:s1');
    for (const id of ['span:s1:a', 'span:s1:b', 'span:s1:a1', 'span:s1:a2']) {
      const node = box(boxes, id);
      expect(node.parent).toBe(TURN);
      expect(node.x + node.width).toBeLessThanOrEqual(turn.width);
      expect(node.y + node.height).toBeLessThanOrEqual(turn.height);
    }
  });

  it('[spec:canvas-view#S2] draws depth along y and orders siblings by start time', () => {
    const { boxes } = layoutGraph(sampleGraph(), ALL);
    const a = box(boxes, 'span:s1:a');
    const b = box(boxes, 'span:s1:b');
    const a1 = box(boxes, 'span:s1:a1');
    const a2 = box(boxes, 'span:s1:a2');
    // b started before a, so it is the left sibling.
    expect(b.x).toBeLessThan(a.x);
    expect(a.y).toBe(b.y);
    expect(a1.y).toBeGreaterThan(a.y);
    expect(a1.x).toBeLessThan(a2.x);
    // The parent sits centred over its children.
    expect(a.x + NODE_WIDTH / 2).toBeCloseTo((a1.x + a2.x + NODE_WIDTH) / 2);
  });

  it('places sessions side by side, newest first, and stacks a session\'s main above its turns', () => {
    const { boxes } = layoutGraph(sampleGraph(), ALL);
    const s1 = box(boxes, 'session:s1');
    const s2 = box(boxes, 'session:s2');
    expect(s1.x).toBeLessThan(s2.x);
    expect(box(boxes, 'main:s1').y).toBeLessThan(box(boxes, TURN).y);
  });

  it('[spec:canvas-view#S3] hangs the agents of a session without a trace straight off its frame', () => {
    const { boxes } = layoutGraph(sampleGraph(), ALL);
    expect(box(boxes, 'span:s2:t1').parent).toBe('session:s2');
    expect(box(boxes, 'span:s2:t1').y).toBeGreaterThan(box(boxes, 'main:s2').y);
  });

  it('[spec:canvas-view#S10] an override wins for that node only and grows the frame to hold it', () => {
    const auto = layoutGraph(sampleGraph(), ALL);
    const moved = layoutGraph(sampleGraph(), ALL, { 'span:s1:b': { x: 900, y: 600 } });
    expect(box(moved.boxes, 'span:s1:b')).toMatchObject({ x: 900, y: 600 });
    expect(box(moved.boxes, 'span:s1:a1')).toEqual(box(auto.boxes, 'span:s1:a1'));
    expect(box(moved.boxes, TURN).width).toBeGreaterThanOrEqual(900 + NODE_WIDTH);
    expect(box(moved.boxes, TURN).height).toBeGreaterThanOrEqual(600 + 132);
    // Without the override, everything is back to the automatic layout.
    expect(layoutGraph(sampleGraph(), ALL, {})).toEqual(auto);
  });

  it('ignores a malformed override and moves a dragged session frame', () => {
    const auto = layoutGraph(sampleGraph(), ALL);
    const bad = layoutGraph(sampleGraph(), ALL, { 'span:s1:b': { x: Number.NaN, y: 3 } });
    expect(box(bad.boxes, 'span:s1:b')).toEqual(box(auto.boxes, 'span:s1:b'));
    const frame = layoutGraph(sampleGraph(), ALL, { 'session:s2': { x: -500, y: 40 } });
    expect(box(frame.boxes, 'session:s2')).toMatchObject({ x: -500, y: 40 });
  });
});

describe('visibleGraph', () => {
  it('[spec:canvas-view#S7] sessions only: every session is a collapsed frame with its node count', () => {
    const view = visibleGraph(sampleGraph(), { level: 'sessions', collapsed: new Set() });
    expect(view.visible.size).toBe(0);
    expect(view.sessions.map((each) => [each.group.id, each.collapsed, each.hidden])).toEqual([
      ['session:s1', true, 5],
      ['session:s2', true, 2],
    ]);
  });

  it('[spec:canvas-view#S7] turns: main nodes stay, turns collapse and say how much they hide', () => {
    const view = visibleGraph(sampleGraph(), { level: 'turns', collapsed: new Set() });
    expect([...view.visible].sort()).toEqual(['main:s1', 'main:s2', 'span:s2:t1']);
    expect(view.sessions[0]!.turns[0]).toMatchObject({ collapsed: true, hidden: 4 });
  });

  it('[spec:canvas-view#S7] top-level agents: sub-agents are hidden and counted on their parent', () => {
    const view = visibleGraph(sampleGraph(), { level: 'agents', collapsed: new Set() });
    expect(view.visible.has('span:s1:a')).toBe(true);
    expect(view.visible.has('span:s1:a1')).toBe(false);
    expect(view.hiddenBelow.get('span:s1:a')).toBe(2);
    expect(view.edges.map((each) => each.to)).not.toContain('span:s1:a1');
  });

  it('[spec:canvas-view#S7] collapsing one agent hides only its subtree, and expanding restores it', () => {
    const collapsed = visibleGraph(sampleGraph(), { level: 'all', collapsed: new Set(['span:s1:a']) });
    expect(collapsed.visible.has('span:s1:a')).toBe(true);
    expect(collapsed.visible.has('span:s1:a2')).toBe(false);
    expect(collapsed.visible.has('span:s1:b')).toBe(true);
    expect(visibleGraph(sampleGraph(), ALL).visible.size).toBe(7);
  });

  it('[spec:canvas-view#S7] a frame or agent expanded by hand opens even where the level folds it', () => {
    const expanded = explicitlyExpanded(new Map([['session:s1', false], [TURN, false], ['span:s1:a', false], ['span:s1:b', true]]));
    expect([...expanded].sort()).toEqual(['session:s1', 'span:s1:a', TURN].sort());
    const sessions = visibleGraph(sampleGraph(), { level: 'sessions', collapsed: new Set(), expanded: new Set(['session:s1']) });
    expect(sessions.sessions.map((each) => [each.group.id, each.collapsed])).toEqual([
      ['session:s1', false],
      ['session:s2', true],
    ]);
    expect(sessions.sessions[0]!.turns[0]).toMatchObject({ collapsed: true });
    const turns = visibleGraph(sampleGraph(), { level: 'turns', collapsed: new Set(), expanded: new Set([TURN]) });
    expect(turns.sessions[0]!.turns[0]).toMatchObject({ collapsed: false, hidden: 0 });
    const agents = visibleGraph(sampleGraph(), { level: 'agents', collapsed: new Set(), expanded: new Set(['span:s1:a']) });
    expect(agents.visible.has('span:s1:a1')).toBe(true);
  });

  it('starts ended sessions collapsed, and an explicit choice overrides that default', () => {
    expect([...defaultCollapsed(sampleGraph())]).toEqual(['session:s2']);
    expect(effectiveCollapsed(sampleGraph(), new Map([['session:s2', false]])).has('session:s2')).toBe(false);
    expect(effectiveCollapsed(sampleGraph(), new Map([['span:s1:a', true]])).has('span:s1:a')).toBe(true);
    // A choice is the state picked, not a flip: a session expanded while open stays expanded once it ends.
    const ended = sampleGraph();
    const endedNow = { ...ended, groups: ended.groups.map((each) => (each.id === 'session:s1' ? { ...each, status: 'ended' as const } : each)) };
    expect(effectiveCollapsed(endedNow, new Map([['session:s1', false]])).has('session:s1')).toBe(false);
    expect(effectiveCollapsed(sampleGraph(), new Map([['session:s1', false]])).has('session:s1')).toBe(false);
  });
});

describe('filterGraphByPeriod', () => {
  it('keeps open sessions and the ended ones that ended inside the period', () => {
    const narrowed = filterGraphByPeriod(sampleGraph(), NOW - 3000);
    expect(narrowed.groups.map((each) => each.id)).toEqual(['session:s1', TURN]);
    expect(narrowed.nodes.some((each) => each.group === 'session:s2')).toBe(false);
    expect(narrowed.edges.some((each) => each.from === 'main:s2')).toBe(false);
    expect(filterGraphByPeriod(sampleGraph(), null)).toEqual(sampleGraph());
  });
});

describe('focusSet', () => {
  it('[spec:canvas-view#S8] holds the node, its ancestors and its descendants', () => {
    expect([...focusSet(sampleGraph(), 'span:s1:a')].sort()).toEqual(['main:s1', 'span:s1:a', 'span:s1:a1', 'span:s1:a2']);
    expect([...focusSet(sampleGraph(), 'span:s1:a1')].sort()).toEqual(['main:s1', 'span:s1:a', 'span:s1:a1']);
    expect(focusSet(sampleGraph(), 'nope').size).toBe(0);
  });
});

describe('heat and tones', () => {
  it('[spec:canvas-view#S9] scales with tokens and keeps unknown usage apart from the lowest level', () => {
    expect(heatTone(null, 1000)).toBe('unknown');
    expect(heatTone(0, 1000)).toBe(0);
    expect(heatTone(1, 1000)).toBe(1);
    expect(heatTone(500, 1000)).toBe(2);
    expect(heatTone(1000, 1000)).toBe(4);
    expect(heatTone(50, 0)).toBe(0);
  });

  it('[spec:canvas-view#S5] shows n/a for unknown usage and marks an incomplete frame total', () => {
    expect(nodeTokensLabel({ kind: 'agent', tokens: 0, subtree_tokens: 0, usage_complete: false })).toBe('n/a');
    expect(nodeTokensLabel({ kind: 'agent', tokens: 12_345, subtree_tokens: 20_000, usage_complete: true })).toBe('12k');
    // The main node reports no work of its own: it shows the session total, never a bare 0.
    expect(nodeTokensLabel({ kind: 'main', tokens: 0, subtree_tokens: 12_345, usage_complete: true })).toBe('12k');
    expect(nodeTokensLabel({ kind: 'main', tokens: 0, subtree_tokens: 0, usage_complete: false })).toBe('n/a');
    expect(frameTokensLabel({ tokens: 1500, usage_complete: false })).toBe('1.5k+ tokens (incomplete)');
    expect(frameTokensLabel({ tokens: 0, usage_complete: false })).toBe('tokens n/a');
    expect(frameTokensLabel({ tokens: 900, usage_complete: true })).toBe('900 tokens');
  });

  it('[spec:canvas-view#S4] gives every status a word, not only a tone', () => {
    expect(statusTone('running')).toEqual({ tone: 'running', label: 'Running' });
    expect(statusTone('idle')).toEqual({ tone: 'idle', label: 'Idle' });
    expect(statusTone('failed').label).toBe('Failed');
    expect(statusTone('interrupted').label).toBe('Interrupted');
    expect(statusTone(null).tone).toBe('unknown');
  });

  it('[spec:canvas-view#S4] groups roles into families, namespaced names included', () => {
    expect(roleFamily(null, 'main')).toBe('orchestration');
    expect(roleFamily('software-architect')).toBe('planning');
    expect(roleFamily('devteam:backend-developer')).toBe('implementation');
    expect(roleFamily('frontend-reviewer')).toBe('review-qa');
    expect(roleFamily('qa-specialist')).toBe('review-qa');
    expect(roleFamily('anything', 'review')).toBe('review-qa');
    expect(roleFamily('Explore', 'builtin')).toBe('builtin');
    expect(roleFamily(null)).toBe('builtin');
  });
});

describe('outlineTree', () => {
  it('[spec:canvas-view#S12] lists the whole hierarchy whatever the collapse level', () => {
    const tree = outlineTree(sampleGraph());
    expect(tree.map((each) => each.id)).toEqual(['session:s1', 'session:s2']);
    const s1 = tree[0]!;
    expect(s1.children.map((each) => each.id)).toEqual(['main:s1', TURN]);
    const turn = s1.children[1]!;
    expect(turn.children.map((each) => each.id)).toEqual(['span:s1:b', 'span:s1:a']);
    expect(turn.children[1]!.children.map((each) => each.id)).toEqual(['span:s1:a1', 'span:s1:a2']);
    expect(turn.children[1]!.label).toBe('backend-developer: Build the cart API');
  });
});

describe('revealPlan', () => {
  it('opens the frames and ancestors that hide a node and raises the level only as far as it must', () => {
    const index = indexGraph(sampleGraph());
    expect(revealPlan(index, 'span:s2:t1', 'sessions')).toEqual({ level: 'turns', expand: ['session:s2'] });
    expect(revealPlan(index, 'span:s1:a1', 'turns')).toEqual({ level: 'all', expand: ['session:s1', TURN, 'span:s1:a'] });
    expect(revealPlan(index, 'span:s1:a', 'sessions')).toEqual({ level: 'agents', expand: ['session:s1', TURN] });
    expect(revealPlan(index, TURN, 'sessions')).toEqual({ level: 'turns', expand: ['session:s1'] });
    expect(revealPlan(index, 'session:s2', 'agents')).toEqual({ level: 'agents', expand: [] });
    expect(revealPlan(index, 'nope', 'all')).toBeNull();
  });
});

describe('traceProblems', () => {
  it('reads missing and unreadable traces from the notices', () => {
    expect([...traceProblems(['no_trace:s2', 'bad_trace:s1', 'other'])]).toEqual([
      ['s2', 'missing'],
      ['s1', 'unreadable'],
    ]);
  });
});
