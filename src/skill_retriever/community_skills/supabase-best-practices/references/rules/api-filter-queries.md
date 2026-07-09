---
title: Always Filter Queries Even With RLS
impact: HIGH
impactDescription: Defense in depth against data leakage
tags: api, security, rls, queries
---

## Always Filter Queries Even With RLS

**Impact: HIGH (Defense in depth against data leakage)**

Always include explicit filters in your queries to limit data retrieval, even when Row Level Security (RLS) is enabled. RLS is your safety net, not your only line of defense. Filtering queries reduces data transfer, improves performance, and provides defense in depth if RLS policies are misconfigured.

**Incorrect (relying solely on RLS):**

```typescript
// DON'T DO THIS - fetching all data and relying on RLS to filter
async function getUserProjects() {
  const { data, error } = await supabase
    .from('projects')
    .select('*')  // Fetches everything, RLS filters after

  return data
}

// DON'T DO THIS - no pagination, potential memory issues
async function getAllMessages(channelId: string) {
  const { data } = await supabase
    .from('messages')
    .select('*')
    .eq('channel_id', channelId)
    // No limit! Could return millions of rows
}
```

**Correct (explicit filtering with RLS as backup):**

```typescript
// Always filter by user even though RLS enforces it
async function getUserProjects(userId: string) {
  const { data, error } = await supabase
    .from('projects')
    .select('id, name, created_at')  // Only select needed columns
    .eq('user_id', userId)           // Explicit filter (even with RLS)
    .order('created_at', { ascending: false })
    .limit(50)                        // Always paginate

  if (error) {
    throw new Error(`Failed to fetch projects: ${error.message}`)
  }

  return data
}

// Paginated query with explicit filters
async function getMessages(
  channelId: string,
  cursor?: string,
  pageSize: number = 50
) {
  let query = supabase
    .from('messages')
    .select('id, content, user_id, created_at')
    .eq('channel_id', channelId)
    .order('created_at', { ascending: false })
    .limit(pageSize)

  if (cursor) {
    query = query.lt('created_at', cursor)
  }

  const { data, error } = await query

  return {
    messages: data ?? [],
    nextCursor: data?.at(-1)?.created_at,
  }
}
```

**Best Practices for Query Filtering:**

```typescript
// 1. Select only needed columns
const { data } = await supabase
  .from('users')
  .select('id, name, avatar_url')  // NOT select('*')

// 2. Always include user context filters
const { data } = await supabase
  .from('documents')
  .select('*')
  .eq('organization_id', orgId)   // Scope to organization
  .eq('created_by', userId)       // Scope to user

// 3. Use range queries for large datasets
const { data } = await supabase
  .from('logs')
  .select('*')
  .gte('created_at', startDate)
  .lte('created_at', endDate)
  .limit(1000)

// 4. Use count queries instead of fetching all data
const { count, error } = await supabase
  .from('notifications')
  .select('*', { count: 'exact', head: true })
  .eq('user_id', userId)
  .eq('read', false)
```

**Why This Matters:**

| Issue | Without Filtering | With Filtering |
|-------|------------------|----------------|
| Data transfer | Full table scan | Minimal data |
| Performance | Slow queries | Fast queries |
| Security | Single layer (RLS) | Defense in depth |
| Memory usage | Potential OOM | Predictable |
| Cost | High egress | Lower egress |

**When NOT to use this pattern:**
- Admin dashboards that legitimately need all data (but still paginate)
- Export functions where full data is required (use streaming)
- Aggregation queries that need full dataset access

Reference: [Supabase Querying Data](https://supabase.com/docs/guides/database/tables#querying-data)
