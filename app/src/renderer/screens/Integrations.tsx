import type { EnvironmentReport } from '../../shared/api.js';
import { IntegrationCards } from '../integrations/IntegrationList.js';

/**
 * The top-level Integrations tab: one card per integration the CLI lists, in account mode —
 * the token, the account fields, Test connection and Disconnect (ADR-0023).
 */
export function Integrations({
  environment,
  onAccountChanged,
}: {
  environment: EnvironmentReport | null;
  /** An account write or test succeeded: the project screens' account readouts are now stale. */
  onAccountChanged?: (() => void) | undefined;
}) {
  return (
    <section aria-label="Integrations" className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Connect an account once; every project on this machine can then use it. Tokens are kept in the OS keychain and are never shown again.
      </p>
      <IntegrationCards mode="account" projectId={null} environment={environment} onAccountChanged={onAccountChanged} />
    </section>
  );
}
