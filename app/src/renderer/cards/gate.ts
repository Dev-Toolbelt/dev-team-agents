import type { EnvironmentReport } from '../../shared/api.js';
import { isAnyWithheld, type Withheld } from '../writeActionGating.js';

const NOT_CHECKED: Withheld = { withheld: true, reason: 'the app has not finished checking its own preconditions' };

/** Whether any of `commands` is withheld; withheld outright until the environment report has arrived. */
export function gateFor(environment: EnvironmentReport | null, commands: readonly string[]): Withheld {
  return environment === null ? NOT_CHECKED : isAnyWithheld(environment.withheld, commands);
}
