---
title: Clean Up Realtime Subscriptions
impact: MEDIUM
impactDescription: Prevents memory leaks and unnecessary server connections
tags: realtime, performance, cleanup, subscriptions
---

## Clean Up Realtime Subscriptions

**Impact: MEDIUM (Prevents memory leaks and unnecessary server connections)**

Always unsubscribe from realtime channels when components unmount or when subscriptions are no longer needed. Failing to clean up subscriptions causes memory leaks, wasted server resources, and can lead to receiving stale or duplicate events.

**Incorrect (no cleanup on unmount):**

```typescript
// DON'T DO THIS - memory leak in React
function ChatRoom({ roomId }: { roomId: string }) {
  const [messages, setMessages] = useState<Message[]>([])

  useEffect(() => {
    const channel = supabase
      .channel(`room-${roomId}`)
      .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'messages' },
        (payload) => setMessages(prev => [...prev, payload.new as Message])
      )
      .subscribe()

    // NO CLEANUP! Channel stays subscribed after unmount
  }, [roomId])

  return <div>{/* messages */}</div>
}
```

```typescript
// DON'T DO THIS - creating new channels without removing old ones
function switchRoom(newRoomId: string) {
  // Old channel still subscribed!
  const channel = supabase
    .channel(`room-${newRoomId}`)
    .on('postgres_changes', { event: '*', schema: 'public', table: 'messages' },
      handleMessage
    )
    .subscribe()
}
```

**Correct (proper cleanup in React):**

```typescript
function ChatRoom({ roomId }: { roomId: string }) {
  const [messages, setMessages] = useState<Message[]>([])

  useEffect(() => {
    const channel = supabase
      .channel(`room-${roomId}`)
      .on(
        'postgres_changes',
        {
          event: 'INSERT',
          schema: 'public',
          table: 'messages',
          filter: `room_id=eq.${roomId}`
        },
        (payload) => setMessages(prev => [...prev, payload.new as Message])
      )
      .subscribe()

    // CLEANUP: Unsubscribe when component unmounts or roomId changes
    return () => {
      supabase.removeChannel(channel)
    }
  }, [roomId])

  return <div>{/* messages */}</div>
}
```

**Correct (cleanup in vanilla JavaScript):**

```typescript
class RealtimeManager {
  private channels: Map<string, RealtimeChannel> = new Map()

  subscribe(channelName: string, callback: (payload: any) => void) {
    // Remove existing channel if any
    this.unsubscribe(channelName)

    const channel = supabase
      .channel(channelName)
      .on('postgres_changes', { event: '*', schema: 'public', table: 'messages' },
        callback
      )
      .subscribe()

    this.channels.set(channelName, channel)
    return channel
  }

  unsubscribe(channelName: string) {
    const channel = this.channels.get(channelName)
    if (channel) {
      supabase.removeChannel(channel)
      this.channels.delete(channelName)
    }
  }

  unsubscribeAll() {
    this.channels.forEach((channel) => {
      supabase.removeChannel(channel)
    })
    this.channels.clear()
  }
}

// Usage
const manager = new RealtimeManager()

// On page/component load
manager.subscribe('chat-room-1', handleMessage)

// On page/component unload
manager.unsubscribeAll()
```

**Correct (cleanup in Next.js with custom hook):**

```typescript
import { useEffect, useRef } from 'react'
import { RealtimeChannel } from '@supabase/supabase-js'

function useRealtimeSubscription<T>(
  channelName: string,
  table: string,
  filter: string | undefined,
  onInsert: (record: T) => void
) {
  const channelRef = useRef<RealtimeChannel | null>(null)

  useEffect(() => {
    const channel = supabase
      .channel(channelName)
      .on(
        'postgres_changes',
        {
          event: 'INSERT',
          schema: 'public',
          table,
          filter
        },
        (payload) => onInsert(payload.new as T)
      )
      .subscribe()

    channelRef.current = channel

    return () => {
      if (channelRef.current) {
        supabase.removeChannel(channelRef.current)
        channelRef.current = null
      }
    }
  }, [channelName, table, filter, onInsert])
}

// Usage in component
function OrdersPage() {
  const handleNewOrder = useCallback((order: Order) => {
    console.log('New order:', order)
  }, [])

  useRealtimeSubscription(
    'orders-channel',
    'orders',
    `status=eq.pending`,
    handleNewOrder
  )
}
```

**Verify cleanup is working:**

```typescript
// Check active channels
const channels = supabase.getChannels()
console.log('Active channels:', channels.length)

// Should be 0 or expected number after cleanup
```

**When NOT to use this pattern:**
- Application-wide subscriptions that should persist for the entire session
- Background sync services that need continuous connection

Reference: [Supabase Realtime Unsubscribe](https://supabase.com/docs/guides/realtime/subscribing-to-database-changes#unsubscribe)
