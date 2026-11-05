/**
 * The canvas as plain data (ADR-0063): what is visible at a collapse level, where every frame and
 * node sits, which nodes a focus keeps prominent, and the tones the screen styles them with. No
 * React here — every function is pure, deterministic and returns new values.
 *
 * Layout: one frame per session, side by side, newest first. Inside a session the main node sits
 * on top and the turn frames stack below it in time order; inside a turn the agent spans form a
 * tidy tree with depth along y, siblings ordered by (started_at, id). Positions of a frame's
 * children are relative to that frame, which is what React Flow expects of child nodes.
 */
import type { GraphEdge, GraphGroup, GraphNode, GraphNodeKind, GraphNodeStatus, TaskGraph } from '../shared/api.js';

export const NODE_WIDTH = 264;
export const NODE_HEIGHT = 132;
export const GAP_X = 24;
export const GAP_Y = 48;
export const FRAME_PAD = 20;
export const TURN_HEADER = 40;
export const TURN_GAP = 24;
export const SESSION_HEADER = 72;
export const SESSION_GAP = 96;
export const COLLAPSED_TURN_HEIGHT = TURN_HEADER + 12;
export const COLLAPSED_SESSION_WIDTH = 340;
export const COLLAPSED_SESSION_HEIGHT = SESSION_HEADER + 36;

export type CollapseLevel = 'sessions' | 'turns' | 'agents' | 'all';

export const COLLAPSE_LEVELS: readonly { readonly value: CollapseLevel; readonly label: string }[] = [
  { value: 'sessions', label: 'Sessions only' },
  { value: 'turns', label: 'Turns' },
  { value: 'agents', label: 'Top-level agents' },
  { value: 'all', label: 'Everything' },
];

export interface XY {
  readonly x: number;
  readonly y: number;
}

export type Overrides = Readonly<Record<string, XY>>;

// ── indexing ─────────────────────────────────────────────────────────────────

export interface GraphIndex {
  readonly groups: ReadonlyMap<string, GraphGroup>;
  readonly nodes: ReadonlyMap<string, GraphNode>;
  /** Spawn parent of a node (main or span), from the `spawn` edges. */
  readonly parent: ReadonlyMap<string, string>;
  /** Spawn children of a node, sorted by (started_at, id). */
  readonly children: ReadonlyMap<string, readonly string[]>;
}

function byStart(a: GraphNode, b: GraphNode): number {
  const sa = a.started_at ?? Number.POSITIVE_INFINITY;
  const sb = b.started_at ?? Number.POSITIVE_INFINITY;
  if (sa !== sb) return sa < sb ? -1 : 1;
  return a.id < b.id ? -1 : a.id > b.id ? 1 : 0;
}

export function indexGraph(graph: TaskGraph): GraphIndex {
  const groups = new Map(graph.groups.map((each) => [each.id, each]));
  const nodes = new Map(graph.nodes.map((each) => [each.id, each]));
  const parent = new Map<string, string>();
  const kids = new Map<string, GraphNode[]>();
  for (const edge of graph.edges) {
    if (edge.kind !== 'spawn') continue;
    const child = nodes.get(edge.to);
    if (child === undefined || !nodes.has(edge.from) || parent.has(edge.to) || edge.from === edge.to) continue;
    parent.set(edge.to, edge.from);
    const list = kids.get(edge.from) ?? [];
    list.push(child);
    kids.set(edge.from, list);
  }
  const children = new Map<string, readonly string[]>();
  for (const [id, list] of kids) children.set(id, [...list].sort(byStart).map((each) => each.id));
  return { groups, nodes, parent, children };
}

/** The session group a node or group belongs to; `null` when the graph does not say. */
export function sessionOf(index: GraphIndex, id: string): string | null {
  const node = index.nodes.get(id);
  let group = index.groups.get(node === undefined ? id : node.group);
  for (let hops = 0; group !== undefined && hops < 4; hops += 1) {
    if (group.kind === 'session') return group.id;
    group = group.parent === null ? undefined : index.groups.get(group.parent);
  }
  return null;
}

/** `session:<sid>` → `<sid>`. */
export function sessionIdOf(groupId: string): string {
  return groupId.startsWith('session:') ? groupId.slice('session:'.length) : groupId;
}

