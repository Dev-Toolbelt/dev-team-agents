const encoder = new TextEncoder();

export function normalizeEmail(email: string): string {
  return email.trim().normalize("NFC").toLowerCase();
}

export function toHex(bytes: Uint8Array): string {
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}

export async function emailHmacHex(pepper: string, email: string): Promise<string> {
  const key = await crypto.subtle.importKey(
    "raw",
    encoder.encode(pepper),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const mac = await crypto.subtle.sign("HMAC", key, encoder.encode(normalizeEmail(email)));
  return toHex(new Uint8Array(mac));
}
