---
title: Use Publishable API Keys for Client Applications
impact: HIGH
impactDescription: Prevents accidental secret exposure
tags: api, security, keys, client
---

## Use Publishable API Keys for Client Applications

**Impact: HIGH (Prevents accidental secret exposure)**

Always use Supabase publishable keys (anon key or the newer `sb_publishable_*` keys) for client-side applications. These keys are safe to expose in browser code and rely on Row Level Security (RLS) for data protection. Never use the service role key in client code.

**Incorrect (using wrong keys or hardcoding):**

```typescript
// DON'T DO THIS - service role key in client code
const supabase = createClient(
  'https://xxx.supabase.co',
  'eyJhbGciOiJIUzI1NiIs...',  // This is the SERVICE_ROLE key!
)

// DON'T DO THIS - hardcoded keys without validation
const supabase = createClient(
  process.env.SUPABASE_URL,       // Missing NEXT_PUBLIC_ prefix
  process.env.SUPABASE_ANON_KEY,  // Won't work in browser!
)

// DON'T DO THIS - mixing up key types
// Using service role key from environment variable in client
const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!,  // WRONG! Server-only key
)
```

**Correct (using publishable keys properly):**

```typescript
// Client-side: Use NEXT_PUBLIC_ prefixed environment variables
// These are safe to expose in the browser
const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
)

// Or with the newer publishable keys (recommended for new projects)
const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!,  // sb_publishable_...
)
```

**Environment Variables Setup:**

```bash
# .env.local (Next.js)
# Public keys - safe for client-side (prefix with NEXT_PUBLIC_)
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIs...

# Secret keys - server-only (NO prefix)
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIs...
```

```bash
# .env (Vite)
# Public keys - safe for client-side (prefix with VITE_)
VITE_SUPABASE_URL=https://xxx.supabase.co
VITE_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIs...
```

**Key Types and Their Usage:**

| Key Type | Format | Client Safe | Server Safe | Respects RLS |
|----------|--------|-------------|-------------|--------------|
| Anon Key | `eyJhbG...` (JWT) | ✅ Yes | ✅ Yes | ✅ Yes |
| Publishable Key | `sb_publishable_...` | ✅ Yes | ✅ Yes | ✅ Yes |
| Service Role Key | `eyJhbG...` (JWT) | ❌ NO | ✅ Yes | ❌ Bypasses |

**Framework-Specific Patterns:**

```typescript
// Next.js App Router - Client Component
'use client'
import { createBrowserClient } from '@supabase/ssr'

export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
  )
}

// Next.js App Router - Server Component
import { createServerClient } from '@supabase/ssr'
import { cookies } from 'next/headers'

export async function createServerSupabaseClient() {
  const cookieStore = await cookies()

  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,  // Still anon key!
    {
      cookies: {
        getAll() {
          return cookieStore.getAll()
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value, options }) =>
            cookieStore.set(name, value, options)
          )
        },
      },
    },
  )
}
```

**Validation Pattern:**

```typescript
// Validate keys at startup to catch misconfigurations early
function validateEnvironment() {
  const requiredPublicVars = [
    'NEXT_PUBLIC_SUPABASE_URL',
    'NEXT_PUBLIC_SUPABASE_ANON_KEY',
  ]

  for (const varName of requiredPublicVars) {
    if (!process.env[varName]) {
      throw new Error(`Missing required environment variable: ${varName}`)
    }
  }

  // Ensure service role key is NOT exposed publicly
  if (typeof window !== 'undefined' && process.env.SUPABASE_SERVICE_ROLE_KEY) {
    console.error('WARNING: Service role key may be exposed to client!')
  }
}
```

**When NOT to use this pattern:**
- Server-side admin operations that need to bypass RLS (use service role key server-side only)
- Background jobs and cron tasks running on the server
- Database migrations and seeding scripts

Reference: [Supabase API Keys](https://supabase.com/docs/guides/api/api-keys)
