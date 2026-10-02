import { useEffect, useRef, useState, type FormEvent, type ReactNode } from 'react';
import { Loader2 } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  codeProblem,
  displayNameProblem,
  emailProblem,
  newPasswordProblem,
  normalizeEmail,
  signInPasswordProblem,
  type AuthProvider,
} from '../../shared/accountRules.js';
import type { AuthState, OperationResult } from '../../shared/api.js';
import { currentTranslator, type Translate } from './strings.js';
import { ErrorLine, Field, useCall } from './support.js';

type Step =
  | { readonly name: 'choose' }
  | { readonly name: 'otp-code'; readonly email: string }
  | { readonly name: 'signup-code'; readonly email: string }
  | { readonly name: 'forgot' }
  | { readonly name: 'forgot-code'; readonly email: string };

/**
 * Every way to sign in (ADR-0029): Google and GitHub in the system browser, an emailed code,
 * or email and password (with sign-up and a forgotten-password reset).
 *
 * The CLI owns the session; this screen only collects values and hands them to named
 * operations. Fields are validated on submit, not while typing, with the same rules the CLI
 * applies. Failures are generic sentences — never the CLI's text, never a hint about whether
 * an address is registered.
 */
export function SignIn({ onSignedIn }: { onSignedIn: (state: AuthState) => void }) {
  const t = currentTranslator();
  const [step, setStep] = useState<Step>({ name: 'choose' });

  // A password sign-up waiting for its code is remembered by the main process (the address
  // only). Leaving this screen in any way other than finishing forgets it.
  const signUpWaiting = useRef(false);
  useEffect(
    () => () => {
      if (signUpWaiting.current) void window.devteam.authPasswordSignUpCancel();
    },
    [],
  );
  const leaveSignUp = () => {
    if (signUpWaiting.current) void window.devteam.authPasswordSignUpCancel();
    signUpWaiting.current = false;
    setStep({ name: 'choose' });
  };

  return (
    <div className="mx-auto flex w-full max-w-md flex-col gap-4 py-6">
      <Card>
        {step.name === 'choose' ? (
          <Choose
            t={t}
            onSignedIn={onSignedIn}
            onCodeSent={(email) => setStep({ name: 'otp-code', email })}
            onSignUpSent={(email) => {
              signUpWaiting.current = true;
              setStep({ name: 'signup-code', email });
            }}
            onForgot={() => setStep({ name: 'forgot' })}
          />
        ) : step.name === 'otp-code' ? (
          <CodeStep
            t={t}
            title={t('signin.title')}
            lead={t('signin.codeSentTo', { email: step.email })}
            submitLabel={t('signin.verify')}
            backLabel={t('signin.useAnotherEmail')}
            onBack={() => setStep({ name: 'choose' })}
            onSubmit={(code) => window.devteam.authOtpVerify(step.email, code)}
            onDone={onSignedIn}
          />
        ) : step.name === 'signup-code' ? (
          <CodeStep
            t={t}
            title={t('signin.confirmEmail')}
            lead={t('signin.confirmLead', { email: step.email })}
            submitLabel={t('signin.confirm')}
            backLabel={t('signin.cancel')}
            onBack={leaveSignUp}
            onSubmit={(code) => window.devteam.authPasswordSignUpFinish(code)}
            onDone={(state) => {
              signUpWaiting.current = false;
              onSignedIn(state);
            }}
          />
        ) : step.name === 'forgot' ? (
          <Forgot t={t} onSent={(email) => setStep({ name: 'forgot-code', email })} onBack={() => setStep({ name: 'choose' })} />
        ) : (
          <ForgotCode t={t} email={step.email} onBack={() => setStep({ name: 'forgot' })} onDone={onSignedIn} />
        )}
      </Card>
    </div>
  );
}

function Heading({ title, description }: { title: string; description?: string }) {
  return (
    <CardHeader>
      <CardTitle>
        <h2 className="text-lg font-semibold">{title}</h2>
      </CardTitle>
      {description !== undefined ? <CardDescription>{description}</CardDescription> : null}
    </CardHeader>
  );
}

function Spinner({ label }: { label: string }) {
  return (
    <span className="inline-flex items-center gap-2">
      <Loader2 className="size-4 animate-spin" aria-hidden="true" />
      {label}
    </span>
  );
}

// ── the first step ────────────────────────────────────────────────────────────────

