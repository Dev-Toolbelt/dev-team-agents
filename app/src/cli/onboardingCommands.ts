/**
 * The first-run commands this app may run (ADR-0030), kept apart from `operations.ts` for the
 * reason `accountCommands.ts` is: that file does not grow by another screen's worth, and
 * `onboardingOperations.ts` can import the shapes without a cycle.
 *
 * `detect` only reads: it inspects a folder and the machine's PATH and writes nothing, so it
 * joins `READ_ONLY_COMMANDS`. `start` sets the folder up for the framework, which is a write
 * the framework classifies in `compat.MUTATING`, so it joins `GATED_COMMANDS` and runs only
 * with a written schema declaration. `test/operations.test.ts` checks both against `compat.py`.
 *
 * Both take their folder from `--path`, always one the main process handed back through the
 * folder picker (`main/ipc.ts` refuses any other), and neither takes a secret.
 */

export const ONBOARDING_READ_ONLY_COMMANDS: readonly (readonly string[])[] = Object.freeze([['detect']]);

export const ONBOARDING_GATED_COMMANDS: readonly (readonly string[])[] = Object.freeze([['start']]);

type Shape = {
  readonly operands: 0 | 1 | 2 | 3;
  readonly flags: Readonly<Record<string, 'value' | 'bare' | 'repeatable'>>;
};

/** Keyed like `COMMAND_SHAPES`: the command words joined with a space. */
export const ONBOARDING_SHAPES: Readonly<Record<string, Shape>> = Object.freeze({
  detect: { operands: 0, flags: { '--path': 'value' } },
  start: { operands: 0, flags: { '--path': 'value', '--provider': 'value', '--type': 'value' } },
});
