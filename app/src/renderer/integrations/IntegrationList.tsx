import { useCallback } from 'react';
import { Plug } from 'lucide-react';

import { Button } from '@/components/ui/button';
import type { EnvironmentReport, IntegrationView, ProjectId } from '../../shared/api.js';
import { Empty, Loading, Problem } from '../Problem.js';
import { IntegrationCard, type IntegrationMode } from './IntegrationCard.js';
import { useIntegrationList } from './useIntegrationList.js';

/**
 * The cards of every integration the CLI lists, for either screen. The two screens differ
 * only in the mode they draw and the project they ask about.
 */
export function IntegrationCards({
  mode,
  projectId,
  environment,
  onDirtyChange,
  onRunningChange,
  onConnectAccount,
  active = true,
  refreshNonce = 0,
  onAccountChanged,
}: {
  mode: IntegrationMode;
  projectId: ProjectId | null;
  environment: EnvironmentReport | null;
  onDirtyChange?: (count: number) => void;
  onRunningChange?: (count: number) => void;
  onConnectAccount?: (() => void) | undefined;
  /** Whether the screen holding these cards is visible; a return to visible reloads the list. */
  active?: boolean;
  /** Changes whenever an account write elsewhere made this list stale. */
  refreshNonce?: number;
  /** Account mode: a write or test succeeded, so every project's list is stale. */
  onAccountChanged?: (() => void) | undefined;
}) {
  const hook = useIntegrationList(projectId, onDirtyChange, onRunningChange, active, refreshNonce);
  const { replace } = hook;
  const onView = useCallback(
    (view: IntegrationView) => {
      replace(view);
      if (mode === 'account') onAccountChanged?.();
    },
    [replace, mode, onAccountChanged],
  );
  const { state, list, views, reload, reloadProblem } = hook;

  if (list === null) {
    if (state.phase === 'loading') return <Loading what="devteam integration list" />;
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
    return null;
  }

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
      {views.length === 0 ? (
        <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed py-10 text-center">
          <Plug className="size-6 text-muted-foreground" aria-hidden="true" />
          <Empty>No integrations are available in this version of dev-team-agents.</Empty>
        </div>
      ) : (
        views.map((view) => (
          <IntegrationCard
            key={view.name}
            mode={mode}
            projectId={projectId}
            view={view}
            environment={environment}
            onView={onView}
            onDirtyChange={hook.cardDirty}
            onRunningChange={hook.cardRunning}
            open={hook.openCards[view.name] ?? false}
            onOpenChange={hook.setCardOpen}
            lockedReason={hook.lockedReason(view.name)}
            onConnectAccount={onConnectAccount}
          />
        ))
      )}
    </div>
  );
}
