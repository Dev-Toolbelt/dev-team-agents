import type { AuthedUser } from "./types.ts";

export const REAUTH_WINDOW_SECONDS = 300;
const FUTURE_TOLERANCE_SECONDS = 60;

/** The method SR-37 requires for a destructive step: a code sent to the account's email. */
export const REAUTH_METHOD = "otp";

/**
 * The newest sign-in on this session must be an email code, made in the last five minutes
 * (SR-37). A fresh password or OAuth sign-in does not count: a stolen session that links the
 * attacker's own provider would otherwise get a fresh entry and delete the account.
 */
export function isFreshlyAuthenticated(user: AuthedUser, now: Date): boolean {
  const nowSec = Math.floor(now.getTime() / 1000);
  const entries = user.amr.filter((e) => Number.isFinite(e.timestamp));
  if (entries.length === 0) return false;
  const newest = entries.reduce((a, b) => (b.timestamp > a.timestamp ? b : a));
  return (
    newest.method === REAUTH_METHOD &&
    newest.timestamp <= nowSec + FUTURE_TOLERANCE_SECONDS &&
    nowSec - newest.timestamp <= REAUTH_WINDOW_SECONDS
  );
}
