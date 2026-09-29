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

export function Problem({ problem }: { problem: Extract<OperationResult<never>, { ok: false }> }) {
  return (
    <Alert variant="destructive">
      <AlertTriangle />
      <AlertTitle>{TITLES[problem.kind]}</AlertTitle>
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
