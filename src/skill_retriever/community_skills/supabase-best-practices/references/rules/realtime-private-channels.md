---
title: Use Private Channels for Authenticated Communication
impact: HIGH
impactDescription: Prevents unauthorized access to realtime data
tags: realtime, security, channels, authentication
---

## Use Private Channels for Authenticated Communication

**Impact: HIGH (Prevents unauthorized data access)**

When building realtime features with Supabase, use private channels to ensure only authenticated users can subscribe to sensitive data streams. Private channels require a valid JWT token and can leverage RLS policies for fine-grained access control.

**Incorrect (using public broadcast channel for sensitive data):**

```typescript
// DON'T DO THIS - anyone can subscribe to broadcast channels
const channel = supabase.channel('orders')

channel
  .on('broadcast', { event: 'new_order' }, (payload) => {
    console.log('New order:', payload)
  })
  .subscribe()

// Sending sensitive data over public channel
channel.send({
  type: 'broadcast',
  event: 'new_order',
  payload: { order_id: 123, customer_email: 'user@example.com' }
})
```

**Correct (using private channels with RLS):**

```typescript
// Use Postgres Changes which respect RLS policies
const channel = supabase
  .channel('orders-changes')
  .on(
    'postgres_changes',
    {
      event: '*',
      schema: 'public',
      table: 'orders',
      filter: `user_id=eq.${userId}` // Additional client-side filter
    },
    (payload) => {
      console.log('Order change:', payload)
    }
  )
  .subscribe()
```

**For broadcast with authorization, use Realtime Authorization:**

```typescript
// Server-side: Create authorized channel
const channel = supabase.channel('private-room', {
  config: {
    private: true // Requires valid JWT
  }
})

// Client must have valid session to subscribe
channel
  .on('broadcast', { event: 'message' }, (payload) => {
    console.log('Private message:', payload)
  })
  .subscribe(async (status) => {
    if (status === 'SUBSCRIBED') {
      // User is authenticated and subscribed
    }
  })
```

**RLS policy for realtime authorization:**

```sql
-- Enable realtime for the table
ALTER PUBLICATION supabase_realtime ADD TABLE orders;

-- RLS policy controls who sees which changes
CREATE POLICY "users_see_own_orders"
ON orders
FOR SELECT
TO authenticated
USING (user_id = (SELECT auth.uid()));
```

**When NOT to use this pattern:**
- Public data that should be visible to everyone (e.g., live sports scores)
- Presence features that intentionally show all users in a room
- Development/testing environments with non-sensitive data

Reference: [Supabase Realtime Authorization](https://supabase.com/docs/guides/realtime/authorization)
