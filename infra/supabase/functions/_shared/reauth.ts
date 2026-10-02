import type { AuthedUser } from "./types.ts";

export const REAUTH_WINDOW_SECONDS = 300;
const FUTURE_TOLERANCE_SECONDS = 60;

export function isFreshlyAuthenticated(user: AuthedUser, now: Date): boolean {
  const nowSec = Math.floor(now.getTime() / 1000);
  return user.amr.some(
    (e) =>
      Number.isFinite(e.timestamp) &&
      e.timestamp <= nowSec + FUTURE_TOLERANCE_SECONDS &&
      nowSec - e.timestamp <= REAUTH_WINDOW_SECONDS,
  );
}
