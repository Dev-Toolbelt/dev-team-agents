import { Button } from '@/components/ui/button';
import { initialsOf } from '../../shared/accountRules.js';
import { useAccount } from './AccountContext.js';
import { currentTranslator } from './strings.js';
import { Avatar } from './support.js';

/**
 * The header's account control: the person's initials (never a picture: the renderer's CSP
 * is `img-src 'self' data:` and the app makes no network request of its own), opening the
 * Account tab. Signed out, a plain "Sign in" button; when the check failed, a neutral
 * "Account" one. Renders nothing until the first answer.
 */
export function AccountMenu({ onOpen }: { onOpen: () => void }) {
  const t = currentTranslator();
  const { state, view } = useAccount();
  if (view.kind === 'loading') return null;
  // The check failed (a timeout, no account server): the person may well be signed in, so
  // offer the Account tab without claiming either way.
  if (view.kind === 'unknown') {
    return (
      <Button variant="outline" size="sm" onClick={onOpen}>
        {t('account.tab')}
      </Button>
    );
  }
  if (state === null) {
    return (
      <Button variant="outline" size="sm" onClick={onOpen}>
        {t('account.signedOutAvatar')}
      </Button>
    );
  }
  const name = state.account?.display_name ?? null;
  const email = state.account?.email ?? null;
  const who = name ?? email ?? t('account.tab');
  return (
    <Button variant="ghost" size="sm" className="h-auto gap-2 px-1.5 py-1" aria-label={t('account.avatar', { who })} title={who} onClick={onOpen}>
      <Avatar initials={initialsOf(name, email)} />
    </Button>
  );
}
