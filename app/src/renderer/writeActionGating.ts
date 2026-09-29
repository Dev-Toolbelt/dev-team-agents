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