function ancestors(index: GraphIndex, id: string): string[] {
  const out: string[] = [];
  const seen = new Set<string>([id]);
  for (let at = index.parent.get(id); at !== undefined && !seen.has(at); at = index.parent.get(at)) {
    out.push(at);
    seen.add(at);
  }
  return out;
}

function descendants(index: GraphIndex, id: string): string[] {
  const out: string[] = [];
  const seen = new Set<string>([id]);
  const stack = [...(index.children.get(id) ?? [])];
  while (stack.length > 0) {
    const next = stack.pop()!;
    if (seen.has(next)) continue;
    seen.add(next);
    out.push(next);
    stack.push(...(index.children.get(next) ?? []));
  }
  return out;
}

// ── period ───────────────────────────────────────────────────────────────────

/**
 * The graph narrowed to the sessions the period keeps: a session still open always stays, an
 * ended one stays when it ended (or, lacking that, started) at or after `cutoff`.
 */
export function filterGraphByPeriod(graph: TaskGraph, cutoff: number | null): TaskGraph {
  if (cutoff === null) return graph;
  const kept = new Set(
    graph.groups
      .filter((each) => each.kind === 'session')
      .filter((each) => each.status !== 'ended' || (each.ended_at ?? each.started_at ?? 0) >= cutoff)
      .map((each) => each.id),
  );
  const groups = graph.groups.filter((each) => (each.kind === 'session' ? kept.has(each.id) : each.parent !== null && kept.has(each.parent)));
  const groupIds = new Set(groups.map((each) => each.id));
  const nodes = graph.nodes.filter((each) => groupIds.has(each.group));
  const nodeIds = new Set(nodes.map((each) => each.id));
  const edges = graph.edges.filter((each) => nodeIds.has(each.from) && nodeIds.has(each.to));
  return { ...graph, groups, nodes, edges };
}

/** Sessions that start collapsed: the ended ones. */
export function defaultCollapsed(graph: TaskGraph): ReadonlySet<string> {
  return new Set(graph.groups.filter((each) => each.kind === 'session' && each.status === 'ended').map((each) => each.id));
}

/** The user's explicit collapse choices, by id: `true` collapsed, `false` expanded. */
export type CollapseChoices = ReadonlyMap<string, boolean>;

/**
 * Default collapse state with the user's choices applied. A choice is stored as the state the
 * user picked, not as a flip, so a session that ends after being expanded stays expanded.
 */
export function effectiveCollapsed(graph: TaskGraph, choices: CollapseChoices): ReadonlySet<string> {
  const out = new Set(defaultCollapsed(graph));
  for (const [id, isCollapsed] of choices) {
    if (isCollapsed) out.add(id);
    else out.delete(id);
  }
  return out;
}

// ── visibility ───────────────────────────────────────────────────────────────

export interface VisibleTurn {
  readonly group: GraphGroup;
  readonly collapsed: boolean;
  /** Nodes of the turn not drawn because the turn is collapsed. */
  readonly hidden: number;
  readonly nodes: readonly GraphNode[];
}

export interface VisibleSession {
  readonly group: GraphGroup;
  readonly collapsed: boolean;
  readonly hidden: number;
  readonly main: GraphNode | null;
  /** Spans that hang straight off the session (a session without a trace). */
  readonly loose: readonly GraphNode[];
  readonly turns: readonly VisibleTurn[];
}

export interface VisibleGraph {
  readonly index: GraphIndex;
  readonly sessions: readonly VisibleSession[];
  readonly visible: ReadonlySet<string>;
  /** For a drawn node: how many of its descendants are not drawn. */
  readonly hiddenBelow: ReadonlyMap<string, number>;
  readonly edges: readonly GraphEdge[];
}

export interface CollapseState {
  readonly level: CollapseLevel;
  readonly collapsed: ReadonlySet<string>;
  /**
   * Frames and spans the user expanded by hand: they open even where the level would fold them,
   * so a frame's Expand button always does what it says.
   */
  readonly expanded?: ReadonlySet<string>;
}

