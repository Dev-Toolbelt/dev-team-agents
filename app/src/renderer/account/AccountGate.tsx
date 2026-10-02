import { useState, type ReactNode } from 'react';
import { CircleAlert, X } from 'lucide-react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { useAccount } from './AccountContext.js';
import { Blocked, blockedReason, type BlockedReason } from './Blocked.js';
import { SignIn } from './SignIn.js';
import { currentTranslator, type StringKey } from './strings.js';

/**
 * Accounts are mandatory (ADR-0029): when `auth check` says the account is not entitled the
 * app shows only the account screens. The CLI's `gate_mode` decides how hard that is:
 *
 *  - `enforce` — only the sign-in screen (signed out) or the blocked screen replace the app;
 *  - `warn` — the app stays usable under a dismissible banner that says what is wrong.
 *
 * While the first answer is pending nothing of the app is shown either, so a signed-out
 * person never sees a flash of a screen they may not use.
 */
export function AccountGate({ children, onOpenAccount }: { children: ReactNode; onOpenAccount: () => void }) {
  const t = currentTranslator();
  const account = useAccount();
  const [dismissed, setDismissed] = useState<string | null>(null);
  const { view } = account;

  if (view.kind === 'loading') {
    return (
      <p role="status" className="py-8 text-sm text-muted-foreground">
        {t('account.loading')}
      </p>
    );
  }
  if (view.kind === 'entitled') return <>{children}</>;

  const reason: BlockedReason = view.kind === 'unknown' ? 'error' : blockedReason(view.status);

  if (account.mode === 'enforce') {
    return reason === 'signed_out' ? <SignIn onSignedIn={account.apply} /> : <Blocked reason={reason} />;
  }

  return (
    <>
      {dismissed === reason ? null : (
        <Alert className="mb-4" variant="destructive">
          <CircleAlert />
          <AlertTitle>{t(`banner.title.${reason}` as StringKey)}</AlertTitle>
          <AlertDescription>
            <p>{t('banner.body')}</p>
            <div className="flex flex-wrap items-center gap-2">
              <Button size="sm" variant="outline" onClick={onOpenAccount}>
                {reason === 'signed_out' ? t('banner.signIn') : t('banner.open')}
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setDismissed(reason)}>
                <X aria-hidden="true" />
                {t('banner.dismiss')}
              </Button>
            </div>
          </AlertDescription>
        </Alert>
      )}
      {children}
    </>
  );
}
