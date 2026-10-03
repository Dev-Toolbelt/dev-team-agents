import { assertEquals } from "@std/assert";
import { emailHmacHex } from "../_shared/normalize.ts";
import { fakeDeps, fakeState, NOW, req, USER } from "../_shared/testing.ts";
import { AuthUnavailable } from "../_shared/types.ts";
import { handleAccountDelete } from "./handler.ts";

const stale = { ...USER, amr: [{ method: "otp", timestamp: Math.floor(NOW.getTime() / 1000) - 3600 }] };
const hmac = () => emailHmacHex("test-pepper", "person@example.com");

Deno.test("no JWT or invalid JWT: 401 and nothing deleted", async () => {
  const s = fakeState();
  for (const r of [req("POST", null), req("POST", "bad")]) {
    assertEquals((await handleAccountDelete(r, fakeDeps(s))).status, 401);
  }
  assertEquals(s.deleted, []);
});

Deno.test("stale authentication is refused without side effects (SR-37)", async () => {
  const s = fakeState();
  const res = await handleAccountDelete(req("POST", "good"), fakeDeps(s, stale));
  assertEquals(res.status, 403);
  assertEquals(await res.json(), { error: "reauth_required" });
  assertEquals(s.calls, []);
});

Deno.test("a body naming another user id is ignored", async () => {
  const s = fakeState();
  const res = await handleAccountDelete(req("POST", "good", { user_id: "other" }), fakeDeps(s));
  assertEquals(res.status, 200);
  assertEquals(s.deleted, [USER.id]);
});

Deno.test("deletion records trial_consumed before deleting the user", async () => {
  const s = fakeState();
  s.license = { ...s.license!, trial_started_at: NOW };
  await handleAccountDelete(req("POST", "good"), fakeDeps(s));
  assertEquals(s.calls, ["markTrialConsumed", "deleteUser"]);
  assertEquals(s.consumed.get(await hmac()), NOW);
});

Deno.test("an account deleted before any trial started leaves no trial marker", async () => {
  const s = fakeState();
  await handleAccountDelete(req("POST", "good"), fakeDeps(s));
  assertEquals(s.calls, ["deleteUser"]);
  assertEquals(s.consumed.size, 0);
});

Deno.test("a fresh password or OAuth sign-in is not enough to delete", async () => {
  const fresh = Math.floor(NOW.getTime() / 1000) - 30;
  for (const method of ["password", "oauth"]) {
    const user = { ...USER, amr: [{ method: "otp", timestamp: fresh - 60 }, { method, timestamp: fresh }] };
    const s = fakeState();
    const res = await handleAccountDelete(req("POST", "good"), fakeDeps(s, user));
    assertEquals(res.status, 403, method);
    assertEquals(s.deleted, []);
  }
});

Deno.test("an unavailable auth service answers 503, not 401", async () => {
  const s = fakeState();
  const deps = { ...fakeDeps(s), verifyJwt: () => Promise.reject(new AuthUnavailable()) };
  const res = await handleAccountDelete(req("POST", "good"), deps);
  assertEquals(res.status, 503);
});

Deno.test("an existing trial start is preserved", async () => {
  const start = new Date(NOW.getTime() - 3 * 86400_000);
  const s = fakeState();
  s.license = { ...s.license!, trial_started_at: start };
  await handleAccountDelete(req("POST", "good"), fakeDeps(s));
  assertEquals(s.consumed.get(await hmac()), start);
});

Deno.test("a banned account stays banned after deletion", async () => {
  const s = fakeState();
  s.license = { ...s.license!, status: "banned", ban_reason: "abuse" };
  await handleAccountDelete(req("POST", "good"), fakeDeps(s));
  assertEquals(s.banned.has(await hmac()), true);
  assertEquals(s.deleted, [USER.id]);
});

Deno.test("a non-banned account leaves no ban row", async () => {
  const s = fakeState();
  await handleAccountDelete(req("POST", "good"), fakeDeps(s));
  assertEquals(s.banned.size, 0);
});

Deno.test("failure is generic and non-POST is refused", async () => {
  const s = fakeState();
  const d = fakeDeps(s);
  d.store.deleteUser = () => Promise.reject(new Error("secret detail user@x.io"));
  const res = await handleAccountDelete(req("POST", "good"), d);
  assertEquals(res.status, 500);
  assertEquals(await res.json(), { error: "request_failed" });
  assertEquals((await handleAccountDelete(req("GET", "good"), fakeDeps(s))).status, 405);
});
