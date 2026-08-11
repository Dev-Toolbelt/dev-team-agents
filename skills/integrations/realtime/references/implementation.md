# Realtime Implementation Examples

## Channel Lifecycle

```typescript
import { createClient } from '@supabase/supabase-js'
const supabase = createClient(url, anonKey)

const channel = supabase.channel('room:lobby')  // channel name is arbitrary

channel
  .on('broadcast', { event: 'chat' }, (payload) => {
    console.log('message:', payload)
  })
  .subscribe((status) => {
    if (status === 'SUBSCRIBED') {
      // channel is ready
    }
  })

// Cleanup — always unsubscribe when the component/view is destroyed
supabase.removeChannel(channel)
```

Statuses: `SUBSCRIBED` | `TIMED_OUT` | `CLOSED` | `CHANNEL_ERROR`

## Broadcast

Send messages to all clients subscribed to the same channel:

```typescript
// Send
await channel.send({
  type: 'broadcast',
  event: 'cursor-move',
  payload: { x: 100, y: 200, user_id: 'abc' }
})

// Receive (set up before subscribing)
channel.on('broadcast', { event: 'cursor-move' }, ({ payload }) => {
  updateCursor(payload)
})
```

Broadcast does not persist messages. Use for ephemeral events (cursors, typing indicators, live votes). For durability, write to the database and let Postgres Changes propagate.

## Presence

Track connected users and their state:

```typescript
const presenceChannel = supabase.channel('room:lobby', {
  config: { presence: { key: userId } }
})

presenceChannel
  .on('presence', { event: 'sync' }, () => {
    const state = presenceChannel.presenceState()
    renderOnlineUsers(state)
  })
  .on('presence', { event: 'join' }, ({ key, newPresences }) => {
    console.log(`${key} joined`)
  })
  .on('presence', { event: 'leave' }, ({ key, leftPresences }) => {
    console.log(`${key} left`)
  })
  .subscribe(async (status) => {
    if (status === 'SUBSCRIBED') {
      await presenceChannel.track({ user_id: userId, status: 'online' })
    }
  })
```

Call `presenceChannel.untrack()` on logout or component teardown.

## Postgres Changes

Stream database row mutations to clients. Respects RLS — users only receive changes for rows they can SELECT.

```typescript
supabase
  .channel('db-changes')
  .on(
    'postgres_changes',
    { event: '*', schema: 'public', table: 'messages' },
    (payload) => {
      // payload.eventType: 'INSERT' | 'UPDATE' | 'DELETE'
      // payload.new: new row data
      // payload.old: old row data (UPDATE/DELETE)
      handleChange(payload)
    }
  )
  .subscribe()
```

Filter by column value:
```typescript
{ event: 'INSERT', schema: 'public', table: 'orders', filter: 'status=eq.pending' }
```

**Important**: Postgres Changes requires `replica identity` to stream `old` row data on UPDATE/DELETE:
```sql
alter table messages replica identity full;
```

## Frontend Patterns

**React hook for a channel**
```typescript
function useRealtimeChannel(channelName: string, handler: (payload: unknown) => void) {
  useEffect(() => {
    const channel = supabase
      .channel(channelName)
      .on('broadcast', { event: '*' }, handler)
      .subscribe()

    return () => { supabase.removeChannel(channel) }
  }, [channelName])
}
```

**Connection status indicator**: always expose connection state to the user — a stale UI without live updates is worse than no live updates.

```typescript
const [status, setStatus] = useState<'connecting' | 'live' | 'offline'>('connecting')

channel.subscribe((s) => {
  setStatus(s === 'SUBSCRIBED' ? 'live' : 'offline')
})
```

## Backend Patterns

**Broadcast from server (Supabase)**
```typescript
// Server-side broadcast via REST (no persistent WS connection needed)
await adminSupabase
  .channel('notifications')
  .send({ type: 'broadcast', event: 'alert', payload: { message: 'deploy complete' } })
```

**Avoid N+1 subscriptions**: create one channel per logical scope (room, document, user), not one per row. Filter at the subscription level rather than subscribing to all rows and filtering client-side.

## Generic WebSocket Patterns