/** The ids the user explicitly expanded, from their collapse choices. */
export function explicitlyExpanded(choices: CollapseChoices): ReadonlySet<string> {
  const out = new Set<string>();
  for (const [id, isCollapsed] of choices) if (!isCollapsed) out.add(id);
  return out;
}

function bySessionStart(a: GraphGroup, b: GraphGroup): number {
  const sa = a.started_at ?? a.at ?? 0;
  const sb = b.started_at ?? b.at ?? 0;
  if (sa !== sb) return sb - sa;
  return a.id < b.id ? -1 : a.id > b.id ? 1 : 0;
}

function byTurnTime(a: GraphGroup, b: GraphGroup): number {
  const sa = a.at ?? a.started_at ?? 0;
  const sb = b.at ?? b.started_at ?? 0;
  if (sa !== sb) return sa - sb;
  return a.id < b.id ? -1 : a.id > b.id ? 1 : 0;
}

export function visibleGraph(graph: TaskGraph, state: CollapseState, index: GraphIndex = indexGraph(graph)): VisibleGraph {
  const { level, collapsed } = state;
  const expanded = state.expanded ?? new Set<string>();
  const visible = new Set<string>();
  const nodesByGroup = new Map<string, GraphNode[]>();
  for (const node of graph.nodes) {
    const list = nodesByGroup.get(node.group) ?? [];
    list.push(node);
    nodesByGroup.set(node.group, list);
  }
  const mainIds = new Set(graph.nodes.filter((each) => each.kind === 'main').map((each) => each.id));

  // A span is drawn when no ancestor span is collapsed and, at the agents level, it hangs off main.
  const spanShown = (node: GraphNode): boolean => {
    const chain = ancestors(index, node.id);
    if (level === 'agents' && node.kind !== 'main') {
      // Below the top level only under spans the user opened by hand.
      if (chain.some((id) => !mainIds.has(id) && !expanded.has(id))) return false;
    }
    return !chain.some((id) => !mainIds.has(id) && collapsed.has(id));
  };

  const turnsBySession = new Map<string, GraphGroup[]>();
  for (const group of graph.groups) {
    if (group.kind !== 'turn' || group.parent === null) continue;
    const list = turnsBySession.get(group.parent) ?? [];
    list.push(group);
    turnsBySession.set(group.parent, list);
  }

  const sessions: VisibleSession[] = [];
  for (const group of graph.groups.filter((each) => each.kind === 'session').sort(bySessionStart)) {
    const sessionNodes = nodesByGroup.get(group.id) ?? [];
    const turnGroups = [...(turnsBySession.get(group.id) ?? [])].sort(byTurnTime);
    const sessionCollapsed = (level === 'sessions' && !expanded.has(group.id)) || collapsed.has(group.id);
    if (sessionCollapsed) {
      const total = sessionNodes.length + turnGroups.reduce((sum, turn) => sum + (nodesByGroup.get(turn.id)?.length ?? 0), 0);
      sessions.push({ group, collapsed: true, hidden: total, main: null, loose: [], turns: [] });
      continue;
    }
    const main = sessionNodes.find((each) => each.kind === 'main') ?? null;
    if (main !== null) visible.add(main.id);
    const loose = sessionNodes.filter((each) => each.kind !== 'main' && spanShown(each)).sort(byStart);
    for (const each of loose) visible.add(each.id);
    const turns: VisibleTurn[] = turnGroups.map((turn) => {
      const inTurn = nodesByGroup.get(turn.id) ?? [];
      const turnCollapsed = ((level === 'sessions' || level === 'turns') && !expanded.has(turn.id)) || collapsed.has(turn.id);
      if (turnCollapsed) return { group: turn, collapsed: true, hidden: inTurn.length, nodes: [] };
      const shown = inTurn.filter(spanShown).sort(byStart);
      for (const each of shown) visible.add(each.id);
      return { group: turn, collapsed: false, hidden: 0, nodes: shown };
    });
    sessions.push({ group, collapsed: false, hidden: 0, main, loose, turns });
  }

  const hiddenBelow = new Map<string, number>();
  for (const id of visible) {
    const below = descendants(index, id).filter((each) => !visible.has(each)).length;
    if (below > 0) hiddenBelow.set(id, below);
  }
  const edges = graph.edges.filter((each) => visible.has(each.from) && visible.has(each.to));
  return { index, sessions, visible, hiddenBelow, edges };
}

