import { useState } from 'react';
import { CheckCircle2, Info, Loader2, XCircle } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Hint } from '@/components/ui/tooltip';
import type { PluginAction, PluginRunResult, ProjectRecord } from '../../shared/api.js';
import { Problem } from '../Problem.js';
import { useAction } from '../useOperation.js';

export function formatDuration(ms: number): string {
  return ms < 1000 ? `${Math.round(ms)} ms` : `${(ms / 1000).toFixed(1)} s`;
}

/**
 * One button per manifest action, and its result.
 *
 * What the result means depends only on the action's declared `output`: `config` answers are
 * handed to `onProposal` to fill the form's draft (never saved from here), `json` is shown
 * as text, `log` as a collapsible tail. A script that exited non-zero arrives as a normal
 * answer with `ok: false` and is shown as a failure with its tail — it is not a CLI error.
 */
export function ActionRow({
  projectId,
  pluginName,
  action,
  disabledReason,
  onProposal,
  onRan,
}: {
  projectId: ProjectRecord['project_id'];
  pluginName: string;
  action: PluginAction;
  /** Why the button cannot be used right now, or `null`. */
  disabledReason: string | null;
  /** Fill the form with a `config` action's answer; returns the sentence to show. */
  onProposal: (output: Readonly<Record<string, unknown>>) => string;
  /** The action may have changed what the card shows (status, built files); reload it. */
  onRan: () => void;
}) {
  const runner = useAction(() => window.devteam.runPluginAction(projectId, pluginName, action.id));
  const [notice, setNotice] = useState<string | null>(null);
  const pending = runner.state.phase === 'pending';
  const result = runner.state.phase === 'done' ? runner.state.result : null;
  const idle = disabledReason === null && !pending;

  async function click() {
    setNotice(null);
    const answer = await runner.run();
    if (!answer.ok) return;
    if (action.output === 'config' && answer.data.ok) {
      setNotice(answer.data.output === null ? 'The action proposed nothing.' : onProposal(answer.data.output));
    }
    if (action.output !== 'config' || action.writes) onRan();
  }

  const button = (
    <Button type="button" variant="outline" size="sm" disabled={!idle} aria-describedby={`${pluginName}-${action.id}-help`} onClick={() => void click()}>
      {pending ? <Loader2 className="animate-spin" aria-hidden="true" /> : null}
      {pending ? 'Running…' : action.label}
    </Button>
  );

  return (
    <div className="space-y-2 py-3">
      <div className="flex flex-wrap items-center gap-3">
        {disabledReason !== null ? (
          <Hint content={disabledReason}>
            <span className="inline-flex">{button}</span>
          </Hint>
        ) : (
          button
        )}
        {action.help !== null ? (
          <p id={`${pluginName}-${action.id}-help`} className="min-w-0 flex-1 text-xs text-muted-foreground">
            {action.help}
          </p>
        ) : null}
      </div>
      {disabledReason !== null ? <p className="text-xs italic text-muted-foreground">{disabledReason}</p> : null}

      <p aria-live="polite" className="sr-only">
        {pending
          ? `Running ${action.label}…`
          : result !== null && result.ok
            ? `${action.label} ${result.data.ok ? 'finished' : 'failed'}.`
            : ''}
      </p>

      {result !== null && !result.ok ? <Problem problem={result} /> : null}
      {result !== null && result.ok ? <Outcome action={action} run={result.data} /> : null}
      {notice !== null ? (
        <div role="status" className="flex items-start gap-2 rounded-md border bg-muted/50 px-3 py-2 text-sm">
          <Info className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
          {notice}
        </div>
      ) : null}
    </div>
  );
}

function Outcome({ action, run }: { action: PluginAction; run: PluginRunResult }) {
  const json = action.output === 'json' && run.output !== null ? JSON.stringify(run.output, null, 2) : null;
  const text = json ?? run.log_tail;
  const summary = json !== null ? 'Result' : 'Output';
  return (
    <div className="space-y-1.5 text-sm">
      <div className="flex flex-wrap items-center gap-2">
        {run.ok ? (
          <Badge variant="outline" className="gap-1 border-green-600 text-green-800 dark:text-green-300">
            <CheckCircle2 className="size-3.5" aria-hidden="true" />
            Succeeded
          </Badge>
        ) : (
          <Badge variant="destructive" className="gap-1">
            <XCircle className="size-3.5" aria-hidden="true" />
            Failed (exit {run.exit_code})
          </Badge>
        )}
        <span className="text-xs text-muted-foreground">{formatDuration(run.duration_ms)}</span>
      </div>
      {text.trim() !== '' ? (
        <details open={!run.ok} className="rounded-md border">
          <summary className="cursor-pointer px-3 py-1.5 text-xs font-medium">{summary}</summary>
          <pre className="max-h-72 overflow-auto border-t bg-muted/40 px-3 py-2 font-mono text-xs whitespace-pre-wrap">{text}</pre>
        </details>
      ) : null}
    </div>
  );
}
