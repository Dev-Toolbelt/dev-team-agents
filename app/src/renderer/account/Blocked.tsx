import { CircleAlert, Loader2 } from 'lucide-react';
import { useState } from 'react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { EntitlementStatus } from '../../shared/api.js';
import { useAccount } from './AccountContext.js';
import { currentTranslator, type StringKey } from './strings.js';
import { ErrorLine, useCall } from './support.js';

/** The reasons the account can be blocked with a message of their own; anything else reads as `error`. */
export type BlockedReason = Exclude<EntitlementStatus, 'active' | 'trial'> | 'error';

export function blockedReason(status: EntitlementStatus | 'error'): BlockedReason {
  return status === 'active' || status === 'trial' ? 'invalid' : status;
}

/**
 * The account is not entitled (trial ended, banned, no online check possible, an invalid
 * licence) or could not be checked. It states why in one plain sentence, offers the one thing
 * that can change the answer (check again) and a way out (sign out), and says the person's
 * projects are untouched. It is shown alone when the gate enforces; see `AccountGate`.
 */
export function Blocked({ reason }: { reason: BlockedReason }) {
  const t = currentTranslator();
  const account = useAccount();
  const call = useCall(t);
  const [checking, setChecking] = useState(false);
  const who = account.state?.account?.email ?? account.state?.account?.id ?? null;

  async function check() {
    setChecking(true);
    await account.refresh();
    setChecking(false);
  }

  async function signOut() {
    const done = await call.run(() => window.devteam.authLogout());
    if (done !== null) await account.refresh();
  }

  return (
    <div className="mx-auto flex w-full max-w-md flex-col gap-4 py-6">
      <Card>
        <CardHeader>
          <CardTitle>
            <h2 className="flex items-center gap-2 text-lg font-semibold">
              <CircleAlert className="size-5 text-destructive" aria-hidden="true" />
              {t(`blocked.title.${reason}` as StringKey)}
            </h2>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm">{t(`blocked.body.${reason}` as StringKey)}</p>
          {reason === 'signed_out' ? null : <p className="text-sm">{t('blocked.untouched')}</p>}
          {who !== null ? <p className="text-sm text-muted-foreground">{t('blocked.signedInAs', { who })}</p> : null}
          <ErrorLine>{call.error}</ErrorLine>
          <div className="flex flex-wrap gap-2">
            <Button onClick={() => void check()} disabled={checking || call.busy}>
              {checking ? (
                <span className="inline-flex items-center gap-2">
                  <Loader2 className="size-4 animate-spin" aria-hidden="true" />
                  {t('signin.working')}
                </span>
              ) : (
                t('blocked.check')
              )}
            </Button>
            {account.state !== null ? (
              <Button variant="outline" onClick={() => void signOut()} disabled={checking || call.busy}>
                {t('blocked.signOut')}
              </Button>
            ) : null}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
