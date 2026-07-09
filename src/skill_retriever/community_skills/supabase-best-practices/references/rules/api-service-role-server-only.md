---
title: Never Expose Service Role Key to Client
impact: CRITICAL
impactDescription: Prevents complete database compromise
tags: api, security, keys, server
---

## Never Expose Service Role Key to Client

**Impact: CRITICAL (Prevents complete database compromise)**

The service role key bypasses all Row Level Security (RLS) policies and grants full admin access to your database. Never expose this key in client-side code, browser environments, or public repositories. A leaked service role key means complete database compromise.

**Incorrect (exposing service role key):**

```typescript
// DON'T DO THIS - service role key in client code
'use client'
const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY!,  // CRITICAL VULNERABILITY
)

// DON'T DO THIS - service role key in API route response
export async function GET() {
  return Response.json({
    url: process.env.SUPABASE_URL,
    key: process.env.SUPABASE_SERVICE_ROLE_KEY,  // NEVER RETURN THIS
  })
}

// DON'T DO THIS - hardcoded service role key
const adminClient = createClient(
  'https://xxx.supabase.co',
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6...',
)

// DON'T DO THIS - service role in shared utility used by client
// lib/supabase.ts (imported by both client and server)
export const supabaseAdmin = createClient(
  process.env.SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!,
)
```

**Correct (service role key server-only):**

```typescript
// Server-only admin client - separate file that's never imported by client
// lib/supabase-admin.ts (server-only)
import { createClient } from '@supabase/supabase-js'

// Validate we're on the server
if (typeof window !== 'undefined') {
  throw new Error('supabase-admin.ts must only be used on the server')
}

// Create admin client that bypasses RLS
export const supabaseAdmin = createClient(
  process.env.SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!,
  {
    auth: {
      autoRefreshToken: false,
      persistSession: false,
    },
  },
)
```

```typescript
// Next.js API Route - using admin client server-side
// app/api/admin/users/route.ts
import { supabaseAdmin } from '@/lib/supabase-admin'
import { auth } from '@clerk/nextjs/server'

export async function DELETE(req: Request) {
  // First verify the requester is an admin
  const { userId } = await auth()
  if (!userId) {
    return Response.json({ error: 'Unauthorized' }, { status: 401 })
  }

  // Check admin status from your auth provider
  const { data: adminUser } = await supabaseAdmin
    .from('admins')
    .select('id')
    .eq('clerk_user_id', userId)
    .single()

  if (!adminUser) {
    return Response.json({ error: 'Forbidden' }, { status: 403 })
  }

  // Now safe to use admin operations
  const { userId: targetUserId } = await req.json()

  const { error } = await supabaseAdmin.auth.admin.deleteUser(targetUserId)

  if (error) {
    return Response.json({ error: error.message }, { status: 500 })
  }

  return Response.json({ success: true })
}
```

**Environment Variable Security:**

```bash
# .env.local (Next.js)
# NEVER prefix service role key with NEXT_PUBLIC_
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIs...  # Server-only

# These are safe for client
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIs...
```

```typescript
// next.config.js - Ensure service role key isn't bundled
/** @type {import('next').NextConfig} */
const nextConfig = {
  // Verify no sensitive keys in client bundle
  experimental: {
    serverActions: {
      bodySizeLimit: '2mb',
    },
  },
}
```

**Legitimate Service Role Key Use Cases:**

```typescript
// 1. Background jobs / Cron tasks
// scripts/cleanup-expired-sessions.ts (server-only script)
import { supabaseAdmin } from '@/lib/supabase-admin'

async function cleanupExpiredSessions() {
  const { error } = await supabaseAdmin
    .from('sessions')
    .delete()
    .lt('expires_at', new Date().toISOString())

  if (error) throw error
}

// 2. Webhooks that need full access
// app/api/webhooks/stripe/route.ts
import { supabaseAdmin } from '@/lib/supabase-admin'

export async function POST(req: Request) {
  // Verify webhook signature first!
  const sig = req.headers.get('stripe-signature')
  const event = await verifyStripeSignature(req, sig)

  // Admin operations after verification
  if (event.type === 'checkout.session.completed') {
    await supabaseAdmin
      .from('subscriptions')
      .update({ status: 'active' })
      .eq('stripe_session_id', event.data.object.id)
  }
}

// 3. Database migrations (separate from app code)
// scripts/migrate.ts
import { supabaseAdmin } from '@/lib/supabase-admin'

async function runMigration() {
  // Only run from trusted CI/CD environment
  const { error } = await supabaseAdmin.rpc('run_migration_v2')
  if (error) throw error
}
```

**Detection and Prevention:**

```typescript
// Build-time check to prevent service role key leakage
// scripts/check-env-security.ts
function checkForLeakedSecrets() {
  const dangerousPatterns = [
    /NEXT_PUBLIC_.*SERVICE_ROLE/,
    /VITE_.*SERVICE_ROLE/,
    /REACT_APP_.*SERVICE_ROLE/,
  ]

  for (const [key] of Object.entries(process.env)) {
    for (const pattern of dangerousPatterns) {
      if (pattern.test(key)) {
        throw new Error(`SECURITY: ${key} should not be public!`)
      }
    }
  }
}
```

**When NOT to use this pattern:**
- There is NO exception - service role key must NEVER be in client code
- If you think you need it client-side, redesign your architecture

Reference: [Supabase Service Role Key](https://supabase.com/docs/guides/api/api-keys#service-role-key)
