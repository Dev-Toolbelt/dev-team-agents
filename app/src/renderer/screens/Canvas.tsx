import { useCallback, useEffect, useId, useMemo, useRef, useState, type ReactNode } from 'react';
import {
  Background,
  MiniMap,
  Panel,
  ReactFlow,
  ReactFlowProvider,
  applyNodeChanges,
  useReactFlow,
  type Edge,
  type NodeChange,
  type NodeTypes,
} from '@xyflow/react';
import { CircleAlert, Coins, Cpu, X } from 'lucide-react';

import '../canvas.css';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Empty } from '../Problem.js';
import { formatDateTime, formatDuration, periodCutoff, type Period } from '../boardModel.js';
import {
  ROLE_FAMILY_LABEL,
  agentLabel,
  effectiveCollapsed,
  explicitlyExpanded,
  elapsedSeconds,
  filterGraphByPeriod,
  focusSet,
  heatTokens,
  heatTone,
  layoutGraph,
  nodeDescription,
  nodeTokensLabel,
  outlineTree,
  revealPlan,
  roleFamily,
  sessionIdOf,
  sessionOf,
  statusTone,
  formatTokens,
  traceProblems,
  type CollapseChoices,
  type CollapseLevel,
  type Overrides,
} from '../canvasModel.js';
import { clearPositions, loadPositions, savePosition } from '../canvasPositions.js';
import { CanvasGroup, type CanvasFlowGroup } from './CanvasGroup.js';
import { CanvasClock, CanvasNode, STATUS_ICON, STATUS_TEXT_CLASS, WorktreeChip, type CanvasFlowNode } from './CanvasNode.js';
import { CanvasOutline } from './CanvasOutline.js';
import { CanvasToolbar } from './CanvasToolbar.js';
import { PrBadge } from './PrBadge.js';
import type { BoardProject, GraphNode, TaskGraph, TaskGraphResult } from '../../shared/api.js';

const NODE_TYPES: NodeTypes = { canvasNode: CanvasNode, canvasGroup: CanvasGroup };

type FlowNode = CanvasFlowNode | CanvasFlowGroup;

/** Where a board card is, for "Show on board". */
export interface BoardCardRef {
  readonly sessionId: string;
  readonly taskKey: string;
}

/** Epoch seconds, re-sampled every `intervalSeconds` while `enabled`. */
function useClock(clock: () => number, intervalSeconds: number, enabled: boolean): number {
  const sample = () => Math.floor(clock() / 1000);
  const [now, setNow] = useState(sample);
  useEffect(() => {
    if (!enabled) return;
    setNow(Math.floor(clock() / 1000));
    const timer = setInterval(() => setNow(Math.floor(clock() / 1000)), intervalSeconds * 1000);
    return () => clearInterval(timer);
  }, [clock, intervalSeconds, enabled]);
  return now;
}

/**
 * The live graph of one project, read while `active` (ADR-0063): subscribe first, then ask for
 * the latest result; a push that lands before the first answer is newer than it. The last
 * result stays on screen while the canvas is hidden, and nothing is polled then.
 */
function useTaskGraph(projectId: string, active: boolean): TaskGraphResult | null {
  const [result, setResult] = useState<TaskGraphResult | null>(null);
  useEffect(() => {
    if (!active) return;
    let live = true;
    let pushed = false;
    const unsubscribe = window.devteam.onTaskGraph(projectId, (next) => {
      if (!live) return;
      pushed = true;
      setResult(next);
    });
    window.devteam.taskGraph(projectId).then(
      (initial) => {
        if (live && !pushed) setResult(initial);
      },
      (error: unknown) => {
        if (live && !pushed) setResult({ ok: false, reason: 'error', detail: error instanceof Error ? error.message : String(error) });
      },
    );
    return () => {
      live = false;
      unsubscribe();
    };
  }, [projectId, active]);
  return result;
}

/**
 * The canvas next to a project's kanban: who spawned what, read-only. Data comes from the CLI's
 * `tasks graph`; layout and every derived figure come from `canvasModel`.
 */
export function Canvas({
  project,
  period,
  active,
  clock = Date.now,
  onShowOnBoard,
}: {
  project: BoardProject;
  period: Period;
  active: boolean;
  clock?: () => number;
  onShowOnBoard?: (card: BoardCardRef) => void;
}) {
  const result = useTaskGraph(project.project_id, active);
  if (result === null) return <Empty>Loading the canvas…</Empty>;
  if (!result.ok) return <GraphProblem result={result} />;
  return (
    <ReactFlowProvider>
      <CanvasBoard
        graph={result.graph}
        projectId={project.project_id}
        period={period}
        active={active}
        clock={clock}
        onShowOnBoard={onShowOnBoard}
      />
    </ReactFlowProvider>
  );
}

