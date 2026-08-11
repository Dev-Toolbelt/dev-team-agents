---
name: sse-streaming
description: Server-Sent Events — text/event-stream format, EventSource, reconnection, keep-alive, CORS.
---

# SSE Streaming

Server-to-client one-way streaming over plain HTTP. Use for notifications, live feeds, progress updates, dashboards — anything where the server pushes and the client only listens.

---

## When to Apply

| Signal | Action |
|--------|--------|
| Live notifications, activity feeds, progress bars for long-running jobs, real-time dashboards | Apply this skill |
| `EventSource`, `text/event-stream`, `sse` anywhere in the codebase or requirements | Apply this skill |
| Client needs to *send* data too, not just receive (chat, collaborative editing, low-latency bidirectional) | Do not use SSE — use WebSocket instead |
| Updates are infrequent (minutes apart) and staleness is acceptable | Do not use SSE — plain polling is simpler |

---

## Protocol Format

Response `Content-Type` must be `text/event-stream`. Messages are field-value lines terminated by `\n`, and a message ends with a blank line (`\n\n`).

| Field | Purpose |
|-------|---------|
| `event` | Names the event type; triggers a matching `addEventListener()` on the client. Omit to trigger `onmessage` instead |
| `data` | Payload. Multiple consecutive `data:` lines are joined with `\n` — used to stream multi-line payloads |
| `id` | Sets the last-event-id on the client; echoed back as `Last-Event-ID` on reconnect |
| `retry` | Reconnection delay in milliseconds (integer only; non-integer values are ignored) |
| `: comment` | Any line starting with `:` is ignored by the client — use for keep-alive pings |

```
: keep-alive

event: order.updated
id: 482
data: {"orderId": 482, "status": "shipped"}

data: plain message with no event name
data: second line, joined with \n above
```

---

## Backend

### Required response headers
```
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
```
- Behind Nginx or another buffering proxy, also send `X-Accel-Buffering: no` — otherwise events queue until the proxy buffer fills instead of streaming immediately.
- Flush the response after every message; do not let framework-level output buffering hold events back.

### Keep-alive
Send a `: comment` line (or a synthetic `event: ping`) every 15–30 seconds on idle streams. Intermediate proxies and load balancers close connections they consider inactive; a keep-alive line resets that timer without triggering any client-side handler.

### Resuming after reconnect
- Set `id` on every message that represents resumable state.
- On reconnect, the browser automatically sends `Last-Event-ID` as a request header. Read it server-side and replay only the events the client missed — never replay the full history by default.
- Store the last emitted `id` per stream/topic wherever the source events already live (queue offset, DB row id, log sequence) — do not introduce a separate id-tracking store just for this.

### Connection lifecycle
- Detect client disconnect (aborted request / closed socket) and stop producing work for that stream — do not keep computing updates for a client that is gone.
- Cap concurrent open streams per user/connection where the runtime allows it, to bound resource usage on abusive or leaked clients.

### Authentication
`EventSource` cannot set custom request headers, so a bearer token in an `Authorization` header is not an option for the initial request. Use one of:
- A short-lived, signed token in the query string, validated and then discarded server-side (never log the full URL).
- The session cookie, if the API and the page share an origin (or `withCredentials: true` cross-origin) — subject to normal CORS/cookie rules.

---

## Frontend

### Connecting
```js
const source = new EventSource('/api/stream');                 // same-origin
const source = new EventSource('/api/stream', { withCredentials: true }); // cross-origin, send cookies
```

### Listening
```js
source.onmessage = (e) => {
  // fires only for messages with no `event` field
};

source.addEventListener('order.updated', (e) => {
  const payload = JSON.parse(e.data);
});

source.onerror = (err) => {
  // fires on network drop too — EventSource auto-reconnects unless readyState is CLOSED
};
```

### Reconnection
- The browser reconnects automatically after a drop, honoring the server's `retry` field (default ~3s) and resending `Last-Event-ID`.
- Only call `source.close()` explicitly when the feature no longer needs the stream (component unmount, user navigates away, explicit "stop" action) — closing and recreating on every re-render defeats the reconnection/id-resume machinery.

### UX rules
- Show a distinct "reconnecting" state in `onerror` when `source.readyState === EventSource.CONNECTING` — don't surface a fatal error for a transient drop the browser is already retrying.
- Treat `readyState === EventSource.CLOSED` as terminal: the browser gave up (e.g., after a non-retryable HTTP error) and the UI must offer a manual retry, not sit silently disconnected.

---

## Limitations

| Constraint | Detail |
|---|---|
| HTTP/1.1 connection cap | 6 concurrent connections per browser **per domain**, shared across all tabs. Marked "won't fix" by Chrome and Firefox. Affects any page opening more than one SSE stream, or opening one in multiple tabs. |
| Mitigation | Serve SSE over HTTP/2 — the per-domain cap becomes a negotiated stream count (default 100), not a TCP connection count. |
| Workaround (HTTP/1.1 only) | Spread streams across subdomains if HTTP/2 isn't available — 6 connections apply per domain, not globally. |
| No client → server messages | SSE is receive-only. A feature that later needs the client to push data mid-stream has outgrown SSE — move to WebSocket rather than bolting a second channel on top. |

---

## DevOps

- Any reverse proxy or load balancer in front of the stream must have its idle-connection timeout set **longer** than the keep-alive interval above, or it will kill the stream and force constant reconnects.
- Disable response buffering for the SSE route specifically (e.g., Nginx `proxy_buffering off;` or the equivalent `X-Accel-Buffering: no` header) — buffering turns a stream into batched, laggy delivery.
- If the deployment uses sticky sessions or in-memory pub/sub to fan out events to connected clients, ensure load-balancer affinity keeps a client's reconnect on the same backend instance that holds its state, or move the fan-out to a shared broker (Redis pub/sub, etc.) so any instance can serve any client.
