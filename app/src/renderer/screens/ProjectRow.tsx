/**
 * One bound project's row on the Projects screen, and the dialogs its actions open.
 * Moved out of `Projects.tsx` unchanged except for sync, whose state the list now owns.
 */
import { useEffect, useState, type DragEvent, type ReactNode } from 'react';
import { AlertTriangle, CheckCircle2, ChevronRight, GripVertical } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Dialog,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { TableCell, TableRow } from '@/components/ui/table';
import { Hint } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import { Loading, Problem } from '../Problem.js';
import { useAction } from '../useOperation.js';
import { Notice, WriteButton } from '../WriteButton.js';
import type {
  BindReport,
  EnvironmentReport,
  OperationResult,
  ProjectRecord,
  UpgradePlan,
  UpgradeReport,
} from '../../shared/api.js';

export type RowSyncState =
  | { readonly phase: 'idle' }
  | { readonly phase: 'pending' }
  | { readonly phase: 'done'; readonly result: OperationResult<BindReport> };

/**
 * The last path segment, POSIX or Windows — the picker can hand back either. Falls back
 * to the whole string on the degenerate input a directory picker never actually returns
 * (empty, or all separators), so a caller always has something to render.
 */
export function basename(path: string): string {
  const trimmed = path.replace(/[/\\]+$/, '');
  const segments = trimmed.split(/[/\\]/);
  const last = segments[segments.length - 1];
  return last !== undefined && last !== '' ? last : path;
}

/**
 * The name shown for a project: its stored name, or the directory's own basename.
 *
 * The fallback is load-bearing, not cosmetic — see `DevteamBridge.projectNames`'s doc
 * comment in `shared/api.ts`. It applies identically to a project this app never had the
 * chance to name (bound from the terminal) and one bound here and left unnamed, so
 * **no row anywhere in this screen ever renders a bare UUID**.
 */
export function displayName(path: string, projectId: string, names: Readonly<Record<string, string>>): string {
  return names[projectId] ?? basename(path);
}

/**
 * Three states, because the payload has three.
 *
 * `path_exists` is `null` when the CLI did not say, and that is **not** the same claim as
 * "the directory is gone". A red `missing` badge beside a path that exists is the shape
 * ADR-0015's own unmitigated risk names — "a bound project shown unbound leads the user to
 * a destructive action in the terminal" — so an unknown is labelled as one.
 */
function PathState({ exists }: { exists: boolean | null }) {
  if (exists === true) return null;
  if (exists === false) return <Badge variant="destructive">missing</Badge>;
  return (
    <Badge variant="outline" title="`devteam list --json` returned no boolean `path_exists` for this row">
      not checked
    </Badge>
  );
}

/**
 * Whether a project resolves to the store's current version.
 *
 * Nothing at all when the store has no current version: "outdated" relative to nothing is
 * a claim the payload cannot support. The icon is never the only signal — the tooltip text
 * is also the accessible name, so a colour-blind or screen-reader user gets the same fact.
 */
function VersionState({ resolvesTo, current }: { resolvesTo: string; current: string | null }) {
  if (current === null) return null;
  if (resolvesTo === current) {
    const label = `Up to date — the store's current version is ${current}.`;
    return (
      <Hint content={label}>
        <span role="img" aria-label={label} className="inline-flex text-green-600 dark:text-green-500">
          <CheckCircle2 className="size-4" aria-hidden="true" />
        </span>
      </Hint>
    );
  }
  const label = `Outdated — the store's current version is ${current}.`;
  return (
    <Hint content={label}>
      <span role="img" aria-label={label} className="inline-flex text-amber-600 dark:text-amber-500">
        <AlertTriangle className="size-4" aria-hidden="true" />
      </span>
    </Hint>
  );
}


/**
 * One boolean preference as a positive or negative badge.
 *
 * `null` is "the CLI did not say" and renders a neutral dash, not "Off": an unknown shown as
 * a negative is a false claim about the project (same rule as `path_exists`). The word is
 * always there, so the colour is never the only signal. `detail` is the tooltip.
 */
