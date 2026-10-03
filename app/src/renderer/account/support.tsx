import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react';
import { Eye, EyeOff } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import type { FieldProblem } from '../../shared/accountRules.js';
import type { OperationResult } from '../../shared/api.js';
import { unreachable } from '../useOperation.js';
import { currentTranslator, type StringKey, type Translate } from './strings.js';

type Failure = Extract<OperationResult<never>, { ok: false }>;

/**
 * A failure in the user's language, from the CLI's machine-readable `reason` (or, for a
 * request this app refused, its kind). **Never the CLI's own text**: that carries the command
 * line, and so the address. One sentence per cause, none of them says whether an address is
 * registered (ADR-0029 SR-10).
 */
export function describeFailure(failure: Failure, t: Translate = currentTranslator()): string {
  const byReason = failure.reason === undefined ? undefined : (`error.${failure.reason}` as StringKey);
  const known: readonly StringKey[] = [
    'error.invalid_credentials', 'error.invalid_code', 'error.session_expired', 'error.not_signed_in',
    'error.rate_limited', 'error.unreachable', 'error.not_configured', 'error.headless', 'error.timeout',
    'error.oauth_failed', 'error.password_rejected', 'error.last_identity',
  ];
  if (byReason !== undefined && known.includes(byReason)) return t(byReason);
  if (failure.kind === 'refused' || failure.kind === 'usage') return t('error.refused');
  if (failure.kind === 'unavailable') return t('error.unavailable');
  if (failure.kind === 'timeout') return t('error.timeout');
  return t('error.generic');
}

export function fieldMessage(problem: FieldProblem, t: Translate = currentTranslator()): string {
  return t(`field.${problem}` as StringKey);
}

/**
 * Run one bridge call with a busy flag and a generic error line.
 *
 * `run` returns the data on success and `null` on failure (the error is then in `error`).
 * A rejected bridge call is shown like any other failure. The result's own `message`, `hint`
 * and `command` are deliberately never put on screen.
 */
export function useCall(t: Translate) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const live = useRef(true);
  // `live` only guards setState after the screen went away (a sign-in replaced it).
  useEffect(() => {
    live.current = true;
    return () => {
      live.current = false;
    };
  }, []);
  const mounted = useCallback((): boolean => live.current, []);

  const run = useCallback(
    async <T,>(call: () => Promise<OperationResult<T>>): Promise<T | null> => {
      setBusy(true);
      setError(null);
      let result: OperationResult<T>;
      try {
        result = await call();
      } catch (caught) {
        result = unreachable(caught);
      }
      if (!mounted()) return null;
      setBusy(false);
      if (!result.ok) {
        setError(describeFailure(result, t));
        return null;
      }
      return result.data;
    },
    [t, mounted],
  );

  return { busy, error, setError, run };
}

export function ErrorLine({ id, children }: { id?: string; children: string | null }) {
  if (children === null) return null;
  return (
    <p id={id} role="alert" className="text-sm text-destructive">
      {children}
    </p>
  );
}

/**
 * A labelled input. The error is announced and tied to the input; a secret field gets a
 * show/hide toggle and is never autofilled with anything but the platform's own manager.
 */
export function Field({
  id,
  label,
  value,
  onChange,
  t,
  type = 'text',
  secret = false,
  autoComplete,
  help,
  problem,
  disabled = false,
  inputMode,
  autoFocus = false,
  maxLength,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  t: Translate;
  type?: 'text' | 'email';
  secret?: boolean;
  autoComplete?: string | undefined;
  help?: string | undefined;
  /** Shown when set; the caller decides when (after a submit attempt, not while typing). */
  problem: FieldProblem | null;
  disabled?: boolean;
  inputMode?: 'numeric' | 'email' | 'text' | undefined;
  autoFocus?: boolean | undefined;
  maxLength?: number | undefined;
}) {
  const [shown, setShown] = useState(false);
  const helpId = `${id}-help`;
  const errorId = `${id}-error`;
  const describedBy = [help !== undefined ? helpId : null, problem !== null ? errorId : null].filter((x) => x !== null).join(' ');
  return (
    <div className="space-y-1.5">
      <Label htmlFor={id}>{label}</Label>
      <div className="flex gap-2">
        <Input
          id={id}
          type={secret && !shown ? 'password' : type}
          value={value}
          // Read-only rather than disabled while a call runs: a disabled input drops focus, so
          // after a failed submit the keyboard user would land on <body> instead of the field.
          readOnly={disabled}
          aria-disabled={disabled || undefined}
          className={disabled ? 'opacity-60' : undefined}
          autoComplete={autoComplete ?? 'off'}
          autoFocus={autoFocus}
          spellCheck={false}
          maxLength={maxLength}
          inputMode={inputMode}
          aria-invalid={problem !== null}
          aria-describedby={describedBy === '' ? undefined : describedBy}
          onChange={(event) => onChange(event.target.value)}
        />
        {secret ? (
          <Button
            type="button"
            variant="outline"
            size="icon"
            disabled={disabled}
            aria-pressed={shown}
            aria-label={shown ? t('field.hide') : t('field.show')}
            title={shown ? t('field.hide') : t('field.show')}
            onClick={() => setShown((was) => !was)}
          >
            {shown ? <EyeOff aria-hidden="true" /> : <Eye aria-hidden="true" />}
          </Button>
        ) : null}
      </div>
      {help !== undefined ? (
        <p id={helpId} className="text-xs text-muted-foreground">
          {help}
        </p>
      ) : null}
      {problem !== null ? (
        <p id={errorId} role="alert" className="text-sm text-destructive">
          {fieldMessage(problem, t)}
        </p>
      ) : null}
    </div>
  );
}

/** The initials avatar: decorative, the accessible name is carried by the button around it. */
export function Avatar({ initials, className = '' }: { initials: string; className?: string }) {
  return (
    <span
      aria-hidden="true"
      className={`inline-flex size-8 shrink-0 items-center justify-center rounded-full bg-primary text-xs font-semibold text-primary-foreground ${className}`}
    >
      {initials}
    </span>
  );
}

/** One titled block of the profile screen. */
export function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>
          <h3 className="text-base font-semibold">{title}</h3>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">{children}</CardContent>
    </Card>
  );
}
