import { assertEquals } from "@std/assert";
import { emailHmacHex } from "../_shared/normalize.ts";
import { fakeState, fakeStore, USER } from "../_shared/testing.ts";
import { handleBanUser } from "./handler.ts";

const SERVICE = "service-role-secret";

function call(token: string | null, body: unknown, s = fakeState()) {
  const headers = new Headers();
  if (token) headers.set("authorization", `Bearer ${token}`);
  const req = new Request("http://localhost/ban-user", { method: "POST", headers, body: JSON.stringify(body) });
  return { s, res: handleBanUser(req, { store: fakeStore(s), banKey: "test-pepper", serviceKey: SERVICE }) };
}

Deno.test("ban-user refuses anything but the service key", async () => {
  for (const token of [null, "anon", SERVICE + "x"]) {
    const { res } = call(token, { user_id: USER.id, reason: "abuse" });
    assertEquals((await res).status, 401);
  }
});

Deno.test("ban-user bans in SQL and records the email HMAC", async () => {
  const { s, res } = call(SERVICE, { user_id: USER.id, reason: "abuse" });
  assertEquals((await res).status, 200);
  assertEquals(s.calls.includes("banUser:" + USER.id), true);
  assertEquals(s.banned.has(await emailHmacHex("test-pepper", USER.email!)), true);
});

Deno.test("ban-user validates its input", async () => {
  for (const body of [{}, { user_id: "nope", reason: "x" }, { user_id: USER.id, reason: "" }]) {
    const { res } = call(SERVICE, body);
    assertEquals((await res).status, 400);
  }
});
