import type { StepId } from './model.js';

/**
 * The first-run order (ADR-0030 section 1), and which step a set of facts puts the person on.
 *
 * Fixed: the CLI first (nothing else works without it), then sign-in (the CLI owns it, so it
 * cannot come earlier), then the machine's prerequisites, then the project. After sign-in the
 * person needs at most three clicks: `folder` (choose it), `confirm` (check what was found) and
 * `start` (begin the first task). `machine` is not one of them: when nothing is missing it
 * passes by itself.
 */
export const STEP_ORDER: readonly StepId[] = Object.freeze(['cli', 'signin', 'machine', 'folder', 'confirm', 'start']);

/** The steps that cost the person a click once they are signed in and the machine is ready. */
export const CLICK_STEPS: readonly StepId[] = Object.freeze(['folder', 'confirm', 'start']);

export interface Facts {
  /** The wizard was finished before (the app's own flag). */
  readonly completed: boolean;
  /** The registry already holds a project: a returning user. */
  readonly hasProjects: boolean;
  readonly cliFound: boolean;
  /** Signed in, or the framework is not enforcing sign-in yet. */
  readonly signedIn: boolean;
  /** The machine check passed or the person chose to continue. */
  readonly machineReady: boolean;
  /** The folder the person chose, or `null`. */
  readonly folder: string | null;
  /** The person confirmed what was found. */
  readonly confirmed: boolean;
  /** The first task was started. */
  readonly started: boolean;
}

/** The wizard runs only for a person who has neither finished it nor any project. */
export function shouldRun(facts: Pick<Facts, 'completed' | 'hasProjects'>): boolean {
  return !facts.completed && !facts.hasProjects;
}

/** The first step whose fact is not yet true, or `null` once the first task has started. */
export function currentStep(facts: Facts): StepId | null {
  if (!facts.cliFound) return 'cli';
  if (!facts.signedIn) return 'signin';
  if (!facts.machineReady) return 'machine';
  if (facts.folder === null) return 'folder';
  if (!facts.confirmed) return 'confirm';
  if (!facts.started) return 'start';
  return null;
}

/** How many more clicks the person owes from `facts` onward, counting only `CLICK_STEPS`. */
export function clicksRemaining(facts: Facts): number {
  const step = currentStep(facts);
  if (step === null) return 0;
  const from = STEP_ORDER.indexOf(step);
  return CLICK_STEPS.filter((click) => STEP_ORDER.indexOf(click) >= from).length;
}
