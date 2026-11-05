import { createContext, memo, useContext, useSyncExternalStore } from 'react';
import { Handle, NodeToolbar, Position, type Node, type NodeProps } from '@xyflow/react';
import { CheckCircle2, ChevronDown, ChevronRight, CircleDashed, CircleSlash, Clock, Coins, FolderGit2, Loader2, PauseCircle, TriangleAlert, XCircle } from 'lucide-react';

import { Hint } from '@/components/ui/tooltip';
import { formatDuration } from '../boardModel.js';
import { canvasActions } from '../canvasActions.js';
import {
  ROLE_FAMILY_LABEL,
  agentLabel,
  elapsedSeconds,
  nodeTokensLabel,
  roleFamily,
  statusTone,
  type HeatLevel,
  type RoleFamily,
  type StatusTone,
} from '../canvasModel.js';
import { PrBadge } from './PrBadge.js';
import type { GraphNode } from '../../shared/api.js';

export type CanvasNodeData = {
  readonly node: GraphNode;
  readonly projectId: string;
  readonly sessionId: string;
  /** `null` while the heatmap is off. */
  readonly heat: HeatLevel | null;
  readonly dimmed: boolean;
  readonly hiddenBelow: number;
  /** The node has spawn children, so it can be collapsed. */
  readonly collapsible: boolean;
  readonly collapsed: boolean;
  /** Spawned agents, shown on the main node. */
  readonly spawned: number;
  readonly onToggle: (id: string, shownCollapsed: boolean) => void;
};

export type CanvasFlowNode = Node<CanvasNodeData, 'canvasNode'>;

/**
 * The canvas clock in epoch seconds. Only a running node's elapsed figure reads it, so a tick
 * re-renders those figures and leaves every other node (and its data) as it was.
 */
export const CanvasClock = createContext(0);

export const STATUS_ICON: Readonly<Record<StatusTone, typeof CheckCircle2>> = {
  running: Loader2,
  idle: PauseCircle,
  completed: CheckCircle2,
  failed: XCircle,
  interrupted: CircleSlash,
  unknown: CircleDashed,
};

export const STATUS_TEXT_CLASS: Readonly<Record<StatusTone, string>> = {
  running: 'text-info',
  idle: 'text-muted-foreground',
  completed: 'text-success',
  failed: 'text-destructive',
  interrupted: 'text-warning',
  unknown: 'text-muted-foreground',
};

const STATUS_BORDER_CLASS: Readonly<Record<StatusTone, string>> = {
  running: 'border-info',
  idle: 'border-muted-foreground/50',
  completed: 'border-success/70',
  failed: 'border-destructive',
  interrupted: 'border-warning',
  unknown: 'border-border border-dashed',
};

export const ROLE_BG_CLASS: Readonly<Record<RoleFamily, string>> = {
  orchestration: 'bg-[var(--canvas-role-orchestration)]',
  planning: 'bg-[var(--canvas-role-planning)]',
  implementation: 'bg-[var(--canvas-role-implementation)]',
  'review-qa': 'bg-[var(--canvas-role-review-qa)]',
  builtin: 'bg-[var(--canvas-role-builtin)]',
};

const HEAT_BG_CLASS: Readonly<Record<Exclude<HeatLevel, 'unknown'>, string>> = {
  0: 'bg-card',
  1: 'bg-primary/10',
  2: 'bg-primary/20',
  3: 'bg-primary/35',
  4: 'bg-primary/50',
};

const HEAT_LABEL: Readonly<Record<HeatLevel, string>> = {
  0: 'no tokens',
  1: 'low token use',
  2: 'moderate token use',
  3: 'high token use',
  4: 'highest token use',
  unknown: 'token use unknown',
};

function backgroundClass(family: RoleFamily, heat: HeatLevel | null): string {
  if (heat === null) return ROLE_BG_CLASS[family];
  if (heat === 'unknown') return 'bg-card canvas-heat-unknown';
  return HEAT_BG_CLASS[heat];
}

