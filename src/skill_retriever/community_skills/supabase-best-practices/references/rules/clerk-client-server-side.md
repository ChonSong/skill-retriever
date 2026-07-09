---
title: Server-Side Supabase Client with Clerk
impact: CRITICAL
impactDescription: Secure server-side authentication pattern
tags: clerk, security, authentication, server, nextjs
---

## Server-Side Supabase Client with Clerk

**Impact: CRITICAL (Secure server-side authentication pattern)**

Use the `accessToken` callback pattern for server-side Supabase clients. This ensures tokens are fetched fresh for each request and properly integrated with Clerk's authentication.

**Incorrect (manual token handling):**

```typescript
// lib/supabase/server.ts - DON'T DO THIS
import { auth } from '@clerk/nextjs/server'
import { createClient } from '@supabase/supabase-js'

export async function createServerSupabaseClient() {
  const { getToken } = await auth()
  const token = await getToken()

  // DON'T: Manual header injection
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_KEY!,
    {
      global: {
        headers: { Authorization: `Bearer ${token}` }
      }
    }
  )
}
```

**Correct (accessToken callback pattern):**

```typescript
// lib/supabase/server.ts
import { auth } from '@clerk/nextjs/server'
import { createClient } from '@supabase/supabase-js'

export function createServerSupabaseClient() {
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_KEY!,
    {
      async accessToken() {
        return (await auth()).getToken()
      },
    },
  )
}
```

**Usage in Server Components:**

```typescript
// app/dashboard/page.tsx
import { createServerSupabaseClient } from '@/lib/supabase/server'

export default async function DashboardPage() {
  const supabase = createServerSupabaseClient()

  // RLS policies will automatically apply based on Clerk user
  const { data: posts } = await supabase
    .from('posts')
    .select('*')

  return <PostList posts={posts} />
}
```

**Usage in Server Actions:**

```typescript
// app/actions.ts
'use server'

import { createServerSupabaseClient } from '@/lib/supabase/server'

export async function createPost(formData: FormData) {
  const supabase = createServerSupabaseClient()

  const { data, error } = await supabase
    .from('posts')
    .insert({ title: formData.get('title') })
    .select()
    .single()

  if (error) throw error
  return data
}
```

**Usage in Route Handlers:**

```typescript
// app/api/posts/route.ts
import { createServerSupabaseClient } from '@/lib/supabase/server'
import { NextResponse } from 'next/server'

export async function GET() {
  const supabase = createServerSupabaseClient()

  const { data, error } = await supabase
    .from('posts')
    .select('*')

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 })
  }

  return NextResponse.json(data)
}
```

**Why this matters:**

1. **Automatic token refresh**: The callback is called for each request, ensuring fresh tokens.

2. **Lazy evaluation**: Token is only fetched when a database operation is performed.

3. **Proper async handling**: Works correctly with Next.js App Router's async patterns.

4. **RLS integration**: Clerk's user ID (`sub` claim) is automatically available as `auth.uid()` in RLS policies.

**When NOT to use this pattern:**

- Client-side components (use `clerk-client-client-side` pattern instead)
- Edge Functions (use `clerk-edge-function` pattern)

Reference: [Clerk Supabase Integration](https://clerk.com/docs/integrations/databases/supabase)
