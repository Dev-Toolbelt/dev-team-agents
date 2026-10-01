import type { EnvironmentReport } from '../shared/api.js';

/**
 * Whether a write action is withheld right now, and why.
 *
 * `command` must be the exact CLI subcommand words the action would run, space-joined —
 * `bind`, `unbind`, `sync`, `pin`, `upgrade` — per the pinned contract on
 * `EnvironmentReport.withheld`. An exact match only: a prefix match would let `pin`
 * accidentally cover a future `pin release` two-word leaf withheld for a different reason,
 * silently hiding the wrong action.
 */
export type Withheld = { readonly withheld: true; readonly reason: string } | { readonly withheld: false };

export function isWithheld(entries: EnvironmentReport['withheld'], command: string): Withheld {
  const match = entries.find((entry) => entry.command === command);
  return match === undefined ? { withheld: false } : { withheld: true, reason: match.reason };
}

/**
 * The exact subcommand keys the Plugins tab's write buttons run, which is what
 * `EnvironmentReport.withheld` is keyed by. `plugin config set` and `plugin config unset`
 * are two leaves in the framework's table; a config save may use either, so it is withheld
 * when either is (`isAnyWithheld`).
 */
export const PLUGIN_COMMANDS = {
  enable: 'plugin enable',
  disable: 'plugin disable',
  configSet: 'plugin config set',
  configUnset: 'plugin config unset',
  run: 'plugin run',
} as const;

/**
 * The exact subcommand keys the Integrations screens' write buttons run. Saving account
 * fields may run `connect` or `config set`/`config unset`, so callers gate with `isAnyWithheld`.
 */
export const INTEGRATION_COMMANDS = {
  connect: 'integration connect',
  disconnect: 'integration disconnect',
  configSet: 'integration config set',
  configUnset: 'integration config unset',
  test: 'integration test',
} as const;

/** The exact subcommand keys the Credentials tab's write buttons run. */
export const CREDENTIALS_COMMANDS = {
  init: 'cred local init',
  patch: 'cred local patch',
} as const;

/** The first of `commands` that is withheld, so one reason is reported when several are. */
export function isAnyWithheld(entries: EnvironmentReport['withheld'], commands: readonly string[]): Withheld {
  for (const command of commands) {
    const result = isWithheld(entries, command);
    if (result.withheld) return result;
  }
  return { withheld: false };
}