function GraphProblem({ result }: { result: Extract<TaskGraphResult, { ok: false }> }) {
  if (result.reason === 'unsupported') {
    return (
      <Alert>
        <CircleAlert />
        <AlertTitle>The installed devteam CLI does not support the canvas</AlertTitle>
        <AlertDescription>
          Update the CLI (run <code className="font-mono">devteam update</code>) to see the canvas. The task board keeps working meanwhile.
        </AlertDescription>
      </Alert>
    );
  }
  return (
    <Alert variant="destructive">
      <CircleAlert />
      <AlertTitle>{result.reason === 'unavailable' ? 'The canvas is not available' : 'The canvas could not be loaded'}</AlertTitle>
      <AlertDescription>{result.detail ?? 'The task graph could not be read.'}</AlertDescription>
    </Alert>
  );
}

function CanvasBoard({
  graph: fullGraph,
  projectId,
  period,
  active,
  clock,
  onShowOnBoard,
}: {
  graph: TaskGraph;
  projectId: string;
  period: Period;
  active: boolean;
  clock: () => number;
  onShowOnBoard: ((card: BoardCardRef) => void) | undefined;
}) {
  const flow = useReactFlow();
  const coarseNow = Math.max(useClock(clock, 60, active), fullGraph.as_of);
  const cutoff = periodCutoff(period, coarseNow);
  const graph = useMemo(() => filterGraphByPeriod(fullGraph, cutoff), [fullGraph, cutoff]);
  const anyRunning = useMemo(() => graph.nodes.some((each) => each.status === 'running'), [graph]);
  const tick = Math.max(useClock(clock, 1, active && anyRunning), fullGraph.as_of);

  const [level, setLevel] = useState<CollapseLevel>('all');
  const [choices, setChoices] = useState<CollapseChoices>(() => new Map());
  const [overrides, setOverrides] = useState<Overrides>(() => loadPositions(projectId));
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [focusOn, setFocusOn] = useState(false);
  const [heatOn, setHeatOn] = useState(false);
  const [outlineOn, setOutlineOn] = useState(true);

  const collapsed = useMemo(() => effectiveCollapsed(graph, choices), [graph, choices]);
  const expanded = useMemo(() => explicitlyExpanded(choices), [choices]);
  const layout = useMemo(() => layoutGraph(graph, { level, collapsed, expanded }, overrides), [graph, level, collapsed, expanded, overrides]);
  const { view } = layout;
  const traceProblem = useMemo(() => traceProblems(graph.notices), [graph.notices]);
  const selectedNode = selectedId === null ? undefined : view.index.nodes.get(selectedId);
  const focus = useMemo(
    () => (focusOn && selectedNode !== undefined ? focusSet(graph, selectedNode.id, view.index) : null),
    [focusOn, selectedNode, graph, view.index],
  );
  const maxHeat = useMemo(() => {
    let max = 0;
    for (const id of view.visible) {
      const node = view.index.nodes.get(id);
      if (node !== undefined && node.kind !== 'main' && node.usage_complete) max = Math.max(max, node.subtree_tokens);
    }
    return max;
  }, [view]);

  // A toggle records the opposite of what is on screen, so it also opens what the level folded.
  const toggle = useCallback((id: string, shownCollapsed: boolean) => {
    setChoices((was) => new Map(was).set(id, !shownCollapsed));
  }, []);

  // A selection whose node left the graph (period, live update) closes its panel and its focus.
  useEffect(() => {
    if (selectedId !== null && !view.index.nodes.has(selectedId)) {
      setSelectedId(null);
      setFocusOn(false);
    }
  }, [selectedId, view.index]);

  const flowNodes = useMemo<FlowNode[]>(() => {
    const groupById = new Map(graph.groups.map((each) => [each.id, each]));
    const sessionById = new Map(view.sessions.map((each) => [each.group.id, each]));
    const turnHidden = new Map(view.sessions.flatMap((each) => each.turns.map((turn) => [turn.group.id, turn.hidden] as const)));
    return layout.boxes.map((box): FlowNode => {
      const base = {
        id: box.id,
        position: { x: box.x, y: box.y },
        width: box.width,
        height: box.height,
        ...(box.parent !== null ? { parentId: box.parent } : {}),
      };
      if (box.kind !== 'node') {
        const group = groupById.get(box.id)!;
        const sessionGroupId = box.kind === 'session' ? box.id : (group.parent ?? box.id);
        const hidden = box.kind === 'session' ? (sessionById.get(box.id)?.hidden ?? 0) : (turnHidden.get(box.id) ?? 0);
        return {
          ...base,
          type: 'canvasGroup',
          draggable: box.kind === 'session',
          selectable: false,
          focusable: false,
          zIndex: box.kind === 'session' ? 0 : 1,
          ariaLabel: `${box.kind === 'session' ? 'Session' : 'Turn'} ${group.label}`,
          data: {
            group,
            projectId,
            // The CLI's own field; the id grammar only for an older CLI that predates it.
            sessionId: group.session_id ?? sessionIdOf(sessionGroupId),
            collapsed: box.collapsed,
            hidden,
            traceProblem: box.kind === 'session' ? (traceProblem.get(group.session_id ?? sessionIdOf(box.id)) ?? null) : null,
            dimmed: focus !== null,
            onToggle: toggle,
          },
        };
      }
      const node = view.index.nodes.get(box.id)!;
      const sessionGroup = sessionOf(view.index, node.id) ?? '';
      const status = statusTone(node.status);
      return {
        ...base,
        type: 'canvasNode',
        selected: node.id === selectedId,
        ariaLabel: `${agentLabel(node)}, ${status.label}${node.description !== null ? `: ${node.description}` : ''}`,
        data: {
          node,
          projectId,
          sessionId: node.session_id ?? sessionIdOf(sessionGroup),
          heat: heatOn && node.kind !== 'main' ? heatTone(heatTokens(node), maxHeat) : null,
          dimmed: focus !== null && !focus.has(node.id),
          hiddenBelow: view.hiddenBelow.get(node.id) ?? 0,
          collapsible: node.kind !== 'main' && (view.index.children.get(node.id)?.length ?? 0) > 0,
          // Folded by hand, or by the level: one of its own spawns is hidden (a deeper fold elsewhere
          // in its subtree does not make this node read as collapsed).
          collapsed:
            collapsed.has(node.id) || (view.index.children.get(node.id) ?? []).some((child) => !view.visible.has(child)),
          spawned: view.index.children.get(node.id)?.length ?? 0,
          onToggle: toggle,
        },
      };
    });
  }, [layout, view, graph.groups, projectId, traceProblem, focus, toggle, selectedId, heatOn, maxHeat, collapsed]);

  const flowEdges = useMemo<Edge[]>(
    () =>
      view.edges.map((edge) => {
        const target = view.index.nodes.get(edge.to);
        const dimmed = focus !== null && !(focus.has(edge.from) && focus.has(edge.to));
        const classes = [target?.background === true ? 'canvas-edge-background' : '', dimmed ? 'canvas-edge-dimmed' : ''].filter(Boolean);
        return {
          id: edge.id,
          source: edge.from,
          target: edge.to,
          type: 'smoothstep',
          focusable: false,
          selectable: false,
          ...(classes.length > 0 ? { className: classes.join(' ') } : {}),
        };
      }),
    [view, focus],
  );

  // React Flow moves nodes through `onNodesChange` while dragging; the layout is re-adopted on
  // every change, except mid-drag, when a live update must not yank the node from the pointer.
  // A move that settles (`dragging: false`) is saved: the end of a pointer drag and an arrow-key
  // move alike, so both take the same path into the layout.
  const [nodes, setNodes] = useState<FlowNode[]>(flowNodes);
  const dragging = useRef(false);
  useEffect(() => {
    if (!dragging.current) setNodes(flowNodes);
  }, [flowNodes]);
  const onNodesChange = useCallback(
    (changes: NodeChange<FlowNode>[]) => {
      setNodes((was) => applyNodeChanges(changes, was));
      for (const change of changes) {
        if (change.type === 'select' && change.selected) setSelectedId(change.id);
        if (change.type !== 'position') continue;
        dragging.current = change.dragging === true;
        if (change.dragging === false && change.position !== undefined) {
          setOverrides(savePosition(projectId, change.id, change.position));
        }
      }
    },
    [projectId],
  );

  const fitted = useRef(false);
  useEffect(() => {
    if (fitted.current || flowNodes.length === 0 || !active) return;
    fitted.current = true;
    const frame = requestAnimationFrame(() => void flow.fitView({ padding: 0.1 }));
    return () => cancelAnimationFrame(frame);
  }, [flowNodes.length, active, flow]);

  // Revealing from the outline opens whatever hides the target (its frames, its collapsed
  // ancestors, a level too coarse), selects it, and fits the view once it is drawn.
  const [pendingFit, setPendingFit] = useState<string | null>(null);
  const revealInCanvas = (id: string) => {
    const plan = revealPlan(view.index, id, level);
    if (plan === null) return;
    if (plan.level !== level) setLevel(plan.level);
    if (plan.expand.some((each) => collapsed.has(each))) {
      setChoices((was) => {
        const next = new Map(was);
        for (const each of plan.expand) next.set(each, false);
        return next;
      });
    }
    if (view.index.nodes.has(id)) setSelectedId(id);
    setPendingFit(id);
  };
  useEffect(() => {
    if (pendingFit === null || !nodes.some((each) => each.id === pendingFit)) return;
    const id = pendingFit;
    setPendingFit(null);
    const frame = requestAnimationFrame(() => void flow.fitView({ nodes: [{ id }], padding: 0.6, duration: 200, maxZoom: 1.2 }));
    return () => cancelAnimationFrame(frame);
  }, [pendingFit, nodes, flow]);
  const outline = useMemo(() => outlineTree(graph, view.index), [graph, view.index]);

  const resetLayout = () => {
    clearPositions(projectId);
    setOverrides({});
  };
  const hasOverrides = Object.keys(overrides).length > 0;
  const fullScreen = useFullScreen(() => void flow.fitView({ padding: 0.1, duration: 200 }));
  // Nothing left to show takes the canvas, and its full screen, away: it comes back windowed.
  const empty = graph.groups.length === 0;
  const leaveFullScreen = fullScreen.leave;
  useEffect(() => {
    if (empty) leaveFullScreen();
  }, [empty, leaveFullScreen]);

  if (empty) {
    return <Empty>No session of this project has activity in this period.</Empty>;
  }

  return (
    <div className="space-y-3">
      <CanvasNotices graph={fullGraph} />

      <div
        ref={fullScreen.ref}
        data-full-screen={fullScreen.on ? 'overlay' : 'off'}
        {...(fullScreen.on ? { role: 'dialog', 'aria-modal': true, 'aria-label': 'Canvas full screen' } : {})}
        className={`flex min-h-0 gap-3 ${fullScreen.on ? 'fixed inset-0 z-50 bg-background p-3' : 'h-[max(28rem,calc(100vh-17rem))]'}`}
      >
          <div className="min-w-0 flex-1 overflow-hidden rounded-lg border" aria-label="Canvas" role="region">
            <CanvasClock.Provider value={tick}>
              <ReactFlow<FlowNode, Edge>
                className="devteam-canvas"
                nodes={nodes}
                edges={flowEdges}
                nodeTypes={NODE_TYPES}
                onNodesChange={onNodesChange}
                onPaneClick={() => {
                  setSelectedId(null);
                  setFocusOn(false);
                }}
                nodesConnectable={false}
                edgesFocusable={false}
                elementsSelectable
                multiSelectionKeyCode={null}
                selectionKeyCode={null}
                deleteKeyCode={null}
                onlyRenderVisibleElements
                minZoom={0.1}
                maxZoom={2}
                proOptions={{ hideAttribution: true }}
              >
                <Background gap={24} />
                <Panel position="top-left">
                  <CanvasToolbar
                    level={level}
                    onLevel={setLevel}
                    onFitView={() => void flow.fitView({ padding: 0.1, duration: 200 })}
                    onZoomIn={() => void flow.zoomIn({ duration: 150 })}
                    onZoomOut={() => void flow.zoomOut({ duration: 150 })}
                    focusOn={focusOn}
                    focusDisabled={selectedNode === undefined && !focusOn}
                    onFocus={() => setFocusOn((was) => !was)}
                    heatOn={heatOn}
                    onHeat={() => setHeatOn((was) => !was)}
                    outlineOn={outlineOn}
                    onOutline={() => setOutlineOn((was) => !was)}
                    fullScreen={fullScreen.on}
                    onFullScreen={fullScreen.toggle}
                    canReset={hasOverrides}
                    onReset={resetLayout}
                  />
                </Panel>
                <MiniMap
                  pannable
                  zoomable
                  ariaLabel="Mini map"
                  nodeColor={(node) => (node.type === 'canvasGroup' ? 'var(--muted)' : 'var(--muted-foreground)')}
                />
              </ReactFlow>
            </CanvasClock.Provider>
          </div>
          {outlineOn ? (
            <div className="w-72 shrink-0 overflow-auto rounded-lg border bg-card" data-panel="outline">
              <CanvasOutline items={outline} selectedId={selectedId} onSelect={revealInCanvas} />
            </div>
          ) : null}
          {selectedNode !== undefined ? (
            <NodeDetail
              node={selectedNode}
              projectId={projectId}
              sessionId={selectedNode.session_id ?? sessionIdOf(sessionOf(view.index, selectedNode.id) ?? '')}
              now={selectedNode.status === 'running' ? tick : coarseNow}
              onClose={() => {
                setSelectedId(null);
                setFocusOn(false);
              }}
              onShowOnBoard={onShowOnBoard}
            />
          ) : null}
      </div>
    </div>
  );
}

