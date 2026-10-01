import { AlertTriangle, Loader2 } from 'lucide-react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import type { OperationResult, ProblemKind } from '../shared/api.js';

/**
 * How a failed operation is shown. One component, so every screen reports a problem the
 * same way and none of them can quietly render an empty list instead.
 *
 * The CLI's own `error` and `hint` are shown verbatim. They are written to be actionable
 * ("Run `devteam bind`."), and a paraphrase would lose that while sounding tidier.
 */
const TITLES: Record<ProblemKind, string> = {
  usage: 'The app asked the CLI something malformed',
  environment: 'The environment is not ready',
  conflict: 'The CLI refused the request',
  // Exit 1 carrying an error document. It used to fall through to `environment`, so a
  // finding was titled "The environment is not ready".
  findings: 'The CLI ran and reported a finding',
  refused: 'This app would not run that',
  'contract-breach': 'The CLI’s answer did not match the documented contract',
  unavailable: 'The devteam CLI could not be run',
  timeout: 'The CLI did not answer in time',
};

/** Titles for a `reason` the CLI attaches, where it says more than the exit code does. */
const REASON_TITLES: Record<string, string> = {
  'invalid-source': 'This source cannot be installed',
};

type Failure = Extract<OperationResult<never>, { ok: false }>;

/** The heading a failure is reported under — shared by the inline alert and the toast. */
export function problemTitle(problem: Failure): string {
  return (problem.reason !== undefined ? REASON_TITLES[problem.reason] : undefined) ?? TITLES[problem.kind];
}

export function Problem({ problem }: { problem: Failure }) {
  const title = problemTitle(problem);
  return (
    <Alert variant="destructive">
      <AlertTriangle />
      <AlertTitle>{title}</AlertTitle>
      <AlertDescription>
        <p>{problem.message}</p>
        {problem.hint !== undefined ? <p className="text-muted-foreground">{problem.hint}</p> : null}
        <p className="font-mono text-xs text-muted-foreground">
          {problem.command}
          {problem.exitCode !== null ? ` → exit ${problem.exitCode}` : ''}
        </p>
      </AlertDescription>
    </Alert>
  );
}

export function Loading({ what }: { what: string }) {
  return (
    <p className="flex items-center gap-2 py-8 text-sm text-muted-foreground" aria-live="polite">
      <Loader2 className="size-4 animate-spin" aria-hidden="true" />
      Running {what}…
    </p>
  );
}

export function Empty({ children }: { children: React.ReactNode }) {
  return <p className="py-8 text-sm text-muted-foreground">{children}</p>;
}
