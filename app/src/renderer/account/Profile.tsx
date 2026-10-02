import { useState, type FormEvent } from 'react';
import { Loader2, ShieldAlert } from 'lucide-react';
import { toast } from 'sonner';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { displayNameProblem, initialsOf, type AuthProvider } from '../../shared/accountRules.js';
import type { AuthIdentity, AuthProfile, AuthState } from '../../shared/api.js';
import { unreachable, useOperation } from '../useOperation.js';
import { useAccount } from './AccountContext.js';
import { Blocked } from './Blocked.js';
import { DeleteAccount } from './DeleteAccount.js';
import { EmailChange } from './EmailChange.js';
import { PasswordChange } from './PasswordChange.js';
import { SignIn } from './SignIn.js';
import { currentLocale, currentTranslator, type Translate } from './strings.js';
import { Avatar, ErrorLine, Field, Section, describeFailure, useCall } from './support.js';

const PROVIDER_LABEL: Readonly<Record<string, string>> = { google: 'Google', github: 'GitHub', email: 'Email' };
const LINKABLE: readonly AuthProvider[] = ['google', 'github'];
const providerLabel = (provider: string): string => PROVIDER_LABEL[provider] ?? provider;

/**
 * The Account tab. Signed out it is the sign-in screen (so the banner of `warn` mode has
 * somewhere to go); signed in it is the profile: display name, email change, linked
 * providers, password, sign-out and account deletion. Every action is one named operation;
 * nothing here ever holds a token.
 */
export function Profile() {
  const account = useAccount();
  if (account.view.kind === 'loading') return null;
  if (account.view.kind === 'unknown') return <Blocked reason="error" />;
  if (account.state === null) return <SignIn onSignedIn={account.apply} />;
  return <SignedIn state={account.state} />;
}

function SignedIn({ state }: { state: AuthState }) {
  const t = currentTranslator();
  const account = useAccount();
  const profile = useOperation<AuthProfile>(() => window.devteam.authProfileGet().catch(unreachable), []);
  const out = useCall(t);

  const name = state.account?.display_name ?? null;
  const email = state.account?.email ?? null;

  async function signOut() {
    const done = await out.run(() => window.devteam.authLogout());
    if (done !== null) {
      toast.success(t('profile.signedOut'));
      await account.refresh();
    }
  }

  return (
    <section aria-labelledby="account-heading" className="mx-auto max-w-2xl space-y-4">
      <header className="flex items-center gap-3">
        <Avatar initials={initialsOf(name, email)} className="size-10 text-sm" />
        <div className="min-w-0">
          <h2 id="account-heading" className="truncate text-lg font-semibold">
            {name ?? email ?? t('profile.title')}
          </h2>
          {name !== null && email !== null ? <p className="truncate text-sm text-muted-foreground">{email}</p> : null}
        </div>
        <LicenseBadge state={state} t={t} />
      </header>

      {state.secret_backend_insecure ? (
        <Alert variant="destructive">
          <ShieldAlert />
          <AlertDescription>{t('profile.insecureStore')}</AlertDescription>
        </Alert>
      ) : null}

      {profile.state.phase === 'loading' ? (
        <p role="status" className="flex items-center gap-2 py-4 text-sm text-muted-foreground">
          <Loader2 className="size-4 animate-spin" aria-hidden="true" />
          {t('signin.working')}
        </p>
      ) : !profile.state.result.ok ? (
        <div className="space-y-3">
          <ErrorLine>{`${t('profile.loadFailed')} ${describeFailure(profile.state.result, t)}`}</ErrorLine>
          <Button variant="outline" size="sm" onClick={profile.reload}>
            {t('profile.retry')}
          </Button>
        </div>
      ) : (
        <ProfileSections
          t={t}
          profile={profile.state.result.data}
          onChanged={() => {
            profile.reload();
            void account.refresh();
          }}
        />
      )}

      <Section title={t('profile.signOut')}>
        <ErrorLine>{out.error}</ErrorLine>
        <Button variant="outline" disabled={out.busy} onClick={() => void signOut()}>
          {t('profile.signOut')}
        </Button>
      </Section>

      <DeleteAccount
        onDeleted={() => {
          toast.success(t('delete.done'));
          void account.refresh();
        }}
      />
    </section>
  );
}

function LicenseBadge({ state, t }: { state: AuthState; t: Translate }) {
  const { status, trial_ends_at: ends } = state.entitlement;
  if (status !== 'active' && status !== 'trial') return null;
  const date = ends === null ? null : new Date(ends * 1000).toLocaleDateString(currentLocale());
  return (
    <span className="ml-auto flex flex-col items-end gap-0.5">
      <Badge variant={status === 'active' ? 'default' : 'secondary'}>
        {status === 'active' ? t('profile.license.active') : t('profile.license.trial')}
      </Badge>
      {status === 'trial' && date !== null ? <span className="text-xs text-muted-foreground">{t('profile.license.trialEnds', { date })}</span> : null}
    </span>
  );
}