function Choose({
  t,
  onSignedIn,
  onCodeSent,
  onSignUpSent,
  onForgot,
}: {
  t: Translate;
  onSignedIn: (state: AuthState) => void;
  onCodeSent: (email: string) => void;
  onSignUpSent: (email: string) => void;
  onForgot: () => void;
}) {
  const [method, setMethod] = useState('code');
  const [signUp, setSignUp] = useState(false);
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [password, setPassword] = useState('');
  const [attempted, setAttempted] = useState(false);
  const [oauth, setOauth] = useState<AuthProvider | null>(null);
  const call = useCall(t);

  const emailIssue = attempted ? emailProblem(email) : null;
  const nameIssue = attempted && signUp && name.trim() !== '' ? displayNameProblem(name) : null;
  const passwordIssue = attempted ? (signUp ? newPasswordProblem(password) : signInPasswordProblem(password)) : null;

  async function signInWith(provider: AuthProvider) {
    setOauth(provider);
    const state = await call.run(() => window.devteam.authLoginOAuth(provider));
    setOauth(null);
    if (state !== null) onSignedIn(state);
  }

  async function sendCode(event: FormEvent) {
    event.preventDefault();
    setAttempted(true);
    if (emailProblem(email) !== null) return;
    const sent = await call.run(() => window.devteam.authOtpStart(normalizeEmail(email), null));
    if (sent !== null) onCodeSent(normalizeEmail(email));
  }

  async function submitPassword(event: FormEvent) {
    event.preventDefault();
    setAttempted(true);
    if (emailProblem(email) !== null) return;
    if (signUp) {
      if (newPasswordProblem(password) !== null) return;
      if (name.trim() !== '' && displayNameProblem(name) !== null) return;
      const started = await call.run(() =>
        window.devteam.authPasswordSignUpStart(normalizeEmail(email), password, name.trim() === '' ? null : name.trim()),
      );
      if (started !== null) {
        setPassword('');
        onSignUpSent(normalizeEmail(email));
      }
      return;
    }
    if (signInPasswordProblem(password) !== null) return;
    const state = await call.run(() => window.devteam.authPasswordSignIn(normalizeEmail(email), password));
    if (state !== null) onSignedIn(state);
  }

  const busy = call.busy;
  return (
    <>
      <Heading title={t('signin.title')} description={t('signin.lead')} />
      <CardContent className="space-y-5">
        <div className="grid gap-2">
          <Button variant="outline" disabled={busy} onClick={() => void signInWith('google')}>
            {t('signin.google')}
          </Button>
          <Button variant="outline" disabled={busy} onClick={() => void signInWith('github')}>
            {t('signin.github')}
          </Button>
          {oauth !== null ? (
            <p role="status" className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="size-4 animate-spin" aria-hidden="true" />
              {t('signin.browserWaiting')}
            </p>
          ) : null}
        </div>

        <div className="flex items-center gap-3 text-xs text-muted-foreground" aria-hidden="true">
          <span className="h-px flex-1 bg-border" />
          {t('signin.or')}
          <span className="h-px flex-1 bg-border" />
        </div>

        <Tabs
          value={method}
          onValueChange={(next) => {
            setMethod(next);
            setAttempted(false);
            call.setError(null);
          }}
        >
          <TabsList className="w-full">
            <TabsTrigger value="code">{t('signin.tabCode')}</TabsTrigger>
            <TabsTrigger value="password">{t('signin.tabPassword')}</TabsTrigger>
          </TabsList>

          <TabsContent value="code" className="pt-4">
            <form className="space-y-4" onSubmit={(event) => void sendCode(event)} noValidate>
              <Field
                id="signin-code-email"
                label={t('signin.email')}
                type="email"
                inputMode="email"
                autoComplete="email"
                value={email}
                onChange={setEmail}
                problem={emailIssue}
                disabled={busy}
                t={t}
              />
              <ErrorLine>{call.error}</ErrorLine>
              <Button type="submit" className="w-full" disabled={busy}>
                {busy && oauth === null ? <Spinner label={t('signin.working')} /> : t('signin.sendCode')}
              </Button>
            </form>
          </TabsContent>

          <TabsContent value="password" className="pt-4">
            <form className="space-y-4" onSubmit={(event) => void submitPassword(event)} noValidate>
              {signUp ? (
                <Field
                  id="signin-name"
                  label={t('signin.name')}
                  autoComplete="name"
                  value={name}
                  onChange={setName}
                  problem={nameIssue}
                  disabled={busy}
                  t={t}
                />
              ) : null}
              <Field
                id="signin-pw-email"
                label={t('signin.email')}
                type="email"
                inputMode="email"
                autoComplete="email"
                value={email}
                onChange={setEmail}
                problem={emailIssue}
                disabled={busy}
                t={t}
              />
              <Field
                id="signin-password"
                label={signUp ? t('signin.newPassword') : t('signin.password')}
                secret
                autoComplete={signUp ? 'new-password' : 'current-password'}
                help={signUp ? t('signin.passwordHelp') : undefined}
                value={password}
                onChange={setPassword}
                problem={passwordIssue}
                disabled={busy}
                t={t}
              />
              <ErrorLine>{call.error}</ErrorLine>
              <Button type="submit" className="w-full" disabled={busy}>
                {busy && oauth === null ? <Spinner label={t('signin.working')} /> : signUp ? t('signin.signUp') : t('signin.signIn')}
              </Button>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <Button
                  type="button"
                  variant="link"
                  size="sm"
                  className="h-auto p-0"
                  disabled={busy}
                  onClick={() => {
                    setSignUp((was) => !was);
                    setAttempted(false);
                    call.setError(null);
                  }}
                >
                  {signUp ? t('signin.haveAccount') : t('signin.createAccount')}
                </Button>
                {signUp ? null : (
                  <Button type="button" variant="link" size="sm" className="h-auto p-0" disabled={busy} onClick={onForgot}>
                    {t('signin.forgot')}
                  </Button>
                )}
              </div>
            </form>
          </TabsContent>
        </Tabs>
      </CardContent>
    </>
  );
}

