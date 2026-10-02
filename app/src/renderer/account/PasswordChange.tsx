import { useState, type FormEvent } from 'react';

import { Button } from '@/components/ui/button';
import { newPasswordProblem, signInPasswordProblem } from '../../shared/accountRules.js';
import { currentTranslator } from './strings.js';
import { ErrorLine, Field, Section, useCall } from './support.js';

/** Current password, then the new one; both are cleared as soon as the call returns. */
export function PasswordChange() {
  const t = currentTranslator();
  const [open, setOpen] = useState(false);
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [attempted, setAttempted] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const call = useCall(t);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setAttempted(true);
    if (signInPasswordProblem(current) !== null || newPasswordProblem(next) !== null) return;
    setMessage(null);
    const done = await call.run(() => window.devteam.authPasswordChange(current, next));
    setCurrent('');
    setNext('');
    // Emptied on purpose; it must not read as a validation error.
    setAttempted(false);
    if (done !== null) {
      setOpen(false);
      setMessage(done.other_sessions_revoked ? t('profile.passwordChanged') : t('profile.passwordChangedPartial'));
    }
  }

  return (
    <Section title={t('profile.password')}>
      {message !== null ? (
        <p role="status" className="text-sm text-muted-foreground">
          {message}
        </p>
      ) : null}
      {!open ? (
        <Button variant="outline" size="sm" onClick={() => setOpen(true)}>
          {t('profile.changePassword')}
        </Button>
      ) : (
        <form className="space-y-3" onSubmit={(event) => void submit(event)} noValidate>
          <Field
            id="password-current"
            label={t('profile.currentPassword')}
            secret
            autoComplete="current-password"
            autoFocus
            value={current}
            onChange={setCurrent}
            problem={attempted ? signInPasswordProblem(current) : null}
            disabled={call.busy}
            t={t}
          />
          <Field
            id="password-new"
            label={t('profile.newPassword')}
            secret
            autoComplete="new-password"
            help={t('signin.passwordHelp')}
            value={next}
            onChange={setNext}
            problem={attempted ? newPasswordProblem(next) : null}
            disabled={call.busy}
            t={t}
          />
          <ErrorLine>{call.error}</ErrorLine>
          <div className="flex gap-2">
            <Button type="submit" disabled={call.busy}>
              {t('profile.changePassword')}
            </Button>
            <Button
              type="button"
              variant="ghost"
              disabled={call.busy}
              onClick={() => {
                setOpen(false);
                setCurrent('');
                setNext('');
                setAttempted(false);
                call.setError(null);
              }}
            >
              {t('signin.cancel')}
            </Button>
          </div>
        </form>
      )}
    </Section>
  );
}
