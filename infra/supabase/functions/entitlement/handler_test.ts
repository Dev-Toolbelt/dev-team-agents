import { assert, assertEquals } from "jsr:@std/assert@1";
import { b64Decode, importSigningKey } from "../_shared/token.ts";
import { emailHmacHex } from "../_shared/normalize.ts";
import { fakeDeps, fakeState, NOW, req, USER } from "../_shared/testing.ts";
import { type EntitlementDeps, handleEntitlement } from "./handler.ts";

async function deps(state = fakeState(), user = USER): Promise<EntitlementDeps> {
  const pair = await crypto.subtle.generateKey("Ed25519", true, ["sign", "verify"]) as CryptoKeyPair;
  const pkcs8 = new Uint8Array(await crypto.subtle.exportKey("pkcs8", pair.privateKey));
  return {
    ...fakeDeps(state, user),
    signingKey: await importSigningKey(btoa(String.fromCharCode(...pkcs8))),
    kid: "test-1",
    issuer: "https://ref.supabase.co",
  };
}

const payloadOf = async (res: Response) => {
  const { token } = await res.json();
  return JSON.parse(new TextDecoder().decode(b64Decode(token.split(".")[2])));
};

Deno.test("no JWT and an invalid JWT both get a generic 401", async () => {
  const d = await deps();
  for (const r of [req("POST", null), req("POST", "bad")]) {
    const res = await handleEntitlement(r, d);
    assertEquals(res.status, 401);
    assertEquals(await res.json(), { error: "unauthorized" });
  }
});

Deno.test("user id comes from the JWT, never from the body", async () => {
  const res = await handleEntitlement(req("POST", "good", { user_id: "22222222-2222-2222-2222-222222222222" }), await deps());
  assertEquals(res.status, 200);
  assertEquals((await payloadOf(res)).sub, USER.id);
});

Deno.test("trial disabled: active token, 7-day expiry, no CORS headers", async () => {
  const res = await handleEntitlement(req("GET", "good"), await deps());
  const p = await payloadOf(res);
  assertEquals(p.status, "active");
  assertEquals(p.exp - p.iat, 7 * 86400);
  assertEquals(p.aud, "devteam-cli");
  assertEquals(p.iss, "https://ref.supabase.co");
  assertEquals(res.headers.get("access-control-allow-origin"), null);
});

Deno.test("first request starts the trial; exp never passes the trial end", async () => {
  const state = fakeState({ config: { trial_enabled: true, trial_days: 2, max_offline_days: 7 } });
  const p = await payloadOf(await handleEntitlement(req("POST", "good"), await deps(state)));
  assertEquals(p.status, "trial");
  assertEquals(p.exp, p.trial_ends_at);
  assertEquals(p.trial_ends_at, Math.floor(NOW.getTime() / 1000) + 2 * 86400);
  assertEquals(state.license?.trial_started_at, NOW);
});

Deno.test("re-registering a banned email yields banned", async () => {
  const state = fakeState();
  state.banned.add(await emailHmacHex("test-pepper", "person@example.com"));
  assertEquals((await payloadOf(await handleEntitlement(req("POST", "good"), await deps(state)))).status, "banned");
});

Deno.test("deleted account re-registering resumes the consumed trial", async () => {
  const state = fakeState({ config: { trial_enabled: true, trial_days: 5, max_offline_days: 7 } });
  state.consumed.set(await emailHmacHex("test-pepper", "person@example.com"), new Date(NOW.getTime() - 9 * 86400_000));
  assertEquals((await payloadOf(await handleEntitlement(req("POST", "good"), await deps(state)))).status, "trial_expired");
});

Deno.test("rate limit returns 429 with retry-after", async () => {
  const res = await handleEntitlement(req("POST", "good"), await deps(fakeState({ slots: 0 })));
  assertEquals(res.status, 429);
  assert(res.headers.get("retry-after"));
});

Deno.test("missing license row fails generically", async () => {
  const res = await handleEntitlement(req("POST", "good"), await deps(fakeState({ license: null })));
  assertEquals(res.status, 500);
  assertEquals(await res.json(), { error: "request_failed" });
});

Deno.test("other methods are refused", async () => {
  assertEquals((await handleEntitlement(req("DELETE", "good"), await deps())).status, 405);
});