/**
 * Full screen for the canvas and its side panels: an overlay over the whole app window, which
 * Esc or the toolbar button leaves. Not the Fullscreen API — the session refuses every
 * permission (main/security.ts), `fullscreen` included, so a request there changes nothing.
 * `onChange` runs after each switch, so the view can fit the new size.
 */
function useFullScreen(onChange: () => void) {
  const [on, setOn] = useState(false);
  const [element, setElement] = useState<HTMLDivElement | null>(null);
  const onChangeRef = useRef(onChange);
  useEffect(() => {
    onChangeRef.current = onChange;
  });

  useEffect(() => {
    if (!on) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !event.defaultPrevented) setOn(false);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [on]);

  const first = useRef(true);
  useEffect(() => {
    if (first.current) {
      first.current = false;
      return;
    }
    const frame = requestAnimationFrame(() => onChangeRef.current());
    return () => cancelAnimationFrame(frame);
  }, [on]);

  // Modal while on: what the overlay covers leaves the tab order and the accessibility tree.
  // Siblings along the path to <body> go inert; a portal mounted later (a tooltip, the Show
  // menu) is a new child of <body> and stays live, and so do the toasts, which draw above it.
  useEffect(() => {
    if (!on || element === null) return;
    const covered: Element[] = [];
    for (let node: Element = element; node.parentElement !== null; node = node.parentElement) {
      for (const sibling of Array.from(node.parentElement.children)) {
        if (sibling === node || sibling.hasAttribute('inert') || isToaster(sibling)) continue;
        covered.push(sibling);
      }
    }
    for (const each of covered) each.setAttribute('inert', '');
    return () => {
      for (const each of covered) each.removeAttribute('inert');
    };
  }, [on, element]);

  const toggle = useCallback(() => setOn((was) => !was), []);
  const leave = useCallback(() => setOn(false), []);
  return { ref: setElement, on, toggle, leave };
}