function PreferenceBadge({ on, detail }: { on: boolean | null; detail?: string }) {
  if (on === null) {
    return (
      <span className="text-muted-foreground" title="Not reported by this devteam CLI">
        —
      </span>
    );
  }
  const badge = on ? (
    <Badge variant="outline" className="border-transparent bg-green-100 text-green-800 dark:bg-green-950 dark:text-green-300">
      On
    </Badge>
  ) : (
    <Badge variant="secondary" className="text-muted-foreground">
      Off
    </Badge>
  );
  return detail !== undefined ? <Hint content={detail}>{badge}</Hint> : badge;
}

/** `suppress_notifications` is bool-or-list, and *suppressing* is the negative: `true` means Off. */
function notificationsBadge(value: boolean | readonly string[] | null | undefined) {
  if (value === null || value === undefined) return <PreferenceBadge on={null} />;
  if (typeof value === 'boolean') return <PreferenceBadge on={!value} />;
  if (value.length === 0) return <PreferenceBadge on />;
  return <PreferenceBadge on detail={`Muted: ${value.join(', ')}`} />;
}

export function settingsButtonId(projectId: string): string {
  return `open-settings-${projectId}`;
}

type RowDialog = 'upgrade' | null;

/**
 * One bound project's row, plus the dialogs its actions open.
 *
 * Pin and Unbind are not here: they live on the project's own screen (`ProjectDialogs`).
 */
export function ProjectRow({
  project,
  environment,
  projectNames,
  current,
  onChanged,
  onOpenSettings,
  selected,
  onSelect,
  dragging,
  draggable,
  onDragStart,
  onDragEnd,
  moveMenu,
  syncState,
  syncBlocked,
  onSync,
  depth = 0,
}: {
  /** How many folders deep the row sits: 0 at the top level. Indents the name, tree-style. */
  depth?: number;
  /**
   * Owned by the list, not the row: a row remounts when it moves to another folder, and a
   * sync in flight must keep its state — and its result — across that.
   */
  syncState: RowSyncState;
  /** Another sync is running; see `useProjectSyncs`. */
  syncBlocked: boolean;
  onSync: () => void;
  project: ProjectRecord;
  environment: EnvironmentReport | null;
  projectNames: Readonly<Record<string, string>>;
  current: string | null;
  onChanged: () => void;
  onOpenSettings: () => void;
  selected: boolean;
  onSelect: (checked: boolean) => void;
  dragging: boolean;
  /** Only when there is a folder to drop on. */
  draggable: boolean;
  onDragStart: (event: DragEvent<HTMLElement>) => void;
  onDragEnd: () => void;
  moveMenu: ReactNode;
}) {
  const [dialog, setDialog] = useState<RowDialog>(null);
  const name = displayName(project.path, project.project_id, projectNames);

  return (
    <TableRow data-state={selected ? 'selected' : undefined} className={cn('group/row', dragging && 'opacity-50')}>
      <TableCell className="w-14">
        <span className="flex items-center gap-1.5">
          {/* The handle is the drag source, not the whole row, so selecting text in a cell or
              pressing a row button never starts a drag by accident. Hidden from assistive
              tech: the row's "Move to folder" menu is the keyboard path to the same result. */}
          {draggable ? (
            <span
              draggable
              onDragStart={onDragStart}
              onDragEnd={onDragEnd}
              aria-hidden="true"
              title="Drag to a folder"
              data-drag-handle={project.project_id}
              className="-ml-1 cursor-grab text-muted-foreground/40 transition-colors group-hover/row:text-muted-foreground active:cursor-grabbing"
            >
              <GripVertical className="size-4" />
            </span>
          ) : null}
          <Checkbox checked={selected} onCheckedChange={(checked) => onSelect(checked === true)} aria-label={`Select ${name}`} />
        </span>
      </TableCell>
      <TableCell style={depth > 0 ? { paddingLeft: `calc(0.5rem + ${depth * 1.5}rem)` } : undefined}>
        {/* The name only. `project_id` is a UUID that means nothing to the reader and is
            never rendered — `devteam list` in a terminal is where a debugger gets it. The
            name is the way into the project's settings, so it is a real button. */}
        <span className="flex items-center gap-2">
          <Hint
            content={
              <span className="block max-w-sm space-y-0.5">
                <span className="block">Open this project&apos;s settings</span>
                <span className="block break-all font-mono text-xs opacity-80">{project.path}</span>
              </span>
            }
          >
            <button
              type="button"
              id={settingsButtonId(project.project_id)}
              onClick={onOpenSettings}
              className="group inline-flex items-center gap-1 rounded-sm font-medium outline-none hover:text-primary focus-visible:ring-[3px] focus-visible:ring-ring/50"
              aria-label={`${name} — open settings`}
            >
              {name}
              <ChevronRight className="size-3.5 text-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:text-primary" aria-hidden="true" />
            </button>
          </Hint>
          <PathState exists={project.path_exists} />
        </span>
      </TableCell>
      <TableCell>
        <span className="flex items-center gap-2 whitespace-nowrap">
          {project.resolves_to !== null ? (
            <>
              <Badge variant="outline">{project.resolves_to}</Badge>
              <VersionState resolvesTo={project.resolves_to} current={current} />
            </>
          ) : (
            <span className="text-muted-foreground">—</span>
          )}
          {project.pin !== null ? <Badge variant="secondary">pinned {project.pin}</Badge> : null}
        </span>
      </TableCell>
      <TableCell>{project.mode ?? '—'}</TableCell>
      <TableCell>{project.providers.length === 0 ? '—' : project.providers.join(', ')}</TableCell>
      <TableCell>
        <PreferenceBadge on={project.preferences?.auto_update ?? null} />
      </TableCell>
      <TableCell>
        <PreferenceBadge on={project.preferences?.worktree_active ?? null} />
      </TableCell>
      <TableCell>{notificationsBadge(project.preferences?.suppress_notifications)}</TableCell>
      <TableCell>
        <div className="flex flex-nowrap items-center gap-2 whitespace-nowrap">
          <WriteButton
            command="sync"
            environment={environment}
            variant="outline"
            size="xs"
            tooltip={syncBlocked ? 'Another sync is running' : "Re-apply this project's store version to its files"}
            disabled={syncState.phase === 'pending' || syncBlocked}
            onClick={onSync}
          >
            {syncState.phase === 'pending' ? 'Syncing…' : 'Sync'}
          </WriteButton>
          <WriteButton
            command="upgrade"
            environment={environment}
            variant="outline"
            size="xs"
            tooltip="Move this project's memory into the store — shows the plan first"
            onClick={() => setDialog('upgrade')}
          >
            Upgrade…
          </WriteButton>
          <Hint content="Move to a folder">
            <span className="inline-flex">{moveMenu}</span>
          </Hint>
        </div>
        {syncState.phase === 'done' && !syncState.result.ok ? (
          <div className="pt-2">
            <Problem problem={syncState.result} />
          </div>
        ) : null}
        {syncState.phase === 'done' ? <Notice result={syncState.result} /> : null}
      </TableCell>

      <UpgradeDialog
        open={dialog === 'upgrade'}
        onOpenChange={(open) => setDialog(open ? 'upgrade' : null)}
        projectId={project.project_id}
        name={name}
        onApplied={onChanged}
      />
    </TableRow>
  );
}

