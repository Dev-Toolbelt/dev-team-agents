import { memo } from 'react';
import type { Node, NodeProps } from '@xyflow/react';
import { Activity, ChevronDown, ChevronRight, CircleAlert, Moon, Pause } from 'lucide-react';

import { formatDateTime } from '../boardModel.js';
import { frameTokensLabel, type TraceProblem } from '../canvasModel.js';
import { ProviderIcon, providerLabel } from '../providers/ProviderIcon.js';
import { PrBadge } from './PrBadge.js';
import type { BoardSessionStatus, GraphGroup } from '../../shared/api.js';

export type CanvasGroupData = {
  readonly group: GraphGroup;
  readonly projectId: string;
  readonly sessionId: string;
  readonly collapsed: boolean;
  /** Nodes not drawn because this frame is collapsed. */
  readonly hidden: number;
  /** The CLI drew this session without its trace: none was found, or it could not be read. */
  readonly traceProblem: TraceProblem | null;
  readonly dimmed: boolean;
  readonly onToggle: (id: string, shownCollapsed: boolean) => void;
};

export type CanvasFlowGroup = Node<CanvasGroupData, 'canvasGroup'>;

const SESSION_STATUS: Readonly<Record<BoardSessionStatus, { readonly icon: typeof Activity; readonly label: string }>> = {
  active: { icon: Activity, label: 'Active' },
  idle: { icon: Pause, label: 'Idle' },
  ended: { icon: Moon, label: 'Ended' },
};

const TRACE_PROBLEM_TEXT: Readonly<Record<TraceProblem, string>> = {
  missing: 'No trace for this session: agents are listed flat, without their tree or usage.',
  unreadable: 'Trace unreadable for this session: showing board data, without the agent tree or usage.',
};

function ToggleButton({ collapsed, name, onClick }: { collapsed: boolean; name: string; onClick: () => void }) {
  return (
    <button
      type="button"
      aria-expanded={!collapsed}
      aria-label={`${collapsed ? 'Expand' : 'Collapse'} ${name}`}
      onClick={(event) => {
        event.stopPropagation();
        onClick();
      }}
      className="nodrag nopan inline-flex shrink-0 items-center rounded-sm p-0.5 text-muted-foreground hover:bg-accent focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:outline-hidden"
    >
      {collapsed ? <ChevronRight className="size-4" aria-hidden="true" /> : <ChevronDown className="size-4" aria-hidden="true" />}
    </button>
  );
}

/** A session frame (provider, status, branch, PRs, token total) or a turn frame inside it. */
function CanvasGroupView({ data }: NodeProps<CanvasFlowGroup>) {
  const { group, collapsed, hidden, traceProblem, dimmed, onToggle, projectId, sessionId } = data;
  if (group.kind === 'turn') {
    return (
      <div
        className={`h-full w-full rounded-md border border-border/80 bg-[var(--canvas-frame-turn)] ${dimmed ? 'opacity-40' : ''}`}
        data-kind="turn"
      >
        <div className="flex h-10 items-center gap-2 px-3 text-xs">
          <ToggleButton collapsed={collapsed} name={`turn ${group.label}`} onClick={() => onToggle(group.id, collapsed)} />
          <span className="min-w-0 truncate font-semibold" title={group.label}>
            {group.label}
          </span>
          {group.at !== null ? (
            <time className="shrink-0 text-muted-foreground tabular-nums" dateTime={new Date(group.at * 1000).toISOString()}>
              {formatDateTime(group.at)}
            </time>
          ) : null}
          <span className="ml-auto shrink-0 text-muted-foreground tabular-nums">{frameTokensLabel(group)}</span>
          {collapsed && hidden > 0 ? (
            <span className="shrink-0 rounded-full bg-muted px-1.5 font-medium tabular-nums">+{hidden} hidden</span>
          ) : null}
        </div>
      </div>
    );
  }
  const status = group.status === null ? null : SESSION_STATUS[group.status];
  const StatusIcon = status?.icon;
  return (
    <div
      className={`h-full w-full rounded-lg border-2 border-border bg-[var(--canvas-frame-session)] ${dimmed ? 'opacity-40' : ''}`}
      data-kind="session"
    >
      <div className="space-y-1 px-3 pt-2.5 text-xs">
        <div className="flex items-center gap-2">
          <ToggleButton collapsed={collapsed} name={`session ${group.label}`} onClick={() => onToggle(group.id, collapsed)} />
          {group.provider !== null ? (
            <>
              <ProviderIcon provider={group.provider} decorative />
              <span className="sr-only">{providerLabel(group.provider)}</span>
            </>
          ) : null}
          <span className="min-w-0 truncate text-sm font-semibold" title={group.label}>
            {group.label}
          </span>
          {status !== null && StatusIcon !== undefined ? (
            <span className="ml-auto inline-flex shrink-0 items-center gap-1 text-muted-foreground">
              <StatusIcon className="size-3.5" aria-hidden="true" />
              {status.label}
            </span>
          ) : null}
        </div>
        <div className="flex items-center gap-3 pl-6 text-muted-foreground">
          <span className="min-w-0 truncate font-mono">{group.branch ?? 'no branch'}</span>
          <span className="shrink-0 tabular-nums">{frameTokensLabel(group)}</span>
          {group.prs.length > 0 ? (
            <span className="nodrag nopan flex shrink-0 items-center gap-1.5">
              {group.prs.map((pr, index) => (
                <PrBadge
                  key={`${pr.url}:${index}`}
                  pr={pr}
                  request={{ project_id: projectId, session_id: sessionId, task_key: null, link: { type: 'pr', index, expect: String(pr.number) } }}
                />
              ))}
            </span>
          ) : null}
          {collapsed && hidden > 0 ? (
            <span className="ml-auto shrink-0 rounded-full bg-muted px-1.5 font-medium text-foreground tabular-nums">+{hidden} hidden</span>
          ) : null}
        </div>
        {traceProblem !== null && !collapsed ? (
          <p className="flex items-center gap-1 pl-6 text-warning-foreground dark:text-warning" role="note">
            <CircleAlert className="size-3.5 shrink-0" aria-hidden="true" />
            {TRACE_PROBLEM_TEXT[traceProblem]}
          </p>
        ) : null}
      </div>
    </div>
  );
}

export const CanvasGroup = memo(CanvasGroupView);
