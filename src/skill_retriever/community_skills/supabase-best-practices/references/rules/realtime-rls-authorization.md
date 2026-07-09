---
title: Enable RLS for Realtime Postgres Changes
impact: CRITICAL
impactDescription: Without RLS, all database changes are broadcast to all subscribers
tags: realtime, security, rls, postgres-changes
---

## Enable RLS for Realtime Postgres Changes

**Impact: CRITICAL (Without RLS, all database changes are broadcast to all subscribers)**

When using Postgres Changes for realtime subscriptions, RLS policies determine which changes each user receives. Without proper RLS, users may receive changes for data they shouldn't access, leading to data leaks.

**Incorrect (no RLS on realtime-enabled table):**

```sql
-- DON'T DO THIS - all changes broadcast to all subscribers
CREATE TABLE messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  room_id UUID NOT NULL,
  user_id UUID NOT NULL,
  content TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Adding to realtime without RLS = data leak
ALTER PUBLICATION supabase_realtime ADD TABLE messages;

-- NO RLS POLICIES = everyone sees all messages!
```

```typescript
// All users will receive ALL message changes
const channel = supabase
  .channel('messages')
  .on('postgres_changes', { event: '*', schema: 'public', table: 'messages' },
    (payload) => {
      // User receives messages from ALL rooms - security issue!
      console.log('Message:', payload)
    }
  )
  .subscribe()
```

**Correct (RLS controls realtime access):**

```sql
-- Create table with RLS enabled
CREATE TABLE messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  room_id UUID NOT NULL REFERENCES rooms(id),
  user_id UUID NOT NULL,
  content TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS FIRST
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

-- Create policy for room members only
CREATE POLICY "room_members_see_messages"
ON messages
FOR SELECT
TO authenticated
USING (
  EXISTS (
    SELECT 1 FROM room_members rm
    WHERE rm.room_id = messages.room_id
    AND rm.user_id = (SELECT auth.uid())
  )
);

-- Create index for RLS performance
CREATE INDEX idx_room_members_lookup
ON room_members(room_id, user_id);

-- NOW add to realtime publication
ALTER PUBLICATION supabase_realtime ADD TABLE messages;
```

```typescript
// Users only receive messages from rooms they're members of
const channel = supabase
  .channel('my-messages')
  .on(
    'postgres_changes',
    {
      event: 'INSERT',
      schema: 'public',
      table: 'messages',
      filter: `room_id=eq.${currentRoomId}` // Optional: further filter client-side
    },
    (payload) => {
      // Only receives messages user is authorized to see
      console.log('New message:', payload.new)
    }
  )
  .subscribe()
```

**Verify RLS is working:**

```typescript
// Test by subscribing as different users
// User A should only see their authorized data
// User B should only see their authorized data

// Check Realtime logs in Supabase Dashboard for policy violations
```

**Important considerations:**

1. **RLS is evaluated on the server** - Changes are filtered before being sent to clients
2. **Client filters are additional** - The `filter` option in `postgres_changes` is client-side convenience, not security
3. **Publication includes all columns** - RLS controls row access, not column access
4. **Performance matters** - Optimize RLS policies with indexes

**When NOT to use this pattern:**
- Public tables where all data should be visible to everyone
- Internal tables only accessed via service role (not via realtime)

Reference: [Supabase Realtime Authorization](https://supabase.com/docs/guides/realtime/authorization)
