import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Hint } from '@/components/ui/tooltip';
import { isWithheld, type Withheld } from './writeActionGating.js';
import type { EnvironmentReport } from '../shared/api.js';

/**
 * A write button that knows how to disable itself.
 *
 * Centralised so no row can forget the withheld check — item 5 of the brief is "the UI must
 * say why in plain language and must not present the action as available", and a button
 * that has to remember to ask `isWithheld` on its own is a button that eventually doesn't.
 */
export function WriteButton({
  command,
  environment,
  tooltip,
  children,
  ...props
}: {
  command: string;
  environment: EnvironmentReport | null;
  /** What the action does, shown on hover. A withheld reason replaces it — that is the more urgent fact. */
  tooltip?: string;
} & React.ComponentProps<typeof Button>) {
  // `environment === null` means the report has not arrived yet, not that nothing is
  // withheld — so it fails CLOSED. Reading an unanswered precondition as "no objection"
  // would enable every write action during the window before the app has checked whether
  // it could even write its own schema declaration, which is exactly the window in which
  // it must not write. The reason is worded as a wait, not a refusal, because it is one.
  const gate: Withheld =
    environment === null
      ? { withheld: true, reason: 'the app has not finished checking its own preconditions' }
      : isWithheld(environment.withheld, command);
  if (gate.withheld) {
    // The tooltip hangs on a wrapper, not on the button: a `disabled` button receives no
    // mouse events, so a tooltip on it is never triggered. The reason also goes into
    // `aria-label`, because a disabled control is not focusable and a tooltip a screen
    // reader never reaches is not an explanation. `EnvironmentBanner` in `App.tsx` states
    // the same reason once, visibly, for the sighted case — this is the per-control echo.
    return (
      <Hint content={`Withheld: ${gate.reason}`}>
        <span className="inline-flex">
          <Button
            {...props}
            disabled
            // The visible label when it is a plain string, and the CLI subcommand otherwise.
            // Not `String(children)`: a ReactNode stringifies to "[object Object]", which is
            // how a screen reader would have been told the reason.
            aria-label={`${typeof children === 'string' ? children : command} — withheld: ${gate.reason}`}
          >
            {children}
          </Button>
        </span>
      </Hint>
    );
  }
  const button = <Button {...props}>{children}</Button>;
  if (tooltip === undefined) return button;
  // Wrapped in a span for the same reason as above: while pending the button is disabled
  // and would otherwise swallow the hover that shows the tooltip.
  return (
    <Hint content={tooltip}>
      <span className="inline-flex">{button}</span>
    </Hint>
  );
}


/**
 * What a command said on stderr **while succeeding**.
 *
 * `OperationResult.notice` exists because the CLI uses stderr to tell the user something
 * the JSON payload has no field for — `bind` outside a git repository exits 0 with a
 * complete document and warns there that the bind artifacts were added to no ignore file,
 * which is how they get committed by accident. Rendering the payload alone would show a
 * clean success and drop exactly the sentence that mattered. Not `destructive`: the command
 * worked, and styling a warning as a failure teaches the user to ignore both.
 */
export function Notice({ result }: { result: { readonly ok: boolean; readonly notice?: string } }) {
  if (!result.ok || result.notice === undefined) return null;
  return (
    <Alert className="mt-2">
      <AlertTitle>The command succeeded and reported this</AlertTitle>
      <AlertDescription>
        <p className="whitespace-pre-wrap font-mono text-xs">{result.notice}</p>
      </AlertDescription>
    </Alert>
  );
}
