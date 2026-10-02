import { bearerToken, json, jsonError, logFailure } from "../_shared/http.ts";
import { emailHmacHex } from "../_shared/normalize.ts";
import { deriveEntitlement, expirySeconds } from "../_shared/status.ts";
import { type Claims, signToken, TOKEN_AUDIENCE } from "../_shared/token.ts";
import type { Deps } from "../_shared/types.ts";

export const RATE_LIMIT_PER_HOUR = 30;
export const RATE_LIMIT_WINDOW_SECONDS = 3600;

export interface EntitlementDeps extends Deps {
  signingKey: CryptoKey;
  kid: string;
  issuer: string;
}

export async function handleEntitlement(req: Request, deps: EntitlementDeps): Promise<Response> {
  if (req.method !== "GET" && req.method !== "POST") return jsonError(405, "method_not_allowed");

  const jwt = bearerToken(req);
  if (!jwt) return jsonError(401, "unauthorized");

  try {
    const user = await deps.verifyJwt(jwt);
    if (!user) return jsonError(401, "unauthorized");

    if (!(await deps.store.takeSlot(user.id))) {
      return jsonError(429, "rate_limited", { "retry-after": String(RATE_LIMIT_WINDOW_SECONDS) });
    }

    const now = deps.now();
    const [license, config] = await Promise.all([deps.store.getLicense(user.id), deps.store.getConfig()]);
    if (!license) throw new Error("MissingLicense");

    const hmac = user.email ? await emailHmacHex(deps.banKey, user.email) : null;
    const [identityBanned, consumedAt] = hmac
      ? await Promise.all([deps.store.isBanned(hmac), deps.store.getTrialConsumed(hmac)])
      : [false, null];

    const trialStartedAt = license.trial_started_at ?? consumedAt ?? now;
    if (!license.trial_started_at) await deps.store.setTrialStarted(user.id, trialStartedAt);

    const derived = deriveEntitlement({ license, config, identityBanned, trialStartedAt, now });
    const iat = Math.floor(now.getTime() / 1000);
    const claims: Claims = {
      iss: deps.issuer,
      aud: TOKEN_AUDIENCE,
      sub: user.id,
      v: 1,
      iat,
      exp: expirySeconds(iat, config.max_offline_days, derived.status === "trial" ? derived.trialEndsAt : null),
      status: derived.status,
      features: derived.features,
    };
    if (derived.status === "trial" && derived.trialEndsAt) {
      claims.trial_ends_at = Math.floor(derived.trialEndsAt.getTime() / 1000);
    }

    const token = await signToken(claims, deps.signingKey, deps.kid);
    await deps.store.touchLastSeen(user.id, now);
    return json(200, { token });
  } catch (err) {
    logFailure("entitlement", err);
    return jsonError(500, "request_failed");
  }
}
