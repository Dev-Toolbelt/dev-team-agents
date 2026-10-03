import { useState, type FormEvent } from 'react';

import { Button } from '@/components/ui/button';
import { codeProblem, emailProblem, normalizeEmail } from '../../shared/accountRules.js';
import { currentTranslator } from './strings.js';
import { ErrorLine, Field, Section, useCall } from './support.js';

/**
 * Changing the address takes two steps: the new address, then the code sent to it (and, when
 * the server also mailed the old address, that code too — optional here). Neither value is
 * kept after the call that carries it.
 */
export function EmailChange({
  email,
  pending,
  onChanged,
}: {
  email: string | null;
  pending: string | null;
  onChanged: () => void;
}) {
  const t = currentTranslator();
  const [open, setOpen] = useState(false);
  const [target, setTarget] = useState<string | null>(null);
  const [newEmail, setNewEmail] = useState('');
  const [codeNew, setCodeNew] = useState('');
  const [codeCurrent, setCodeCurrent] = useState('');
  const [attempted, setAttempted] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const call = useCall(t);

  function reset() {
    setOpen(false);
    setTarget(null);
    setNewEmail('');
    setCodeNew('');
    setCodeCurrent('');
    setAttempted(false);
    setMessage(null);
    call.setError(null);
  }

  async function start(event: FormEvent) {
    event.preventDefault();
    setAttempted(true);
    if (emailProblem(newEmail) !== null) return;
    setMessage(null);
    const sent = await call.run(() => window.devteam.authEmailChangeStart(normalizeEmail(newEmail)));
    if (sent !== null) {
      setTarget(normalizeEmail(newEmail));
      setAttempted(false);
    }
  }

  async function confirm(event: FormEvent) {
    event.preventDefault();
    setAttempted(true);
    const second = codeCurrent.trim() === '' ? null : codeCurrent;
    if (target === null || codeProblem(codeNew) !== null || (second !== null && codeProblem(second) !== null)) return;
    const done = await call.run(() => window.devteam.authEmailChangeConfirm(target, codeNew, second));
    if (done === null) return;
    if (done.confirmed) {
      reset();
      setMessage(t('profile.emailChanged'));
      onChanged();
    } else {
      setCodeNew('');
      setAttempted(false);
      setMessage(t('profile.emailWaiting'));
    }
  }

  return (
    <Section title={t('profile.email')}>
      <p className="text-sm">{email ?? '—'}</p>
      {pending !== null && target === null ? (
        <p className="text-sm text-muted-foreground">{t('profile.pendingEmail', { email: pending })}</p>
      ) : null}
      {message !== null ? (
        <p role="status" className="text-sm text-muted-foreground">
          {message}
        </p>
      ) : null}
      {!open ? (
        <Button variant="outline" size="sm" onClick={() => setOpen(true)}>
          {t('profile.changeEmail')}
        </Button>
      ) : target === null ? (
        <form className="space-y-3" onSubmit={(event) => void start(event)} noValidate>
          <Field
            id="email-change-new"
            label={t('profile.newEmail')}
            type="email"
            inputMode="email"
            autoComplete="email"
            autoFocus
            value={newEmail}
            onChange={setNewEmail}
            problem={attempted ? emailProblem(newEmail) : null}
            disabled={call.busy}
            t={t}
          />
          <ErrorLine>{call.error}</ErrorLine>
          <div className="flex gap-2">
            <Button type="submit" disabled={call.busy}>
              {t('signin.sendCode')}
            </Button>
            <Button type="button" variant="ghost" disabled={call.busy} onClick={reset}>
              {t('signin.cancel')}
            </Button>
          </div>
        </form>
      ) : (
        <form className="space-y-3" onSubmit={(event) => void confirm(event)} noValidate>
          <p className="text-sm text-muted-foreground">{t('profile.emailSent', { email: target })}</p>
          <Field
            id="email-change-code-new"
            label={t('profile.codeNew')}
            help={t('signin.codeHelp')}
            inputMode="numeric"
            autoComplete="one-time-code"
            autoFocus
            value={codeNew}
            onChange={setCodeNew}
            problem={attempted ? codeProblem(codeNew) : null}
            disabled={call.busy}
            t={t}
          />
          <Field
            id="email-change-code-current"
            label={t('profile.codeCurrent')}
            inputMode="numeric"
            autoComplete="one-time-code"
            value={codeCurrent}
            onChange={setCodeCurrent}
            problem={attempted && codeCurrent.trim() !== '' ? codeProblem(codeCurrent) : null}
            disabled={call.busy}
            t={t}
          />
          <ErrorLine>{call.error}</ErrorLine>
          <div className="flex gap-2">
            <Button type="submit" disabled={call.busy}>
              {t('profile.confirmEmail')}
            </Button>
            <Button type="button" variant="ghost" disabled={call.busy} onClick={reset}>
              {t('signin.cancel')}
            </Button>
          </div>
        </form>
      )}
    </Section>
  );
}
