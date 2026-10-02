import { assert, assertEquals, assertRejects } from "jsr:@std/assert@1";
import { b64Decode, b64urlEncode, type Claims, importSigningKey, signToken, TOKEN_AUDIENCE } from "./token.ts";

const dec = new TextDecoder();
const claims: Claims = {
  iss: "https://ref.supabase.co",
  aud: TOKEN_AUDIENCE,
  sub: "u1",
  v: 1,
  iat: 1000,
  exp: 2000,
  status: "active",
  features: [],
};

async function throwawayKey() {
  const pair = await crypto.subtle.generateKey("Ed25519", true, ["sign", "verify"]) as CryptoKeyPair;
  const pkcs8 = new Uint8Array(await crypto.subtle.exportKey("pkcs8", pair.privateKey));
  return { pair, privateB64: btoa(String.fromCharCode(...pkcs8)) };
}

Deno.test("token wire format and signature verify with the public key", async () => {
  const { pair, privateB64 } = await throwawayKey();
  const token = await signToken(claims, await importSigningKey(privateB64), "test-1");
  const parts = token.split(".");
  assertEquals(parts.length, 4);
  assertEquals(parts[0], "v1");
  assert(!/[^A-Za-z0-9_.-]/.test(token));
  assertEquals(JSON.parse(dec.decode(b64Decode(parts[1]))), { kid: "test-1" });
  assertEquals(JSON.parse(dec.decode(b64Decode(parts[2]))), claims);
  const ok = await crypto.subtle.verify(
    "Ed25519",
    pair.publicKey,
    b64Decode(parts[3]),
    new TextEncoder().encode(`${parts[0]}.${parts[1]}.${parts[2]}`),
  );
  assert(ok);
  assertEquals(b64urlEncode(b64Decode(parts[3])), parts[3]);
});

Deno.test("tampered payload fails verification", async () => {
  const { pair, privateB64 } = await throwawayKey();
  const token = await signToken(claims, await importSigningKey(privateB64), "test-1");
  const [v, h, , s] = token.split(".");
  const forged = b64urlEncode(new TextEncoder().encode(JSON.stringify({ ...claims, status: "premium" })));
  const ok = await crypto.subtle.verify(
    "Ed25519",
    pair.publicKey,
    b64Decode(s),
    new TextEncoder().encode(`${v}.${h}.${forged}`),
  );
  assertEquals(ok, false);
});

Deno.test("oversized token is refused", async () => {
  const { privateB64 } = await throwawayKey();
  const key = await importSigningKey(privateB64);
  const big = { ...claims, features: ["f".repeat(5000)] };
  await assertRejects(() => signToken(big, key, "k"));
});
