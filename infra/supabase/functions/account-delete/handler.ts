import { bearerToken, json, jsonError, logFailure } from "../_shared/http.ts";
import { emailHmacHex } from "../_shared/normalize.ts";
import { isFreshlyAuthenticated } from "../_shared/reauth.ts";
import type { Deps } from "../_shared/types.ts";

export async function handleAccountDelete(req: Request, deps: Deps): Promise<Response> {
  if (req.method !== "POST") return jsonError(405, "method_not_allowed");

  const jwt = bearerToken(req);
  if (!jwt) return jsonError(401, "unauthorized");

  try {
    const user = await deps.verifyJwt(jwt);
    if (!user) return jsonError(401, "unauthorized");

    const now = deps.now();
    if (!isFreshlyAuthenticated(user, now)) return jsonError(403, "reauth_required");

    const license = await deps.store.getLicense(user.id);
    if (user.email) {
      const hmac = await emailHmacHex(deps.banKey, user.email);
      const banned = license?.status === "banned" || (await deps.store.isBanned(hmac));
      if (banned) await deps.store.markBanned(hmac, license?.ban_reason ?? "banned");
      const existing = await deps.store.getTrialConsumed(hmac);
      await deps.store.markTrialConsumed(hmac, license?.trial_started_at ?? existing ?? now);
    }

    await deps.store.deleteUser(user.id);
    return json(200, { ok: true });
  } catch (err) {
    logFailure("account-delete", err);
    return jsonError(500, "request_failed");
  }
}
