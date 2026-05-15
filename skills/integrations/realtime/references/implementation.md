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

For non-Supabase projects using raw WebSockets or other providers:

**Connection management**
```typescript
class RealtimeConnection {
  private ws: WebSocket | null = null
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null

  connect(url: string) {
    this.ws = new WebSocket(url)
    this.ws.onopen = () => this.onConnected()
    this.ws.onmessage = (e) => this.onMessage(JSON.parse(e.data))
    this.ws.onclose = () => this.scheduleReconnect(url)
    this.ws.onerror = (e) => console.error('WS error', e)
  }

  private scheduleReconnect(url: string) {
    this.reconnectTimer = setTimeout(() => this.connect(url), 3000)
  }

  disconnect() {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer)
    this.ws?.close()
    this.ws = null
  }
}
```

**Always implement reconnection** — WebSocket connections drop silently on mobile, network changes, and server restarts.

**Message framing**: use a typed envelope:
```typescript
type WsMessage<T = unknown> = {
  event: string
  payload: T
  ref?: string  // correlation ID for request/response patterns
}
```
