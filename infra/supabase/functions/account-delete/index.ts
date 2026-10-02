import { jsonError, logFailure } from "../_shared/http.ts";
import { adminClient, createStore, requireEnv, verifier } from "../_shared/supabase.ts";
import { handleAccountDelete } from "./handler.ts";

Deno.serve(async (req) => {
  try {
    const db = adminClient();
    return await handleAccountDelete(req, {
      store: createStore(db),
      verifyJwt: verifier(db),
      banKey: requireEnv("BAN_HMAC_KEY"),
      now: () => new Date(),
    });
  } catch (err) {
    logFailure("account-delete-boot", err);
    return jsonError(500, "request_failed");
  }
});