// ── layout ───────────────────────────────────────────────────────────────────

export type LayoutKind = 'session' | 'turn' | 'node';

export interface LayoutBox {
  readonly id: string;
  readonly kind: LayoutKind;
  readonly parent: string | null;
  readonly x: number;
  readonly y: number;
  readonly width: number;
  readonly height: number;
  readonly collapsed: boolean;
}

export interface CanvasLayout {
  readonly view: VisibleGraph;
  /** Parents always before their children, as React Flow requires. */
  readonly boxes: readonly LayoutBox[];
  readonly width: number;
  readonly height: number;
}

interface Forest {
  readonly positions: ReadonlyMap<string, XY>;
  readonly width: number;
  readonly height: number;
}

/** A tidy tree per root, roots side by side; positions relative to the forest's top-left. */
function layoutForest(roots: readonly string[], kids: (id: string) => readonly string[]): Forest {
  const widths = new Map<string, number>();
  const widthOf = (id: string, seen: Set<string>): number => {
    const known = widths.get(id);
    if (known !== undefined) return known;
    seen.add(id);
    const children = kids(id).filter((each) => !seen.has(each));
    const span = children.reduce((sum, each) => sum + widthOf(each, seen), 0) + GAP_X * Math.max(0, children.length - 1);
    const width = Math.max(NODE_WIDTH, span);
    widths.set(id, width);
    return width;
  };
  const positions = new Map<string, XY>();
  let depthMax = -1;
  const place = (id: string, left: number, depth: number) => {
    if (positions.has(id)) return;
    const width = widths.get(id) ?? NODE_WIDTH;
    positions.set(id, { x: left + (width - NODE_WIDTH) / 2, y: depth * (NODE_HEIGHT + GAP_Y) });
    depthMax = Math.max(depthMax, depth);
    const children = kids(id).filter((each) => widths.has(each) && !positions.has(each));
    const span = children.reduce((sum, each) => sum + (widths.get(each) ?? NODE_WIDTH), 0) + GAP_X * Math.max(0, children.length - 1);
    let x = left + (width - span) / 2;
    for (const child of children) {
      place(child, x, depth + 1);
      x += (widths.get(child) ?? NODE_WIDTH) + GAP_X;
    }
  };
  let left = 0;
  for (const root of roots) {
    if (positions.has(root)) continue;
    const width = widthOf(root, new Set());
    place(root, left, 0);
    left += width + GAP_X;
  }
  const width = roots.length === 0 ? 0 : left - GAP_X;
  const height = depthMax < 0 ? 0 : (depthMax + 1) * NODE_HEIGHT + depthMax * GAP_Y;
  return { positions, width, height };
}

/** The forest of `nodes`: roots are the ones whose spawn parent is not among them. */
function forestOf(nodes: readonly GraphNode[], index: GraphIndex): Forest {
  const members = new Set(nodes.map((each) => each.id));
  const roots = nodes.filter((each) => !members.has(index.parent.get(each.id) ?? '')).map((each) => each.id);
  return layoutForest(roots, (id) => (index.children.get(id) ?? []).filter((each) => members.has(each)));
}

function overridden(overrides: Overrides, id: string, auto: XY, min: XY): XY {
  const own = overrides[id];
  if (own === undefined || !Number.isFinite(own.x) || !Number.isFinite(own.y)) return auto;
  return { x: Math.max(min.x, own.x), y: Math.max(min.y, own.y) };
}

/**
 * Where everything goes. `overrides` (a dragged node's last position, relative to its frame, or a
 * dragged session frame's absolute one) win over the computed position; a frame grows to hold a
 * child dragged past its edge. Turn frames are not draggable, so an override for one is ignored.
 */
