import { useCallback, useEffect, useState } from 'react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import type { DoctorReport, OperationResult } from '../../shared/api.js';
import { Problem } from '../Problem.js';
import { unreachable } from '../useOperation.js';
import { Busy, CommandBox, useFocusOnMount } from './CopyButton.js';
import { COPY } from './copy.js';
import { needsAttention } from './model.js';

type State =
  | { readonly phase: 'checking' }
  | { readonly phase: 'done'; readonly result: OperationResult<DoctorReport> };

/**
 * What the machine needs before the first task: git, Python and a provider (`doctor --machine`).
 *
 * Nothing is run without a click. A finding the CLI marked `auto_fixable` gets a "Fix" button
 * that asks the main process to run that finding's own command; any other finding that carries
 * a command (a provider's installer, say) shows it with a copy button and nothing more. When
 * nothing needs attention the step passes by itself, so it only costs the person a screen when
 * it has something to say.
 */
export function MachineStep({ onReady }: { onReady: () => void }) {
  const heading = useFocusOnMount<HTMLHeadingElement>();
  const [state, setState] = useState<State>({ phase: 'checking' });
  const [fixing, setFixing] = useState<number | null>(null);
  const [notes, setNotes] = useState<Readonly<Record<number, string>>>({});

  const check = useCallback(async () => {
    setState({ phase: 'checking' });
    let result: OperationResult<DoctorReport>;
    try {
      result = await window.devteam.doctorMachine();
    } catch (error) {
      result = unreachable(error);
    }
    setState({ phase: 'done', result });
  }, []);

  useEffect(() => {
    void check();
  }, [check]);

  const result = state.phase === 'done' ? state.result : null;
  const clear = result !== null && result.ok && !result.data.findings.some(needsAttention);
  useEffect(() => {
    if (clear) onReady();
  }, [clear, onReady]);

  async function fix(index: number) {
    setFixing(index);
    try {
      const answer = await window.devteam.runMachineFix(index);
      setNotes((previous) => ({ ...previous, [index]: answer.message }));
      if (answer.ran && answer.succeeded) await check();
    } catch (error) {
      setNotes((previous) => ({ ...previous, [index]: String(error) }));
    } finally {
      setFixing(null);
    }
  }

  return (
    <section aria-labelledby="machine-heading" className="flex flex-col gap-4">
      <h2 id="machine-heading" ref={heading} tabIndex={-1} className="text-lg font-semibold outline-hidden">
        {COPY.machine.heading}
      </h2>

      {result === null ? <Busy text={COPY.machine.checking} /> : null}

      {result !== null && !result.ok ? (
        <>
          <Problem problem={result} />
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => void check()}>
              {COPY.machine.recheck}
            </Button>
            <Button onClick={onReady}>{COPY.machine.continueAnyway}</Button>
          </div>
        </>
      ) : null}

      {result !== null && result.ok && !clear ? (
        <>
          <p>{COPY.machine.problems}</p>
          <ul className="flex flex-col gap-3">
            {result.data.findings.map((finding, index) =>
              needsAttention(finding) ? (
                <li key={`${finding.category}-${index}`}>
                  <Alert variant={finding.level === 'warn' ? 'default' : 'destructive'}>
                    <AlertTitle className="flex items-center gap-2">
                      <Badge variant="outline">{finding.category}</Badge>
                      {finding.message}
                    </AlertTitle>
                    <AlertDescription>
                      {finding.hint !== undefined ? <p>{finding.hint}</p> : null}
                      {finding.auto_fixable === true && finding.fix != null ? (
                        <div className="flex flex-wrap items-center gap-3">
                          <Button
                            size="sm"
                            aria-label={COPY.machine.fixLabel(finding.message)}
                            disabled={fixing !== null}
                            onClick={() => void fix(index)}
                          >
                            {fixing === index ? COPY.machine.fixing : COPY.machine.fix}
                          </Button>
                        </div>
                      ) : finding.fix != null ? (
                        <>
                          <p>{COPY.machine.installCommand}</p>
                          <CommandBox text={finding.fix} />
                        </>
                      ) : null}
                      {notes[index] !== undefined ? (
                        <p role="status" className="text-xs text-muted-foreground">
                          {notes[index]}
                        </p>
                      ) : null}
                    </AlertDescription>
                  </Alert>
                </li>
              ) : null,
            )}
          </ul>
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => void check()}>
              {COPY.machine.recheck}
            </Button>
            <Button onClick={onReady}>{COPY.machine.continueAnyway}</Button>
          </div>
        </>
      ) : null}

      {clear ? <p role="status">{COPY.machine.allGood}</p> : null}
    </section>
  );
}