/** Sonner's toast region: rendered in place, not portalled, and kept usable over the overlay. */
function isToaster(element: Element): boolean {
  return element.hasAttribute('data-sonner-toaster') || element.querySelector(':scope > [data-sonner-toaster]') !== null;
}

function CanvasNotices({ graph }: { graph: TaskGraph }) {
  const lines: string[] = [];
  if (graph.truncated) lines.push('The graph hit its size limit: some agents are not shown.');
  if (lines.length === 0) return null;
  return (
    <div role="status">
      <ul className="space-y-0.5 text-xs text-muted-foreground">
        {lines.map((line) => (
          <li key={line}>{line}</li>
        ))}
      </ul>
    </div>
  );
}

function DetailRow({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="grid grid-cols-[6.5rem_1fr] gap-2">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="min-w-0 break-words [overflow-wrap:anywhere]">{children}</dd>
    </div>
  );
}

/** Everything about the selected node, with the link back to its board card when it has one. */
function NodeDetail({
  node,
  projectId,
  sessionId,
  now,
  onClose,
  onShowOnBoard,
}: {
  node: GraphNode;
  projectId: string;
  sessionId: string;
  now: number;
  onClose: () => void;
  onShowOnBoard: ((card: BoardCardRef) => void) | undefined;
}) {
  const headingId = useId();
  const agentId = useId();
  const status = statusTone(node.status);
  const StatusIcon = STATUS_ICON[status.tone];
  const elapsed = elapsedSeconds(node, now);
  const agent = agentLabel(node);
  const description = node.kind === 'main' ? null : nodeDescription(node);
  return (
    <aside
      aria-labelledby={description !== null ? agentId : headingId}
      {...(description !== null ? { 'aria-describedby': headingId } : {})}
      className="w-80 shrink-0 space-y-3 overflow-auto rounded-lg border bg-card p-4 text-sm"
      onKeyDown={(event) => {
        if (event.key === 'Escape') {
          event.stopPropagation();
          onClose();
        }
      }}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 space-y-1">
          {description !== null ? (
            <p id={agentId} className="truncate text-xs font-medium text-muted-foreground" title={agent}>
              {agent}
            </p>
          ) : null}
          <p className={`flex items-center gap-1.5 text-xs font-medium ${STATUS_TEXT_CLASS[status.tone]}`}>
            <StatusIcon className={`size-3.5 ${status.tone === 'running' ? 'animate-spin' : ''}`} aria-hidden="true" />
            {status.label}
          </p>
        </div>
        <Button variant="ghost" size="sm" aria-label="Close details" onClick={onClose}>
          <X aria-hidden="true" />
        </Button>
      </div>
      <h4 id={headingId} className="text-base leading-snug font-semibold break-words [overflow-wrap:anywhere]">
        {description ?? agent}
      </h4>
      <dl className="space-y-1.5 text-xs">
        {node.model !== null ? (
          <DetailRow label="Model">
            <Badge variant="outline" className="max-w-full border-info font-mono text-foreground">
              <Cpu aria-hidden="true" />
              <span className="truncate">{node.model}</span>
            </Badge>
          </DetailRow>
        ) : null}
        <DetailRow label="Tokens">
          <Badge variant="secondary" className="tabular-nums">
            <Coins aria-hidden="true" />
            {nodeTokensLabel(node)}
          </Badge>
        </DetailRow>
        {elapsed !== null ? <DetailRow label={status.tone === 'running' ? 'Running for' : 'Took'}>{formatDuration(elapsed)}</DetailRow> : null}
        {node.started_at !== null ? <DetailRow label="Started">{formatDateTime(node.started_at)}</DetailRow> : null}
        {node.ended_at !== null ? <DetailRow label="Finished">{formatDateTime(node.ended_at)}</DetailRow> : null}
        <DetailRow label="Role">{ROLE_FAMILY_LABEL[roleFamily(node.agent, node.kind)]}</DetailRow>
        {node.background ? <DetailRow label="Mode">Background</DetailRow> : null}
        {node.kind !== 'main' ? (
          <DetailRow label="With sub-agents">{node.usage_complete ? formatTokens(node.subtree_tokens) : 'n/a'}</DetailRow>
        ) : null}
        {node.findings !== null ? <DetailRow label="Findings">{node.findings}</DetailRow> : null}
        {node.worktree !== null ? (
          <DetailRow label="Worktree">
            <span className="inline-flex items-center gap-1 font-mono">
              <WorktreeChip path={node.worktree.path} branch={node.worktree.branch} />
              {node.worktree.branch ?? node.worktree.path}
            </span>
          </DetailRow>
        ) : null}
        {node.pr !== null && node.task_key !== null ? (
          <DetailRow label="Pull request">
            <PrBadge
              pr={node.pr}
              request={{ project_id: projectId, session_id: node.record_id ?? sessionId, task_key: node.task_key, link: { type: 'pr', index: 0, expect: String(node.pr.number) } }}
            />
          </DetailRow>
        ) : null}
      </dl>
      {node.last_output !== null && node.last_output !== '' ? (
        <div className="space-y-1">
          <h5 className="text-xs font-medium text-muted-foreground">Last output</h5>
          <p className="rounded-md bg-muted/50 p-2 font-mono text-xs break-words [overflow-wrap:anywhere]">{node.last_output}</p>
        </div>
      ) : null}
      {node.todos.length > 0 ? (
        <div className="space-y-1">
          <h5 className="text-xs font-medium text-muted-foreground">Todos</h5>
          <ul className="space-y-0.5 text-xs">
            {node.todos.map((todo) => (
              <li key={todo.key} className="flex gap-2">
                <span className="shrink-0 text-muted-foreground">{todo.status.replace(/_/g, ' ')}</span>
                <span className="min-w-0 break-words">{todo.content}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {node.task_key !== null && onShowOnBoard !== undefined ? (
        <Button variant="outline" size="sm" onClick={() => onShowOnBoard({ sessionId: node.record_id ?? sessionId, taskKey: node.task_key! })}>
          Show on board
        </Button>
      ) : null}
    </aside>
  );
}