export function layoutGraph(graph: TaskGraph, state: CollapseState, overrides: Overrides = {}): CanvasLayout {
  const view = visibleGraph(graph, state);
  const boxes: LayoutBox[] = [];
  let cursorX = 0;
  let width = 0;
  let height = 0;

  for (const session of view.sessions) {
    const sessionId = session.group.id;
    if (session.collapsed) {
      const at = overridden(overrides, sessionId, { x: cursorX, y: 0 }, { x: Number.NEGATIVE_INFINITY, y: Number.NEGATIVE_INFINITY });
      boxes.push({ id: sessionId, kind: 'session', parent: null, ...at, width: COLLAPSED_SESSION_WIDTH, height: COLLAPSED_SESSION_HEIGHT, collapsed: true });
      cursorX += COLLAPSED_SESSION_WIDTH + SESSION_GAP;
      width = Math.max(width, at.x + COLLAPSED_SESSION_WIDTH);
      height = Math.max(height, at.y + COLLAPSED_SESSION_HEIGHT);
      continue;
    }

    const looseForest = forestOf(session.loose, view.index);
    const turnPlans = session.turns.map((turn) => {
      const forest = turn.collapsed ? null : forestOf(turn.nodes, view.index);
      const autoW = forest === null ? NODE_WIDTH + 2 * FRAME_PAD : forest.width + 2 * FRAME_PAD;
      let needW = autoW;
      let needH = forest === null ? COLLAPSED_TURN_HEIGHT : TURN_HEADER + forest.height + FRAME_PAD;
      for (const node of turn.nodes) {
        const own = overrides[node.id];
        if (own === undefined || !Number.isFinite(own.x) || !Number.isFinite(own.y)) continue;
        needW = Math.max(needW, Math.max(0, own.x) + NODE_WIDTH + FRAME_PAD);
        needH = Math.max(needH, Math.max(TURN_HEADER, own.y) + NODE_HEIGHT + FRAME_PAD);
      }
      return { turn, forest, autoW, needW, needH };
    });
    // Automatic positions are centred on the automatic width, so a dragged node that widens a
    // frame never moves its neighbours; the frames themselves grow to the widest need.
    const contentW = Math.max(
      NODE_WIDTH,
      looseForest.width,
      ...turnPlans.map((each) => each.autoW - 2 * FRAME_PAD),
      COLLAPSED_SESSION_WIDTH - 2 * FRAME_PAD,
    );
    const frameW = Math.max(contentW, ...turnPlans.map((each) => each.needW - 2 * FRAME_PAD));
    const innerMin = { x: 0, y: SESSION_HEADER };
    const children: LayoutBox[] = [];
    let cursorY = SESSION_HEADER;
    let right = FRAME_PAD + contentW;
    let bottom = SESSION_HEADER;

    if (session.main !== null) {
      const at = overridden(overrides, session.main.id, { x: FRAME_PAD + (contentW - NODE_WIDTH) / 2, y: cursorY }, innerMin);
      children.push({ id: session.main.id, kind: 'node', parent: sessionId, ...at, width: NODE_WIDTH, height: NODE_HEIGHT, collapsed: false });
      right = Math.max(right, at.x + NODE_WIDTH);
      bottom = Math.max(bottom, at.y + NODE_HEIGHT);
      cursorY += NODE_HEIGHT + GAP_Y;
    }

    if (session.loose.length > 0) {
      const left = FRAME_PAD + (contentW - looseForest.width) / 2;
      for (const node of session.loose) {
        const auto = looseForest.positions.get(node.id) ?? { x: 0, y: 0 };
        const at = overridden(overrides, node.id, { x: left + auto.x, y: cursorY + auto.y }, innerMin);
        children.push({ id: node.id, kind: 'node', parent: sessionId, ...at, width: NODE_WIDTH, height: NODE_HEIGHT, collapsed: view.hiddenBelow.has(node.id) });
        right = Math.max(right, at.x + NODE_WIDTH);
        bottom = Math.max(bottom, at.y + NODE_HEIGHT);
      }
      cursorY += looseForest.height + GAP_Y;
    }

    for (const plan of turnPlans) {
      const turnW = frameW + 2 * FRAME_PAD;
      const turnH = plan.needH;
      children.push({ id: plan.turn.group.id, kind: 'turn', parent: sessionId, x: FRAME_PAD, y: cursorY, width: turnW, height: turnH, collapsed: plan.turn.collapsed });
      if (plan.forest !== null) {
        const left = FRAME_PAD + (contentW - plan.forest.width) / 2;
        for (const node of plan.turn.nodes) {
          const auto = plan.forest.positions.get(node.id) ?? { x: 0, y: 0 };
          const at = overridden(overrides, node.id, { x: left + auto.x, y: TURN_HEADER + auto.y }, { x: 0, y: TURN_HEADER });
          children.push({ id: node.id, kind: 'node', parent: plan.turn.group.id, ...at, width: NODE_WIDTH, height: NODE_HEIGHT, collapsed: view.hiddenBelow.has(node.id) });
        }
      }
      right = Math.max(right, FRAME_PAD + turnW);
      bottom = Math.max(bottom, cursorY + turnH);
      cursorY += turnH + TURN_GAP;
    }

    const sessionW = right + FRAME_PAD;
    const sessionH = bottom + FRAME_PAD;
    const at = overridden(overrides, sessionId, { x: cursorX, y: 0 }, { x: Number.NEGATIVE_INFINITY, y: Number.NEGATIVE_INFINITY });
    boxes.push({ id: sessionId, kind: 'session', parent: null, ...at, width: sessionW, height: sessionH, collapsed: false });
    boxes.push(...children);
    cursorX += sessionW + SESSION_GAP;
    width = Math.max(width, at.x + sessionW);
    height = Math.max(height, at.y + sessionH);
  }
  return { view, boxes, width, height };
}