For non-Supabase projects using raw WebSockets or other providers. Based on the [WebSocket API](https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API) — patterns below are plain-`WebSocket` and apply regardless of client/server framework.

**readyState** — the connection has four states; guard every `send()` on it:
```typescript
// WebSocket.CONNECTING = 0, OPEN = 1, CLOSING = 2, CLOSED = 3
function safeSend(ws: WebSocket, data: string) {
  if (ws.readyState === WebSocket.OPEN) ws.send(data)
  // else: queue it, or drop it — never call send() while CONNECTING/CLOSING/CLOSED
}
```

**Connection management with heartbeat and backoff**
```typescript
class RealtimeConnection {
  private ws: WebSocket | null = null
  private reconnectAttempts = 0
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null

  connect(url: string) {
    this.ws = new WebSocket(url) // use wss:// on any https:// page — browsers block mixed content
    this.ws.onopen = () => {
      this.reconnectAttempts = 0
      this.startHeartbeat()
      this.onConnected()
    }
    this.ws.onmessage = (e) => this.onMessage(JSON.parse(e.data))
    this.ws.onclose = (e) => {
      this.stopHeartbeat()
      this.handleClose(e, url)
    }
    this.ws.onerror = (e) => console.error('WS error', e) // errors precede close — do cleanup in onclose, not onerror
  }

  private handleClose(e: CloseEvent, url: string) {
    // 1000 = normal closure, 1001 = endpoint going away — don't reconnect
    if (e.code === 1000 || e.code === 1001) return
    this.scheduleReconnect(url)
  }

  private scheduleReconnect(url: string) {
    const delay = Math.min(30_000, 1000 * 2 ** this.reconnectAttempts) + Math.random() * 500 // exponential backoff + jitter
    this.reconnectAttempts++
    this.reconnectTimer = setTimeout(() => this.connect(url), delay)
  }

  private startHeartbeat() {
    // app-level ping — the WebSocket protocol's own ping/pong frames aren't exposed to JS
    this.heartbeatTimer = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) this.ws.send(JSON.stringify({ event: 'ping' }))
    }, 30_000)
  }

  private stopHeartbeat() {
    if (this.heartbeatTimer) clearInterval(this.heartbeatTimer)
  }

  disconnect() {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer)
    this.stopHeartbeat()
    this.ws?.close(1000, 'client disconnect') // explicit code — distinguishes intentional close from a drop
    this.ws = null
  }
}
```

**Always implement reconnection with backoff** — WebSocket connections drop silently on mobile, network changes, and server restarts. A fixed retry interval hammers a recovering server; exponential backoff with jitter avoids a reconnect storm across many clients.

**Close codes worth branching on**: `1000` normal closure, `1001` going away (navigation/server shutdown), `1006` abnormal closure (no close frame — network drop, never sent by the server itself), `1008` policy violation (e.g. failed auth), `1011` server error. Treat anything other than `1000`/`1001` as a signal to reconnect (with backoff), and log `1008`/`1011` distinctly since retrying blindly won't fix them.

**Binary data**: default `binaryType` is `"blob"`; set `ws.binaryType = "arraybuffer"` when the payload needs synchronous processing (e.g. `TypedArray` views). `send()` also accepts `Blob`, `ArrayBuffer`, `TypedArray`, or `DataView` directly — no need to base64-encode binary payloads into a text frame.

**Backpressure**: `send()` is fire-and-forget over an internal buffer. Before pushing another large payload, check `ws.bufferedAmount` (bytes not yet sent) rather than assuming the previous `send()` flushed — a slow consumer accumulates backlog silently instead of raising an error.

**Message framing**: use a typed envelope:
```typescript
type WsMessage<T = unknown> = {
  event: string
  payload: T
  ref?: string  // correlation ID for request/response patterns
}
```

**Server-side auth**: WebSocket upgrade requests don't carry the app's normal auth headers reliably across all clients — validate the token as a query param or subprotocol during the HTTP upgrade handshake, and close with code `1008` if it fails, before accepting the connection. Never trust `Origin` alone for authorization; it's a hint, not a security boundary.

**Cleanup on page lifecycle** (browser clients): close the socket on `pagehide` and reconnect on `pageshow` — an open WebSocket connection blocks the page from entering the browser's back/forward cache (bfcache).
