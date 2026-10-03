import { jsonError, logFailure } from "../_shared/http.ts";
import { adminClient, createStore, requireEnv } from "../_shared/supabase.ts";
import { handleBanUser } from "./handler.ts";

Deno.serve(async (req) => {
  try {
    return await handleBanUser(req, {
      store: createStore(adminClient()),
      banKey: requireEnv("BAN_HMAC_KEY"),
      serviceKey: requireEnv("SUPABASE_SERVICE_ROLE_KEY"),
    });
  } catch (err) {
    logFailure("ban-user-boot", err);
    return jsonError(500, "request_failed");
  }
});
