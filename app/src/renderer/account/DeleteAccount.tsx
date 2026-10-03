import { useState, type FormEvent } from 'react';

import { Button } from '@/components/ui/button';
import { DELETE_CONFIRM_WORD, codeProblem } from '../../shared/accountRules.js';
import { currentTranslator } from './strings.js';
import { ErrorLine, Field, Section, useCall } from './support.js';

/**
 * Deleting is three deliberate steps: reveal the form, type the confirmation word, and enter
 * the fresh code the CLI emails (the server insists on a recent sign-in). Nothing is sent to
 * the CLI before the word matches, and the code is only ever sent with the delete itself.
 */
export function DeleteAccount({ onDeleted }: { onDeleted: () => void }) {
  const t = currentTranslator();
  const [open, setOpen] = useState(false);
  const [word, setWord] = useState('');
  const [sent, setSent] = useState(false);
  const [code, setCode] = useState('');
  const [attempted, setAttempted] = useState(false);
  const call = useCall(t);

  const confirmed = word.trim().toLowerCase() === DELETE_CONFIRM_WORD;

  function close() {
    setOpen(false);
    setWord('');
    setSent(false);
    setCode('');
    setAttempted(false);
    call.setError(null);
  }

  async function sendCode() {
    if (!confirmed) return;
    const done = await call.run(() => window.devteam.authDeleteStart());
    if (done !== null) setSent(true);
  }

  async function deleteNow(event: FormEvent) {
    event.preventDefault();
    // Enter on the first step (the typed word) means "send the code", not a silent no-op.
    if (!sent) {
      await sendCode();
      return;
    }
    setAttempted(true);
    if (!confirmed || codeProblem(code) !== null) return;
    const done = await call.run(() => window.devteam.authDeleteConfirm(code));
    // The code is spent either way; an emptied field must not read as a validation error.
    setCode('');
    setAttempted(false);
    if (done !== null) {
      close();
      onDeleted();
    }
  }

  return (
    <Section title={t('delete.title')}>
      <p className="text-sm text-muted-foreground">{t('delete.lead')}</p>
      {!open ? (
        <Button variant="destructive" size="sm" onClick={() => setOpen(true)}>
          {t('delete.start')}
        </Button>
      ) : (
        <form className="space-y-3" onSubmit={(event) => void deleteNow(event)} noValidate>
          <Field
            id="delete-word"
            label={t('delete.confirmWord', { word: DELETE_CONFIRM_WORD })}
            autoFocus
            value={word}
            onChange={setWord}
            problem={null}
            disabled={call.busy || sent}
            t={t}
          />
          {sent ? (
            <>
              <p role="status" className="text-sm text-muted-foreground">
                {t('delete.codeSent')}
              </p>
              <Field
                id="delete-code"
                label={t('delete.code')}
                help={t('signin.codeHelp')}
                inputMode="numeric"
                autoComplete="one-time-code"
                autoFocus
                value={code}
                onChange={setCode}
                problem={attempted ? codeProblem(code) : null}
                disabled={call.busy}
                t={t}
              />
            </>
          ) : null}
          <ErrorLine>{call.error}</ErrorLine>
          <div className="flex flex-wrap gap-2">
            {sent ? (
              <Button type="submit" variant="destructive" disabled={call.busy || !confirmed}>
                {t('delete.confirm')}
              </Button>
            ) : (
              <Button type="button" variant="destructive" disabled={call.busy || !confirmed} onClick={() => void sendCode()}>
                {t('delete.sendCode')}
              </Button>
            )}
            <Button type="button" variant="ghost" disabled={call.busy} onClick={close}>
              {t('delete.cancel')}
            </Button>
          </div>
        </form>
      )}
    </Section>
  );
}