/**
 * The two-step upgrade, structurally enforced: `apply` is not offered until `plan` has
 * resolved, and the plan is what shows `collisions`, `git_tracked` and `actions` before
 * anything happens. The plan is fetched automatically on open — it only reads — and the
 * apply step still needs its own explicit click.
 */
function UpgradeDialog({
  open,
  onOpenChange,
  projectId,
  name,
  onApplied,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  projectId: string;
  name: string;
  onApplied: () => void;
}) {
  const plan = useAction(() => window.devteam.planUpgrade(projectId));
  const apply = useAction(() => window.devteam.applyUpgrade(projectId));

  useEffect(() => {
    if (open) {
      void plan.run();
    } else {
      plan.reset();
      apply.reset();
    }
    // `plan`/`apply` are re-created every render (fresh closures from `useAction`), but
    // their `run`/`reset` identities are what would matter here and `reset` is stable;
    // this effect is keyed on the dialog's own open/target, not on those closures.
  }, [open, projectId]);

  const planData = plan.state.phase === 'done' && plan.state.result.ok ? plan.state.result.data : null;
  const nothingToDo = planData !== null && planData.actions.length === 0;
  const applying = apply.state.phase === 'pending';

  return (
    // Closing mid-apply would drop the report of a write that is still running.
    <Dialog open={open} onOpenChange={(next) => (next || !applying ? onOpenChange(next) : undefined)}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Upgrade {name}</DialogTitle>
          <DialogDescription>
            Moves this project&apos;s memory into the store and quarantines what it moved. Nothing changes until
            Apply is confirmed below.
          </DialogDescription>
        </DialogHeader>

        <DialogBody className="space-y-4">
        {plan.state.phase !== 'done' ? <Loading what="devteam upgrade (plan)" /> : null}
        {plan.state.phase === 'done' && !plan.state.result.ok ? <Problem problem={plan.state.result} /> : null}
        {planData !== null ? <UpgradePlanSummary plan={planData} /> : null}

        {apply.state.phase === 'done' && !apply.state.result.ok ? <Problem problem={apply.state.result} /> : null}
        {apply.state.phase === 'done' && apply.state.result.ok ? (
          <UpgradeReportSummary report={apply.state.result.data} />
        ) : null}
        {apply.state.phase === 'done' ? <Notice result={apply.state.result} /> : null}
        </DialogBody>

        <DialogFooter>
          <Button variant="outline" disabled={applying} onClick={() => onOpenChange(false)}>
            {apply.state.phase === 'done' && apply.state.result.ok ? 'Close' : 'Cancel'}
          </Button>
          {apply.state.phase === 'done' && apply.state.result.ok ? (
            <Button onClick={() => onOpenChange(false)}>Done</Button>
          ) : (
            <Button
              disabled={planData === null || nothingToDo || apply.state.phase === 'pending'}
              onClick={() => {
                void apply.run().then((result) => {
                  if (result.ok) onApplied();
                });
              }}
              title={nothingToDo ? 'The plan has no actions — there is nothing to apply.' : undefined}
            >
              {apply.state.phase === 'pending' ? 'Applying…' : 'Apply'}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function UpgradePlanSummary({ plan }: { plan: UpgradePlan }) {
  return (
    <div className="space-y-2 text-sm">
      <p>
        Layout {plan.from_layout} → {plan.to_layout} · {plan.files} file{plan.files === 1 ? '' : 's'} · destination{' '}
        <span className="font-mono text-xs">{plan.destination}</span>
      </p>
      {plan.actions.length === 0 ? (
        <p className="text-muted-foreground">The plan has no actions — this project has nothing to upgrade.</p>
      ) : (
        <div>
          <p className="font-medium">Actions:</p>
          <ul className="list-inside list-disc text-xs text-muted-foreground">
            {plan.actions.map((action, index) => (
              <li key={index}>{action}</li>
            ))}
          </ul>
        </div>
      )}
      {plan.collisions.length > 0 ? (
        <div>
          <p className="font-medium text-destructive">Collisions:</p>
          <ul className="list-inside list-disc font-mono text-xs text-destructive">
            {plan.collisions.map((path) => (
              <li key={path}>{path}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {plan.git_tracked.length > 0 ? (
        <div>
          <p className="font-medium">Git-tracked paths this touches:</p>
          <ul className="list-inside list-disc font-mono text-xs text-muted-foreground">
            {plan.git_tracked.map((path) => (
              <li key={path}>{path}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}

/**
 * `state_pointer`/`memory_pointer` and `git_tracked` are surfaced because they are exactly
 * what changed on disk and what the user still owes a commit — the same honesty `bind`'s
 * `merged_project_files` needs, for the same reason.
 */
function UpgradeReportSummary({ report }: { report: UpgradeReport }) {
  return (
    <div className="space-y-2 text-sm">
      <p>
        Copied {report.copied} file{report.copied === 1 ? '' : 's'} to{' '}
        <span className="font-mono text-xs">{report.destination}</span>.
      </p>
      {report.quarantined !== null ? (
        <p>
          Quarantined to <span className="font-mono text-xs">{report.quarantined}</span>.
        </p>
      ) : null}
      <p className="font-mono text-xs text-muted-foreground">
        state → {report.state_pointer} · memory → {report.memory_pointer}
      </p>
      {report.git_tracked.length > 0 ? (
        <div>
          <p className="font-medium">Commit these yourself:</p>
          <ul className="list-inside list-disc font-mono text-xs text-muted-foreground">
            {report.git_tracked.map((path) => (
              <li key={path}>{path}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}

