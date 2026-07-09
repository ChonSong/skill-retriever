---
title: Avoid Deprecated JWT Templates
impact: CRITICAL
impactDescription: Prevents JWT secret sharing security vulnerability
tags: clerk, security, authentication, jwt, deprecated
---

## Avoid Deprecated JWT Templates

**Impact: CRITICAL (Prevents JWT secret sharing security vulnerability)**

Never use the deprecated Clerk JWT template integration. As of April 2025, this approach is deprecated because it requires sharing your Supabase project's JWT secret with Clerk, creating a significant security risk.

**Incorrect (deprecated JWT template approach):**

```typescript
// DON'T DO THIS - deprecated and insecure
import { useAuth } from '@clerk/nextjs'
import { createClient } from '@supabase/supabase-js'

function MyComponent() {
  const { getToken } = useAuth()

  async function fetchData() {
    // DON'T: Using JWT template
    const token = await getToken({ template: 'supabase' })

    const supabase = createClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_KEY!,
      {
        global: {
          headers: {
            Authorization: `Bearer ${token}`
          }
        }
      }
    )

    return supabase.from('posts').select('*')
  }
}
```

**Why JWT templates are dangerous:**

```
┌─────────────────────────────────────────────────────────────────┐
│                    DEPRECATED APPROACH                          │
│                                                                 │
│  Your App ──► Clerk (with your JWT secret) ──► Supabase        │
│                        ▲                                        │
│                        │                                        │
│              JWT secret shared with                             │
│              third-party service!                               │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    RECOMMENDED APPROACH                         │
│                                                                 │
│  Your App ──► Clerk (own keys) ──► Supabase (verifies with     │
│                                    Clerk's public key)          │
│                                                                 │
│              Asymmetric cryptography -                          │
│              secret never shared!                               │
└─────────────────────────────────────────────────────────────────┘
```

**Correct (Third-Party Auth with native tokens):**

```typescript
// Server-side
import { auth } from '@clerk/nextjs/server'
import { createClient } from '@supabase/supabase-js'

export function createServerSupabaseClient() {
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_KEY!,
    {
      async accessToken() {
        // Use native session token, NOT a template
        return (await auth()).getToken()
      },
    },
  )
}
```

```typescript
// Client-side
'use client'
import { useSession } from '@clerk/nextjs'
import { createClient } from '@supabase/supabase-js'

export function useSupabaseClient() {
  const { session } = useSession()

  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_KEY!,
    {
      async accessToken() {
        // Use native session token, NOT a template
        return session?.getToken() ?? null
      },
    },
  )
}
```

**Migration guide from JWT templates:**

1. **Enable Third-Party Auth in Supabase:**

```toml
# supabase/config.toml
[auth.third_party.clerk]
enabled = true
domain = "your-instance.clerk.accounts.dev"
```

2. **Update Clerk session customization:**

Remove the JWT template and add claims directly:

```json
{
  "role": "authenticated"
}
```

3. **Update your Supabase client code:**

Replace:
```typescript
// Old
const token = await getToken({ template: 'supabase' })
```

With:
```typescript
// New
const token = await session?.getToken()
// Or in accessToken callback
async accessToken() {
  return session?.getToken() ?? null
}
```

4. **Remove JWT template from Clerk:**

Delete the `supabase` JWT template from Clerk Dashboard.

5. **Rotate your Supabase JWT secret:**

Since the secret was shared, rotate it:
- Go to Supabase Dashboard > Settings > API
- Generate new JWT secret
- Update any services still using the old secret

**Security comparison:**

| Aspect | JWT Templates (Old) | Third-Party Auth (New) |
|--------|---------------------|------------------------|
| JWT Secret | Shared with Clerk | Never leaves Supabase |
| Key Type | Symmetric | Asymmetric |
| Security Risk | High | Low |
| Official Support | Deprecated | Recommended |

**Why this matters:**

1. **Secret exposure**: Sharing JWT secrets with third parties is a security anti-pattern.

2. **Key rotation**: If Clerk is compromised, your Supabase project is also at risk.

3. **Compliance**: Many security standards prohibit sharing cryptographic secrets.

4. **Future-proof**: The new approach is the officially supported method.

**When NOT to use this pattern:**

- There is no valid reason to use JWT templates for new projects
- Legacy projects should plan migration to Third-Party Auth

Reference: [Supabase + Clerk Integration](https://supabase.com/docs/guides/auth/third-party/clerk)
