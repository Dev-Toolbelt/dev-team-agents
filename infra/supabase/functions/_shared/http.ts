const BASE_HEADERS = {
  "content-type": "application/json",
  "cache-control": "no-store",
};

export function json(status: number, body: unknown, extra: Record<string, string> = {}): Response {
  return new Response(JSON.stringify(body), { status, headers: { ...BASE_HEADERS, ...extra } });
}

export function jsonError(status: number, code: string, extra: Record<string, string> = {}): Response {
  return json(status, { error: code }, extra);
}

export function bearerToken(req: Request): string | null {
  const header = req.headers.get("authorization") ?? "";
  const match = /^Bearer ([A-Za-z0-9._~+/-]+=*)$/.exec(header);
  return match ? match[1] : null;
}

export function logFailure(fn: string, err: unknown): void {
  const name = err instanceof Error ? err.name : "UnknownError";
  console.error(JSON.stringify({ level: "error", fn, error: name }));
}
