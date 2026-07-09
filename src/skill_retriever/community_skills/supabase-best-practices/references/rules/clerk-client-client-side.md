---
title: Client-Side Supabase Client with Clerk
impact: CRITICAL
impactDescription: Secure client-side authentication pattern
tags: clerk, security, authentication, client, react
---

## Client-Side Supabase Client with Clerk

**Impact: CRITICAL (Secure client-side authentication pattern)**

Use the `useSession()` hook from Clerk for client-side Supabase clients. This ensures tokens are properly managed with React's rendering lifecycle and automatically refresh when needed.

**Incorrect (manual token handling):**

```typescript
// DON'T DO THIS - manual token management
'use client'
import { useAuth } from '@clerk/nextjs'
import { createClient } from '@supabase/supabase-js'
import { useEffect, useState } from 'react'

export function useSupabaseClient() {
  const { getToken } = useAuth()
  const [supabase, setSupabase] = useState(null)

  useEffect(() => {
    async function init() {
      const token = await getToken()
      // DON'T: Creating client with stale token
      const client = createClient(url, key, {
        global: { headers: { Authorization: `Bearer ${token}` } }
      })
      setSupabase(client)
    }
    init()
  }, [])

  return supabase
}
```

**Correct (useSession with accessToken callback):**

```typescript
// lib/supabase/client.ts
'use client'
import { useSession } from '@clerk/nextjs'
import { createClient } from '@supabase/supabase-js'
import { useMemo } from 'react'

export function useSupabaseClient() {
  const { session } = useSession()

  return useMemo(() => {
    return createClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_KEY!,
      {
        async accessToken() {
          return session?.getToken() ?? null
        },
      },
    )
  }, [session])
}
```

**Usage in Client Components:**

```typescript
// components/PostList.tsx
'use client'
import { useSupabaseClient } from '@/lib/supabase/client'
import { useEffect, useState } from 'react'

export function PostList() {
  const supabase = useSupabaseClient()
  const [posts, setPosts] = useState([])

  useEffect(() => {
    async function fetchPosts() {
      const { data } = await supabase
        .from('posts')
        .select('*')

      if (data) setPosts(data)
    }

    fetchPosts()
  }, [supabase])

  return (
    <ul>
      {posts.map(post => (
        <li key={post.id}>{post.title}</li>
      ))}
    </ul>
  )
}
```

**With Real-time Subscriptions:**

```typescript
// components/RealtimePosts.tsx
'use client'
import { useSupabaseClient } from '@/lib/supabase/client'
import { useEffect, useState } from 'react'

export function RealtimePosts() {
  const supabase = useSupabaseClient()
  const [posts, setPosts] = useState([])

  useEffect(() => {
    // Initial fetch
    supabase.from('posts').select('*').then(({ data }) => {
      if (data) setPosts(data)
    })

    // Subscribe to changes
    const channel = supabase
      .channel('posts-changes')
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'posts' },
        (payload) => {
          if (payload.eventType === 'INSERT') {
            setPosts(prev => [...prev, payload.new])
          }
        }
      )
      .subscribe()

    return () => {
      supabase.removeChannel(channel)
    }
  }, [supabase])

  return <PostList posts={posts} />
}
```

**Why this matters:**

1. **Session reactivity**: The client updates automatically when the Clerk session changes.

2. **Automatic token refresh**: `session.getToken()` handles token refresh transparently.

3. **Proper memoization**: Using `useMemo` prevents unnecessary client recreation.

4. **Null safety**: Returns `null` token when not authenticated, which Supabase handles correctly.

**When NOT to use this pattern:**

- Server Components (use `clerk-client-server-side` pattern)
- Server Actions (use `clerk-client-server-side` pattern)
- Static pages that don't need authentication

Reference: [Clerk Supabase Integration](https://clerk.com/docs/integrations/databases/supabase)
