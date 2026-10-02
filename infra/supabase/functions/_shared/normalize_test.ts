import { assertEquals, assertNotEquals } from "jsr:@std/assert@1";
import { emailHmacHex, normalizeEmail, toHex } from "./normalize.ts";

Deno.test("normalize trims, NFC-composes and lowercases, nothing else", () => {
  assertEquals(normalizeEmail("  Jo.Doe+tag@Example.COM \n"), "jo.doe+tag@example.com");
  assertEquals(normalizeEmail("café@x.io"), "café@x.io");
});

Deno.test("hmac is stable across case and whitespace, and is not a plain SHA-256", async () => {
  const a = await emailHmacHex("pepper", "Person@Example.com");
  const b = await emailHmacHex("pepper", "  person@example.COM ");
  assertEquals(a, b);
  assertEquals(a.length, 64);
  const sha = toHex(new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode("person@example.com"))));
  assertNotEquals(a, sha);
  assertNotEquals(a, await emailHmacHex("other-pepper", "person@example.com"));
});
