import { jsonError, logFailure } from "../_shared/http.ts";
import { adminClient, createStore, requireEnv, verifier } from "../_shared/supabase.ts";
import { importSigningKey } from "../_shared/token.ts";
import { handleEntitlement } from "./handler.ts";

Deno.serve(async (req) => {
  try {
    const db = adminClient();
    return await handleEntitlement(req, {
      store: createStore(db),
      verifyJwt: verifier(db),
      banKey: requireEnv("BAN_HMAC_KEY"),
      signingKey: await importSigningKey(requireEnv("ENTITLEMENT_ED25519_PRIVATE_KEY")),
      kid: requireEnv("ENTITLEMENT_KID"),
      issuer: new URL(requireEnv("SUPABASE_URL")).origin,
      now: () => new Date(),
    });
  } catch (err) {
    logFailure("entitlement-boot", err);
    return jsonError(500, "request_failed");
  }
});