// ── focus ────────────────────────────────────────────────────────────────────

/** The node, its spawn ancestors and its spawn descendants. Empty for an unknown id. */
export function focusSet(graph: TaskGraph, nodeId: string, index: GraphIndex = indexGraph(graph)): ReadonlySet<string> {
  if (!index.nodes.has(nodeId)) return new Set();
  return new Set([nodeId, ...ancestors(index, nodeId), ...descendants(index, nodeId)]);
}

// ── tones ────────────────────────────────────────────────────────────────────

export type StatusTone = 'running' | 'idle' | 'completed' | 'failed' | 'interrupted' | 'unknown';

/** The status as a tone and the word that always goes with it: never colour alone. */
export function statusTone(status: GraphNodeStatus | null): { readonly tone: StatusTone; readonly label: string } {
  switch (status) {
    case 'running':
      return { tone: 'running', label: 'Running' };
    case 'idle':
      return { tone: 'idle', label: 'Idle' };
    case 'completed':
      return { tone: 'completed', label: 'Completed' };
    case 'failed':
      return { tone: 'failed', label: 'Failed' };
    case 'interrupted':
      return { tone: 'interrupted', label: 'Interrupted' };
    default:
      return { tone: 'unknown', label: 'Status unknown' };
  }
}

export type RoleFamily = 'orchestration' | 'planning' | 'implementation' | 'review-qa' | 'builtin';

export const ROLE_FAMILY_LABEL: Readonly<Record<RoleFamily, string>> = {
  orchestration: 'Orchestration',
  planning: 'Planning',
  implementation: 'Implementation',
  'review-qa': 'Review and QA',
  builtin: 'Built-in',
};

const ORCHESTRATION = new Set(['orchestrator']);
const PLANNING = new Set(['product-analyst', 'software-architect', 'ui-ux-designer', 'setup-assistant', 'plan']);
const REVIEW_QA = new Set([
  'code-reviewer',
  'backend-reviewer',
  'frontend-reviewer',
  'qa-specialist',
  'security-specialist',
  'backend-test-specialist',
  'frontend-test-specialist',
]);
const IMPLEMENTATION = new Set([
  'backend-developer',
  'frontend-developer',
  'mobile-developer',
  'database-specialist',
  'devops-specialist',
  'technical-writer',
  'seo-specialist',
]);

/**
 * The family an agent's role belongs to, for the node's background tint. A namespaced name
 * (`devteam:backend-developer`) is matched on its last segment; an unknown named agent reads as
 * implementation, a span with no agent name as built-in.
 */
