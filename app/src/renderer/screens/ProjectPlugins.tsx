import { useCallback, useEffect, useRef, useState } from 'react';
import { CircleAlert, Puzzle } from 'lucide-react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import type { EnvironmentReport, PluginList, ProjectRecord } from '../../shared/api.js';
import { PluginCard } from '../plugins/PluginCard.js';
import { Empty, Loading, Problem } from '../Problem.js';
import { useOperation } from '../useOperation.js';

/**
 * The Plugins tab of one project's screen: one card per plugin the CLI lists, drawn only from
 * what `plugin list` says (ADR-0019 § 5). A plugin added to the core appears here with no
 * change to the app.
 *
 * `onDirtyChange` reports the number of unsaved config edits across all cards, so the screen
 * that owns the tabs can warn before the person leaves with edits pending.
 */
export function ProjectPlugins({
  project,
  environment,
  onDirtyChange,
  onRunningChange,
}: {
  project: ProjectRecord;
  environment: EnvironmentReport | null;
  onDirtyChange: (count: number) => void;
  /** How many actions are running across all cards, so leaving can warn about them. */
  onRunningChange: (count: number) => void;
}) {
  const projectId = project.project_id;
  const { state, refreshing, reload } = useOperation(() => window.devteam.projectPlugins(projectId), [projectId]);
  const [openCards, setOpenCards] = useState<Readonly<Record<string, boolean>>>({});
  const setCardOpen = useCallback((name: string, open: boolean) => {
    setOpenCards((previous) => (previous[name] === open ? previous : { ...previous, [name]: open }));
  }, []);
  const [dirty, setDirty] = useState<Readonly<Record<string, number>>>({});

  // The last list that loaded. A reload that fails must not unmount the cards: their drafts
  // are the only copy of what the person typed.
  const lastGood = useRef<PluginList | null>(null);
  if (state.phase === 'done' && state.result.ok) lastGood.current = state.result.data;

  const cardDirty = useCallback((name: string, count: number) => {
    if (count > 0) setCardOpen(name, true);
    setDirty((previous) => {
      if ((previous[name] ?? 0) === count) return previous;
      const next = { ...previous };
      if (count === 0) delete next[name];
      else next[name] = count;
      return next;
    });
  }, [setCardOpen]);

  const [running, setRunning] = useState<Readonly<Record<string, number>>>({});
  const cardRunning = useCallback((name: string, count: number) => {
    if (count > 0) setCardOpen(name, true);
    setRunning((previous) => {
      if ((previous[name] ?? 0) === count) return previous;
      const next = { ...previous };
      if (count === 0) delete next[name];
      else next[name] = count;
      return next;
    });
  }, [setCardOpen]);
  const runningTotal = Object.values(running).reduce((sum, count) => sum + count, 0);
  useEffect(() => {
    onRunningChange(runningTotal);
  }, [runningTotal, onRunningChange]);

  const total = Object.values(dirty).reduce((sum, count) => sum + count, 0);
  useEffect(() => {
    onDirtyChange(total);
  }, [total, onDirtyChange]);

  const seenState = useRef(state);
  const listVersion = useRef(0);
  if (seenState.current !== state) {
    seenState.current = state;
    if (state.phase === 'done') listVersion.current += 1;
  }

  const list = lastGood.current;
  if (list === null) {
    if (state.phase === 'loading') return <Loading what="devteam plugin list" />;
    if (!state.result.ok) {
      return (
        <div className="space-y-4">
          <Problem problem={state.result} />
          <Button variant="outline" size="sm" onClick={reload}>
            Try again
          </Button>
        </div>
      );
    }
  }
  if (list === null) return null;

  const reloadProblem = state.phase === 'done' && !state.result.ok ? state.result : null;

  return (
    <div className="space-y-5">
      {reloadProblem !== null ? (
        <div className="space-y-2">
          <Problem problem={reloadProblem} />
          <Button variant="outline" size="sm" onClick={reload}>
            Try again
          </Button>
        </div>
      ) : null}
      {list.invalid.length > 0 ? (
        <Alert variant="destructive" role="status">
          <CircleAlert />
          <AlertTitle>
            {list.invalid.length === 1 ? 'A plugin was skipped' : `${list.invalid.length} plugins were skipped`}
          </AlertTitle>
          <AlertDescription>
            <p>This plugin&apos;s manifest is invalid and it was skipped.</p>
            <ul className="mt-1 list-disc pl-5">
              {list.invalid.map((item) => (
                <li key={item.name_or_dir}>
                  <span className="font-mono">{item.name_or_dir}</span>: {item.problem}
                </li>
              ))}
            </ul>
          </AlertDescription>
        </Alert>
      ) : null}
      {list.plugins.length === 0 ? (
        <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed py-10 text-center">
          <Puzzle className="size-6 text-muted-foreground" aria-hidden="true" />
          <NoPlugins project={project} />
        </div>
      ) : (
        list.plugins.map((plugin) => (
          <PluginCard
            key={plugin.name}
            projectId={projectId}
            plugin={plugin}
            environment={environment}
            refreshing={refreshing}
            reloadFailed={reloadProblem !== null}
            listVersion={listVersion.current}
            onChanged={reload}
            onDirtyChange={cardDirty}
            onRunningChange={cardRunning}
            open={openCards[plugin.name] ?? false}
            onOpenChange={setCardOpen}
            lockedReason={
              (dirty[plugin.name] ?? 0) > 0 ? 'Save or discard changes first' : (running[plugin.name] ?? 0) > 0 ? 'An action is running' : null
            }
          />
        ))
      )}
    </div>
  );
}

/**
 * Why a project lists no plugins. Plugins ship in the core version a project resolves to, and
 * `plugins/` is optional there (ADR-0019 amendment), so a version older than the plugin system
 * answers with an empty list rather than an error. Saying which version, and how to move off
 * it, is what lets the person act; "no plugins" alone reads as a broken screen.
 */
function NoPlugins({ project }: { project: ProjectRecord }) {
  const version = project.resolves_to;
  const code = 'rounded bg-muted px-1 py-0.5 font-mono text-xs text-foreground';
  return (
    <Empty>
      {version === null ? (
        <>No plugins are available: the dev-team-agents version this project uses could not be resolved.</>
      ) : (
        <>
          This project uses dev-team-agents <span className="font-medium text-foreground">{version}</span>, which
          ships no plugins.
        </>
      )}
      <span className="mt-2 block">
        {project.pin !== null ? (
          <>
            It is pinned to {project.pin}. Release the pin with <code className={code}>devteam pin --release</code>, then
            run <code className={code}>devteam sync</code> in the project.
          </>
        ) : (
          <>
            Update with <code className={code}>devteam update</code>, which syncs every unpinned project, then reopen this
            tab.
          </>
        )}
      </span>
    </Empty>
  );
}
