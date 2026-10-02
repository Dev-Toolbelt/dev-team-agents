import { createClient, type SupabaseClient } from "npm:@supabase/supabase-js@2";
import type { AppConfig, AuthedUser, License, Store } from "./types.ts";
import { b64Decode } from "./token.ts";

const bytea = (hex: string) => `\\x${hex}`;

export function requireEnv(name: string): string {
  const v = Deno.env.get(name);
  if (!v) throw new Error(`MissingEnv:${name}`);
  return v;
}

export function adminClient(): SupabaseClient {
  return createClient(requireEnv("SUPABASE_URL"), requireEnv("SUPABASE_SERVICE_ROLE_KEY"), {
    auth: { autoRefreshToken: false, persistSession: false },
  });
}

function ok<T>(res: { data: T; error: unknown }): T {
  if (res.error) throw new Error("DbError");
  return res.data;
}

export function createStore(db: SupabaseClient): Store {
  return {
    async getLicense(userId) {
      const row = ok(
        await db.from("licenses").select("plan,status,features,trial_started_at,ban_reason")
          .eq("user_id", userId).maybeSingle(),
      );
      if (!row) return null;
      return { ...row, trial_started_at: row.trial_started_at ? new Date(row.trial_started_at) : null } as License;
    },
    async getConfig() {
      return ok(
        await db.from("app_config").select("trial_enabled,trial_days,max_offline_days").eq("id", true).single(),
      ) as AppConfig;
    },
    async isBanned(hex) {
      const row = ok(await db.from("banned_identities").select("email_hmac").eq("email_hmac", bytea(hex)).maybeSingle());
      return row !== null;
    },
    async getTrialConsumed(hex) {
      const row = ok(
        await db.from("trial_consumed").select("trial_started_at")
          .eq("email_hmac", bytea(hex)).gt("expires_at", new Date().toISOString()).maybeSingle(),
      );
      return row ? new Date(row.trial_started_at) : null;
    },
    async setTrialStarted(userId, at) {
      ok(await db.from("licenses").update({ trial_started_at: at.toISOString() })
        .eq("user_id", userId).is("trial_started_at", null));
    },
    async takeSlot(userId) {
      return ok(
        await db.rpc("take_entitlement_slot", { p_user_id: userId, p_limit: 30, p_window_seconds: 3600 }),
      ) === true;
    },
    async touchLastSeen(userId, at) {
      ok(await db.from("profiles").update({ last_seen_at: at.toISOString().slice(0, 10) }).eq("id", userId));
    },
    async markBanned(hex, reason) {
      ok(await db.from("banned_identities").upsert(
        { email_hmac: bytea(hex), reason },
        { onConflict: "email_hmac", ignoreDuplicates: true },
      ));
    },
    async markTrialConsumed(hex, startedAt) {
      ok(await db.from("trial_consumed").upsert(
        { email_hmac: bytea(hex), trial_started_at: startedAt.toISOString() },
        { onConflict: "email_hmac", ignoreDuplicates: true },
      ));
    },
    async deleteUser(userId) {
      const { error } = await db.auth.admin.deleteUser(userId);
      if (error) throw new Error("DeleteUserFailed");
    },
  };
}

export function verifier(db: SupabaseClient): (token: string) => Promise<AuthedUser | null> {
  return async (token) => {
    const { data, error } = await db.auth.getUser(token);
    if (error || !data.user) return null;
    const amr = readAmr(token);
    return { id: data.user.id, email: data.user.email ?? null, amr };
  };
}

function readAmr(token: string): AuthedUser["amr"] {
  try {
    const payload = JSON.parse(new TextDecoder().decode(b64Decode(token.split(".")[1])));
    if (!Array.isArray(payload.amr)) return [];
    return payload.amr
      .filter((e: unknown): e is { method: string; timestamp: number } =>
        typeof e === "object" && e !== null &&
        typeof (e as { method?: unknown }).method === "string" &&
        typeof (e as { timestamp?: unknown }).timestamp === "number"
      );
  } catch {
    return [];
  }
}