export function roleFamily(agent: string | null, kind: GraphNodeKind = 'agent'): RoleFamily {
  if (kind === 'main') return 'orchestration';
  if (kind === 'review') return 'review-qa';
  if (kind === 'builtin') return 'builtin';
  if (agent === null || agent.trim() === '') return 'builtin';
  const name = agent.trim().toLowerCase().split(':').pop() ?? '';
  if (ORCHESTRATION.has(name)) return 'orchestration';
  if (PLANNING.has(name)) return 'planning';
  if (REVIEW_QA.has(name) || name.endsWith('-reviewer')) return 'review-qa';
  if (IMPLEMENTATION.has(name) || name.endsWith('-developer') || name.endsWith('-specialist')) return 'implementation';
  if (name === 'explore' || name === 'general-purpose') return 'builtin';
  return 'implementation';
}

export type HeatLevel = 0 | 1 | 2 | 3 | 4 | 'unknown';

/**
 * Heatmap emphasis for a token figure against the busiest one in view. `null` tokens (usage not
 * reported) are `unknown`, never the lowest level.
 */
export function heatTone(tokens: number | null, max: number): HeatLevel {
  if (tokens === null || !Number.isFinite(tokens)) return 'unknown';
  if (tokens <= 0 || !(max > 0)) return 0;
  const ratio = Math.min(1, tokens / max);
  return Math.max(1, Math.min(4, Math.ceil(ratio * 4))) as 1 | 2 | 3 | 4;
}

/** The figure a heatmap reads for a node: its subtree tokens, or `null` when usage is unknown. */
export function heatTokens(node: GraphNode): number | null {
  return node.usage_complete ? node.subtree_tokens : null;
}

// ── text ─────────────────────────────────────────────────────────────────────

/** `950`, `12.3k`, `1.2M`. */
export function formatTokens(tokens: number): string {
  const n = Math.max(0, Math.round(tokens));
  if (n < 1000) return String(n);
  if (n < 1_000_000) return `${trimZero((n / 1000).toFixed(n < 10_000 ? 1 : 0))}k`;
  return `${trimZero((n / 1_000_000).toFixed(1))}M`;
}

function trimZero(text: string): string {
  return text.endsWith('.0') ? text.slice(0, -2) : text;
}

/**
 * A node's tokens, `n/a` when usage is unknown, never a misleading 0. The main node does no
 * reported work of its own, so it shows the session's total (its subtree) instead.
 */
export function nodeTokensLabel(node: Pick<GraphNode, 'kind' | 'tokens' | 'subtree_tokens' | 'usage_complete'>): string {
  if (!node.usage_complete) return 'n/a';
  return formatTokens(node.kind === 'main' ? node.subtree_tokens : node.tokens);
}

/** A frame total: marked incomplete when any usage in it is unknown; `n/a` when nothing is known. */
export function frameTokensLabel(group: Pick<GraphGroup, 'tokens' | 'usage_complete'>): string {
  if (group.usage_complete) return `${formatTokens(group.tokens)} tokens`;
  return group.tokens > 0 ? `${formatTokens(group.tokens)}+ tokens (incomplete)` : 'tokens n/a';
}

/** The name an agent node is called by. */
export function agentLabel(node: GraphNode): string {
  if (node.kind === 'main') return node.label ?? (node.persona === 'orchestrator' ? 'Orchestrator' : 'Main session');
  return node.agent ?? node.label ?? (node.kind === 'builtin' ? 'Built-in agent' : 'Agent');
}

/** The one-line name of a node in the outline and the detail panel. */
export function nodeTitle(node: GraphNode): string {
  if (node.kind === 'main') return agentLabel(node);
  const agent = agentLabel(node);
  return node.description !== null && node.description !== '' ? `${agent}: ${node.description}` : agent;
}

/** Elapsed seconds: the recorded duration, or the time since it started while it runs. */
export function elapsedSeconds(node: GraphNode, now: number): number | null {
  if (node.status === 'running' && node.started_at !== null) return Math.max(0, now - node.started_at);
  if (node.duration_s > 0) return node.duration_s;
  if (node.started_at !== null && node.ended_at !== null) return Math.max(0, node.ended_at - node.started_at);
  return null;
}

/** Why a session is drawn without its trace: none was found, or one was found and could not be read. */
export type TraceProblem = 'missing' | 'unreadable';

