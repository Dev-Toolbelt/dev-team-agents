import type { EnvironmentReport, ProjectRecord } from '../../shared/api.js';
import { IntegrationCards } from '../integrations/IntegrationList.js';

/**
 * The Integrations tab of one project's screen: the account standing read-only and the
 * project-scope fields (ADR-0023). `onDirtyChange` / `onRunningChange` let the screen that owns
 * the tabs warn before the person leaves with edits pending.
 */
export function ProjectIntegrations({
  project,
  environment,
  onDirtyChange,
  onRunningChange,
  onConnectAccount,
  active = true,
  refreshNonce = 0,
}: {
  project: ProjectRecord;
  environment: EnvironmentReport | null;
  onDirtyChange: (count: number) => void;
  onRunningChange: (count: number) => void;
  onConnectAccount?: (() => void) | undefined;
  /** Whether this tab is the one showing; the list reloads each time it becomes so. */
  active?: boolean;
  /** Changes when an account write elsewhere made the list stale. */
  refreshNonce?: number;
}) {
  return (
    <IntegrationCards
      mode="project"
      projectId={project.project_id}
      environment={environment}
      onDirtyChange={onDirtyChange}
      onRunningChange={onRunningChange}
      onConnectAccount={onConnectAccount}
      active={active}
      refreshNonce={refreshNonce}
    />
  );
}