function ProfileSections({ t, profile, onChanged }: { t: Translate; profile: AuthProfile; onChanged: () => void }) {
  const hasPassword = profile.identities.some((identity) => identity.provider === 'email');
  return (
    <>
      <NameForm t={t} initial={profile.display_name ?? ''} onSaved={onChanged} />
      <EmailChange email={profile.email} pending={profile.pending_email} onChanged={onChanged} />
      <Identities t={t} identities={profile.identities} onChanged={onChanged} />
      {hasPassword ? <PasswordChange /> : null}
    </>
  );
}

function NameForm({ t, initial, onSaved }: { t: Translate; initial: string; onSaved: () => void }) {
  const [name, setName] = useState(initial);
  const [attempted, setAttempted] = useState(false);
  const [saved, setSaved] = useState(false);
  const call = useCall(t);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setAttempted(true);
    setSaved(false);
    if (displayNameProblem(name) !== null) return;
    const done = await call.run(() => window.devteam.authProfileUpdate(name));
    if (done !== null) {
      setSaved(true);
      onSaved();
    }
  }

  return (
    <Section title={t('profile.name')}>
      <form className="space-y-3" onSubmit={(event) => void submit(event)} noValidate>
        <Field
          id="profile-name"
          label={t('profile.name')}
          autoComplete="name"
          value={name}
          onChange={(value) => {
            setName(value);
            setSaved(false);
          }}
          problem={attempted ? displayNameProblem(name) : null}
          disabled={call.busy}
          t={t}
        />
        <ErrorLine>{call.error}</ErrorLine>
        {saved ? (
          <p role="status" className="text-sm text-muted-foreground">
            {t('profile.nameSaved')}
          </p>
        ) : null}
        <Button type="submit" disabled={call.busy}>
          {t('profile.saveName')}
        </Button>
      </form>
    </Section>
  );
}

function Identities({ t, identities, onChanged }: { t: Translate; identities: readonly AuthIdentity[]; onChanged: () => void }) {
  const call = useCall(t);
  const [working, setWorking] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const linked = new Set(identities.map((identity) => identity.provider));
  const onlyOne = identities.length <= 1;

  async function link(provider: AuthProvider) {
    setWorking(`link-${provider}`);
    setNotice(null);
    const done = await call.run(() => window.devteam.authIdentityLink(provider));
    setWorking(null);
    if (done !== null) {
      setNotice(t('profile.linked', { provider: providerLabel(provider) }));
      onChanged();
    }
  }

  async function unlink(provider: AuthProvider) {
    setWorking(`unlink-${provider}`);
    setNotice(null);
    const done = await call.run(() => window.devteam.authIdentityUnlink(provider));
    setWorking(null);
    if (done !== null) {
      setNotice(t('profile.unlinked', { provider: providerLabel(provider) }));
      onChanged();
    }
  }

  return (
    <Section title={t('profile.identities')}>
      <ul className="space-y-2">
        {identities.map((identity) => (
          <li key={`${identity.provider}-${identity.id ?? ''}`} className="flex flex-wrap items-center gap-2 text-sm">
            <span className="font-medium">{providerLabel(identity.provider)}</span>
            {identity.email !== null ? <span className="text-muted-foreground">{identity.email}</span> : null}
            {LINKABLE.includes(identity.provider as AuthProvider) ? (
              <Button
                variant="outline"
                size="sm"
                className="ml-auto"
                disabled={call.busy || onlyOne}
                title={onlyOne ? t('error.last_identity') : undefined}
                onClick={() => void unlink(identity.provider as AuthProvider)}
              >
                {working === `unlink-${identity.provider}` ? <Loader2 className="animate-spin" aria-hidden="true" /> : null}
                {t('profile.unlink', { provider: providerLabel(identity.provider) })}
              </Button>
            ) : null}
          </li>
        ))}
      </ul>
      <div className="flex flex-wrap gap-2">
        {LINKABLE.filter((provider) => !linked.has(provider)).map((provider) => (
          <Button key={provider} variant="outline" size="sm" disabled={call.busy} onClick={() => void link(provider)}>
            {working === `link-${provider}` ? <Loader2 className="animate-spin" aria-hidden="true" /> : null}
            {t('profile.link', { provider: providerLabel(provider) })}
          </Button>
        ))}
      </div>
      {working?.startsWith('link-') ? (
        <p role="status" className="text-sm text-muted-foreground">
          {t('signin.browserWaiting')}
        </p>
      ) : null}
      <ErrorLine>{call.error}</ErrorLine>
      {notice !== null ? (
        <p role="status" className="text-sm text-muted-foreground">
          {notice}
        </p>
      ) : null}
    </Section>
  );
}