/**
 * One agent span (or the main session) on the canvas. Status is a border, an icon and a word;
 * the role family is a tint and a word; the model is text. Plain text throughout: the CLI's
 * strings are rendered, never parsed as HTML.
 */
function CanvasNodeView({ data, selected }: NodeProps<CanvasFlowNode>) {
  const { node, heat, dimmed, hiddenBelow, collapsible, collapsed, spawned, onToggle, projectId, sessionId } = data;
  const status = statusTone(node.status);
  const StatusIcon = STATUS_ICON[status.tone];
  const family = roleFamily(node.agent, node.kind);
  const agent = agentLabel(node);
  // Re-read when a provider registers or leaves, not only when this node's data changes.
  useSyncExternalStore(canvasActions.subscribe, canvasActions.version);
  const actions = canvasActions.actionsFor(node);
  const description =
    node.kind === 'main' ? (spawned > 0 ? `Coordinating ${spawned} ${spawned === 1 ? 'agent' : 'agents'}` : 'No agents spawned') : node.description;
  return (
    <div
      data-status={status.tone}
      data-role={family}
      className={`flex h-full w-full flex-col overflow-hidden rounded-md border-2 text-card-foreground shadow-xs transition-opacity ${
        STATUS_BORDER_CLASS[status.tone]
      } ${backgroundClass(family, heat)} ${dimmed ? 'opacity-30' : ''} ${selected ? 'ring-[3px] ring-ring/60' : ''}`}
    >
      {actions.length > 0 ? (
        <NodeToolbar position={Position.Top} className="nodrag nopan flex gap-1 rounded-md border bg-popover p-1 text-xs shadow-sm">
          {actions.map((action) => (
            <button
              key={action.id}
              type="button"
              disabled={action.disabled === true}
              onClick={() => void action.run(node, { projectId, sessionId, recordId: node.record_id })}
              className="rounded-sm px-2 py-1 hover:bg-accent focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:outline-hidden disabled:opacity-50"
            >
              {action.label}
            </button>
          ))}
        </NodeToolbar>
      ) : null}
      <Handle type="target" position={Position.Top} isConnectable={false} />
      <div className="flex shrink-0 items-center gap-1.5 border-b border-border/70 bg-card/60 px-2.5 py-1.5 text-xs">
        <StatusIcon
          className={`size-3.5 shrink-0 ${STATUS_TEXT_CLASS[status.tone]} ${status.tone === 'running' ? 'animate-spin' : ''}`}
          aria-hidden="true"
        />
        <span className={`shrink-0 font-medium ${STATUS_TEXT_CLASS[status.tone]}`}>{status.label}</span>
        <span aria-hidden="true" className="text-muted-foreground">
          ·
        </span>
        <span className="min-w-0 flex-1 truncate font-semibold" title={agent}>
          {agent}
        </span>
        {collapsible ? (
          <button
            type="button"
            aria-expanded={!collapsed}
            aria-label={`${collapsed ? 'Expand' : 'Collapse'} ${agent}`}
            onClick={(event) => {
              event.stopPropagation();
              onToggle(node.id, collapsed);
            }}
            className="nodrag nopan -mr-1 inline-flex shrink-0 items-center rounded-sm p-0.5 text-muted-foreground hover:bg-accent focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:outline-hidden"
          >
            {collapsed ? <ChevronRight className="size-3.5" aria-hidden="true" /> : <ChevronDown className="size-3.5" aria-hidden="true" />}
          </button>
        ) : null}
      </div>
      <div className="min-h-0 flex-1 space-y-1 px-2.5 py-1.5">
        {description !== null && description !== '' ? (
          <p className="line-clamp-2 text-xs break-words [overflow-wrap:anywhere]">{description}</p>
        ) : (
          <p className="text-xs text-muted-foreground">No description</p>
        )}
        {node.last_output !== null && node.last_output !== '' ? (
          <p className="truncate font-mono text-[11px] text-muted-foreground" title={node.last_output}>
            <span className="sr-only">Last output: </span>
            {node.last_output}
          </p>
        ) : null}
      </div>
      <div className="flex min-w-0 shrink-0 items-center gap-2 overflow-hidden border-t border-border/70 bg-card/60 px-2.5 py-1 text-[11px] text-muted-foreground">
        {node.model !== null ? (
          <span className="max-w-24 truncate rounded-sm border px-1 font-medium text-foreground" title={`Model: ${node.model}`}>
            <span className="sr-only">Model </span>
            {node.model}
          </span>
        ) : null}
        <span className="sr-only">{ROLE_FAMILY_LABEL[family]}</span>
        {node.background ? <span className="rounded-sm border border-dashed px-1">Background</span> : null}
        <span className="inline-flex items-center gap-0.5 tabular-nums" title="Tokens">
          <Coins className="size-3" aria-hidden="true" />
          <span className="sr-only">Tokens: </span>
          {nodeTokensLabel(node)}
        </span>
        {heat !== null ? <span className="sr-only">{`, ${HEAT_LABEL[heat]}`}</span> : null}
        {status.tone === 'running' ? <RunningElapsed node={node} /> : <Elapsed node={node} now={0} />}
        {node.findings !== null && node.findings > 0 ? (
          <span className="inline-flex items-center gap-0.5 text-destructive">
            <TriangleAlert className="size-3" aria-hidden="true" />
            {node.findings} {node.findings === 1 ? 'finding' : 'findings'}
          </span>
        ) : null}
        <span className="ml-auto flex items-center gap-1.5">
          {node.worktree !== null ? <WorktreeChip path={node.worktree.path} branch={node.worktree.branch} /> : null}
          {node.pr !== null && node.task_key !== null ? (
            <span className="nodrag nopan">
              <PrBadge
                pr={node.pr}
                request={{
                  project_id: projectId,
                  // The record the task lives in: a child session's own, when it was folded in.
                  session_id: node.record_id ?? sessionId,
                  task_key: node.task_key,
                  link: { type: 'pr', index: 0, expect: String(node.pr.number) },
                }}
              />
            </span>
          ) : null}
          {hiddenBelow > 0 ? (
            <span className="rounded-full bg-muted px-1.5 font-medium text-foreground tabular-nums">+{hiddenBelow} hidden</span>
          ) : null}
        </span>
      </div>
      <Handle type="source" position={Position.Bottom} isConnectable={false} />
    </div>
  );
}

function Elapsed({ node, now }: { node: GraphNode; now: number }) {
  const elapsed = elapsedSeconds(node, now);
  if (elapsed === null) return null;
  const running = node.status === 'running';
  return (
    <span className="inline-flex items-center gap-0.5 tabular-nums" title={running ? 'Running for' : 'Took'}>
      <Clock className="size-3" aria-hidden="true" />
      <span className="sr-only">{running ? 'Running for ' : 'Took '}</span>
      {formatDuration(elapsed)}
    </span>
  );
}

function RunningElapsed({ node }: { node: GraphNode }) {
  const now = useContext(CanvasClock);
  return <Elapsed node={node} now={now} />;
}

export function WorktreeChip({ path, branch }: { path: string; branch: string | null }) {
  const text = `Worktree: ${path}${branch !== null ? ` (branch ${branch})` : ''}`;
  return (
    <Hint content={text}>
      {/* Not a button: it does nothing on press. The name is on the image; the path is in the details panel. */}
      <span role="img" aria-label={text} className="nodrag nopan inline-flex items-center rounded-sm text-info">
        <FolderGit2 className="size-3.5" aria-hidden="true" />
      </span>
    </Hint>
  );
}

export const CanvasNode = memo(CanvasNodeView);
