import { json, jsonError, logFailure } from "../_shared/http.ts";
import { emailHmacHex } from "../_shared/normalize.ts";
import type { Store } from "../_shared/types.ts";

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export interface BanDeps {
  store: Store;
  banKey: string;
  serviceKey: string;
}

/** Constant-time comparison of two strings of possibly different length. */
function sameSecret(a: string, b: string): boolean {
  const x = new TextEncoder().encode(a);
  const y = new TextEncoder().encode(b);
  let diff = x.length ^ y.length;
  for (let i = 0; i < Math.max(x.length, y.length); i++) diff |= (x[i] ?? 0) ^ (y[i] ?? 0);
  return diff === 0;
}

/**
 * Bans an account in one step (SR-34, SR-35, SR-38): the license, the auth ban and the
 * session revocation in SQL, then the email HMAC that survives a later deletion. Callable
 * only with the service-role key; operators run it from the runbook, never a client.
 */
export async function handleBanUser(req: Request, deps: BanDeps): Promise<Response> {
  if (req.method !== "POST") return jsonError(405, "method_not_allowed");
  const header = req.headers.get("authorization") ?? "";
  const presented = header.startsWith("Bearer ") ? header.slice(7) : "";
  if (!presented || !sameSecret(presented, deps.serviceKey)) return jsonError(401, "unauthorized");

  let body: { user_id?: unknown; reason?: unknown };
  try {
    body = await req.json();
  } catch {
    return jsonError(400, "bad_request");
  }
  const userId = typeof body.user_id === "string" ? body.user_id : "";
  const reason = typeof body.reason === "string" ? body.reason.trim() : "";
  if (!UUID_RE.test(userId) || !reason || reason.length > 500) return jsonError(400, "bad_request");

  try {
    const email = await deps.store.banUser(userId, reason);
    if (email) await deps.store.markBanned(await emailHmacHex(deps.banKey, email), reason);
    return json(200, { ok: true, identity_recorded: email !== null });
  } catch (err) {
    logFailure("ban-user", err);
    return jsonError(500, "request_failed");
  }
}
