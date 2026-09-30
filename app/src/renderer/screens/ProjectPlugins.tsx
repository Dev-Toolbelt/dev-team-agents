import { useCallback, useEffect, useRef, useState } from 'react';
import { Puzzle } from 'lucide-react';

import { Button } from '@/components/ui/button';
import type { EnvironmentReport, PluginList, ProjectRecord } from '../../shared/api.js';
import { PluginCard } from '../plugins/PluginCard.js';
import { Empty, Loading, Problem } from '../Problem.js';
import { useOperation } from '../useOperation.js';

/**
 * The Plugins tab of one project's screen: one card per plugin the CLI lists, drawn only from
 * what `plugin list` says (ADR-0017 § 5). A plugin added to the core appears here with no
 * change to the app.
 *
 * `onDirtyChange` reports the number of unsaved config edits across all cards, so the screen
 * that owns the tabs can warn before the person leaves with edits pending.
 */
export function ProjectPlugins({
  project,
  environment,
  onDirtyChange,
}: {
  project: ProjectRecord;
  environment: EnvironmentReport | null;
  onDirtyChange: (count: number) => void;
}) {
  const projectId = project.project_id;
  const { state, refreshing, reload } = useOperation(() => window.devteam.projectPlugins(projectId), [projectId]);
  const [dirty, setDirty] = useState<Readonly<Record<string, number>>>({});

  // The last list that loaded. A reload that fails must not unmount the cards: their drafts
  // are the only copy of what the person typed.
  const lastGood = useRef<PluginList | null>(null);
  if (state.phase === 'done' && state.result.ok) lastGood.current = state.result.data;

  const cardDirty = useCallback((name: string, count: number) => {
    setDirty((previous) => {
      if ((previous[name] ?? 0) === count) return previous;
      const next = { ...previous };
      if (count === 0) delete next[name];
      else next[name] = count;
      return next;
    });
  }, []);

  const total = Object.values(dirty).reduce((sum, count) => sum + count, 0);
  useEffect(() => {
    onDirtyChange(total);
  }, [total, onDirtyChange]);

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
      {list.plugins.length === 0 ? (
        <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed py-10 text-center">
          <Puzzle className="size-6 text-muted-foreground" aria-hidden="true" />
          <Empty>This version of dev-team-agents ships no plugins.</Empty>
        </div>
      ) : (
        list.plugins.map((plugin) => (
          <PluginCard
            key={plugin.name}
            projectId={projectId}
            plugin={plugin}
            environment={environment}
            refreshing={refreshing}
            onChanged={reload}
            onDirtyChange={cardDirty}
          />
        ))
      )}
    </div>
  );
}
