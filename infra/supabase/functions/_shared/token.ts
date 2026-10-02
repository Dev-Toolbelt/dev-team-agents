import type { EntitlementStatus } from "./types.ts";

export const TOKEN_VERSION = "v1";
export const TOKEN_AUDIENCE = "devteam-cli";
export const MAX_TOKEN_BYTES = 4096;

export interface Claims {
  iss: string;
  aud: string;
  sub: string;
  v: 1;
  iat: number;
  exp: number;
  status: EntitlementStatus;
  features: string[];
  trial_ends_at?: number;
}

const encoder = new TextEncoder();

export function b64urlEncode(bytes: Uint8Array): string {
  let bin = "";
  for (const b of bytes) bin += String.fromCharCode(b);
  return btoa(bin).replaceAll("+", "-").replaceAll("/", "_").replace(/=+$/, "");
}

export function b64Decode(b64: string): Uint8Array<ArrayBuffer> {
  const bin = atob(b64.replaceAll("-", "+").replaceAll("_", "/"));
  const out = new Uint8Array(new ArrayBuffer(bin.length));
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

export function importSigningKey(pkcs8Base64: string): Promise<CryptoKey> {
  return crypto.subtle.importKey("pkcs8", b64Decode(pkcs8Base64), "Ed25519", false, ["sign"]);
}

export async function signToken(claims: Claims, key: CryptoKey, kid: string): Promise<string> {
  const header = b64urlEncode(encoder.encode(JSON.stringify({ kid })));
  const payload = b64urlEncode(encoder.encode(JSON.stringify(claims)));
  const signingInput = `${TOKEN_VERSION}.${header}.${payload}`;
  const sig = new Uint8Array(await crypto.subtle.sign("Ed25519", key, encoder.encode(signingInput)));
  const token = `${signingInput}.${b64urlEncode(sig)}`;
  if (token.length > MAX_TOKEN_BYTES) throw new Error("TokenTooLarge");
  return token;
}