/** The sessions the CLI drew without a trace, from its `no_trace:<sid>` and `bad_trace:<sid>` notices. */
export function traceProblems(notices: readonly string[]): ReadonlyMap<string, TraceProblem> {
  const out = new Map<string, TraceProblem>();
  for (const notice of notices) {
    if (notice.startsWith('bad_trace:')) out.set(notice.slice('bad_trace:'.length), 'unreadable');
    else if (notice.startsWith('no_trace:') && !out.has(notice.slice('no_trace:'.length))) out.set(notice.slice('no_trace:'.length), 'missing');
  }
  return out;
}

// ── reveal ───────────────────────────────────────────────────────────────────

const LEVEL_RANK: Readonly<Record<CollapseLevel, number>> = { sessions: 0, turns: 1, agents: 2, all: 3 };

function atLeast(level: CollapseLevel, floor: CollapseLevel): CollapseLevel {
  return LEVEL_RANK[level] >= LEVEL_RANK[floor] ? level : floor;
}

export interface RevealPlan {
  /** The collapse level that draws the target. */
  readonly level: CollapseLevel;
  /** Frames and spans to expand so the target is drawn. */
  readonly expand: readonly string[];
}

/**
 * What to open so `id` (a node, a turn or a session) is on the canvas: its session and turn
 * frames, every spawn ancestor span, and the lowest collapse level at or above `level` that
 * draws it. `null` for an id the graph does not have.
 */
export function revealPlan(index: GraphIndex, id: string, level: CollapseLevel): RevealPlan | null {
  const node = index.nodes.get(id);
  const group = index.groups.get(node === undefined ? id : node.group);
  if (group === undefined) return null;
  const session = sessionOf(index, group.id);
  if (node === undefined) {
    if (group.kind === 'session') return { level, expand: [] };
    return { level: atLeast(level, 'turns'), expand: session === null ? [] : [session] };
  }
  const expand: string[] = [];
  if (session !== null) expand.push(session);
  if (group.kind === 'turn') expand.push(group.id);
  const chain = ancestors(index, id);
  for (const each of chain) if (index.nodes.get(each)?.kind !== 'main') expand.push(each);
  let next = atLeast(level, 'turns');
  if (group.kind === 'turn') next = atLeast(next, 'agents');
  const parent = chain[0];
  const topLevel = node.kind === 'main' || parent === undefined || index.nodes.get(parent)?.kind === 'main';
  if (next === 'agents' && !topLevel) next = 'all';
  return { level: next, expand };
}

// ── outline ──────────────────────────────────────────────────────────────────

export interface OutlineItem {
  readonly id: string;
  readonly kind: LayoutKind;
  readonly label: string;
  readonly children: readonly OutlineItem[];
}

/**
 * The whole hierarchy as a tree, regardless of collapse level: session → main node, then the
 * session's loose spans and its turns, each holding its span tree.
 */
export function outlineTree(graph: TaskGraph, index: GraphIndex = indexGraph(graph)): readonly OutlineItem[] {
  const view = visibleGraph(graph, { level: 'all', collapsed: new Set() }, index);
  const spanItems = (nodes: readonly GraphNode[]): OutlineItem[] => {
    const members = new Set(nodes.map((each) => each.id));
    const build = (id: string, seen: Set<string>): OutlineItem => {
      seen.add(id);
      const node = index.nodes.get(id)!;
      const kids = (index.children.get(id) ?? []).filter((each) => members.has(each) && !seen.has(each));
      return { id, kind: 'node', label: nodeTitle(node), children: kids.map((each) => build(each, seen)) };
    };
    const seen = new Set<string>();
    return nodes.filter((each) => !members.has(index.parent.get(each.id) ?? '')).map((each) => build(each.id, seen));
  };
  return view.sessions.map((session) => {
    const children: OutlineItem[] = [];
    if (session.main !== null) children.push({ id: session.main.id, kind: 'node', label: nodeTitle(session.main), children: [] });
    children.push(...spanItems(session.loose));
    for (const turn of session.turns) {
      children.push({ id: turn.group.id, kind: 'turn', label: turn.group.label, children: spanItems(turn.nodes) });
    }
    return { id: session.group.id, kind: 'session', label: session.group.label, children };
  });
}