// ── a code and nothing else ───────────────────────────────────────────────────────

function CodeStep({
  t,
  title,
  lead,
  submitLabel,
  backLabel,
  onBack,
  onSubmit,
  onDone,
  onFailed,
}: {
  t: Translate;
  title: string;
  lead: string;
  submitLabel: string;
  backLabel: string;
  onBack: () => void;
  onSubmit: (code: string) => Promise<OperationResult<AuthState>>;
  onDone: (state: AuthState) => void;
  onFailed?: () => void;
}) {
  const [code, setCode] = useState('');
  const [attempted, setAttempted] = useState(false);
  const call = useCall(t);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setAttempted(true);
    if (codeProblem(code) !== null) return;
    const state = await call.run(() => onSubmit(code));
    if (state !== null) onDone(state);
    else onFailed?.();
  }

  return (
    <>
      <Heading title={title} description={lead} />
      <CardContent>
        <form className="space-y-4" onSubmit={(event) => void submit(event)} noValidate>
          <Field
            id="signin-code"
            label={t('signin.code')}
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
          <ErrorLine>{call.error}</ErrorLine>
          <div className="flex flex-wrap gap-2">
            <Button type="submit" disabled={call.busy}>
              {call.busy ? <Spinner label={t('signin.working')} /> : submitLabel}
            </Button>
            <Button type="button" variant="ghost" disabled={call.busy} onClick={onBack}>
              {backLabel}
            </Button>
          </div>
        </form>
      </CardContent>
    </>
  );
}

// ── forgot password ───────────────────────────────────────────────────────────────

function Forgot({ t, onSent, onBack }: { t: Translate; onSent: (email: string) => void; onBack: () => void }) {
  const [email, setEmail] = useState('');
  const [attempted, setAttempted] = useState(false);
  const call = useCall(t);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setAttempted(true);
    if (emailProblem(email) !== null) return;
    const sent = await call.run(() => window.devteam.authPasswordResetStart(normalizeEmail(email)));
    if (sent !== null) onSent(normalizeEmail(email));
  }

  return (
    <>
      <Heading title={t('forgot.title')} description={t('forgot.lead')} />
      <CardContent>
        <form className="space-y-4" onSubmit={(event) => void submit(event)} noValidate>
          <Field
            id="forgot-email"
            label={t('signin.email')}
            type="email"
            inputMode="email"
            autoComplete="email"
            autoFocus
            value={email}
            onChange={setEmail}
            problem={attempted ? emailProblem(email) : null}
            disabled={call.busy}
            t={t}
          />
          <ErrorLine>{call.error}</ErrorLine>
          <div className="flex flex-wrap gap-2">
            <Button type="submit" disabled={call.busy}>
              {call.busy ? <Spinner label={t('signin.working')} /> : t('forgot.send')}
            </Button>
            <Button type="button" variant="ghost" disabled={call.busy} onClick={onBack}>
              {t('signin.back')}
            </Button>
          </div>
        </form>
      </CardContent>
    </>
  );
}

function ForgotCode({
  t,
  email,
  onBack,
  onDone,
}: {
  t: Translate;
  email: string;
  onBack: () => void;
  onDone: (state: AuthState) => void;
}): ReactNode {
  const [code, setCode] = useState('');
  const [password, setPassword] = useState('');
  const [attempted, setAttempted] = useState(false);
  const call = useCall(t);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setAttempted(true);
    if (codeProblem(code) !== null || newPasswordProblem(password) !== null) return;
    const state = await call.run(() => window.devteam.authPasswordResetFinish(email, code, password));
    if (state !== null) onDone(state);
  }

  return (
    <>
      <Heading title={t('forgot.title')} description={t('forgot.codeLead', { email })} />
      <CardContent>
        <form className="space-y-4" onSubmit={(event) => void submit(event)} noValidate>
          <Field
            id="forgot-code"
            label={t('signin.code')}
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
          <Field
            id="forgot-password"
            label={t('forgot.newPassword')}
            secret
            autoComplete="new-password"
            help={t('signin.passwordHelp')}
            value={password}
            onChange={setPassword}
            problem={attempted ? newPasswordProblem(password) : null}
            disabled={call.busy}
            t={t}
          />
          <ErrorLine>{call.error}</ErrorLine>
          <div className="flex flex-wrap gap-2">
            <Button type="submit" disabled={call.busy}>
              {call.busy ? <Spinner label={t('signin.working')} /> : t('forgot.finish')}
            </Button>
            <Button type="button" variant="ghost" disabled={call.busy} onClick={onBack}>
              {t('signin.back')}
            </Button>
          </div>
        </form>
      </CardContent>
    </>
  );
}
