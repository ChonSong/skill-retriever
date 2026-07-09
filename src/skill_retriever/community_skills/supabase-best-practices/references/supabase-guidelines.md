# Supabase Best Practices - Complete Guidelines

**Version:** 1.0.0
**Last Updated:** January 2026

A comprehensive guide for building secure, performant Supabase applications with Clerk authentication. This document consolidates 38 rules across 10 categories, organized by priority and impact.

---

## Table of Contents

1. [Row Level Security (CRITICAL)](#1-row-level-security-critical)
2. [Clerk Integration (CRITICAL)](#2-clerk-integration-critical)
3. [Database Security (HIGH)](#3-database-security-high)
4. [Authentication Patterns (HIGH)](#4-authentication-patterns-high)
5. [API Security (HIGH)](#5-api-security-high)
6. [Storage Security (MEDIUM-HIGH)](#6-storage-security-medium-high)
7. [Realtime Security (MEDIUM)](#7-realtime-security-medium)
8. [Edge Functions (MEDIUM)](#8-edge-functions-medium)
9. [Testing (MEDIUM)](#9-testing-medium)
10. [Performance Benchmarks](#10-performance-benchmarks)
11. [Quick Reference Checklist](#11-quick-reference-checklist)

---

## 1. Row Level Security (CRITICAL)

RLS is the foundation of Supabase security. Properly configured policies ensure data isolation at the database level.

### 1.1 Always Enable RLS on Public Schema Tables

**Impact: CRITICAL (Prevents unauthorized data access)**

Any table in the public schema is accessible via the API. Without RLS, all authenticated users can read and modify all data.

```sql
-- Create table
CREATE TABLE public.user_profiles (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES auth.users(id),
  full_name text,
  email text
);

-- Enable RLS - CRITICAL
ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;

-- Create policy for users to access only their own data
CREATE POLICY "users_can_view_own_profile"
ON public.user_profiles
FOR SELECT
TO authenticated
USING ((SELECT auth.uid()) = user_id);
```

### 1.2 Wrap Auth Functions with SELECT

**Impact: CRITICAL (94.97% performance improvement - 179ms to 9ms)**

PostgreSQL evaluates RLS policy expressions for each row. Wrapping `auth.uid()` or `auth.jwt()` with `(SELECT ...)` forces single evaluation and caching.

```sql
-- Incorrect: auth.uid() called per row
CREATE POLICY "users_own_data" ON documents
FOR SELECT TO authenticated
USING (auth.uid() = user_id);

-- Correct: function evaluated once
CREATE POLICY "users_own_data" ON documents
FOR SELECT TO authenticated
USING ((SELECT auth.uid()) = user_id);
```

### 1.3 Add Indexes on RLS Policy Columns

**Impact: CRITICAL (99.94% performance improvement - 171ms to <0.1ms)**

Without indexes, PostgreSQL performs full table scans to evaluate policies.

```sql
-- Add index on the column used in RLS policy
CREATE INDEX idx_documents_user_id ON documents(user_id);

-- For multi-column policies
CREATE INDEX idx_projects_organization_id ON projects(organization_id);
CREATE INDEX idx_projects_owner_id ON projects(owner_id);
```

### 1.4 Specify Roles with TO Clause

**Impact: CRITICAL (99.78% performance improvement)**

Always specify `TO authenticated` or `TO anon` to prevent policy evaluation for irrelevant roles.

```sql
-- Incorrect: applies to all roles
CREATE POLICY "view_own" ON profiles
FOR SELECT USING ((SELECT auth.uid()) = user_id);

-- Correct: only evaluated for authenticated users
CREATE POLICY "view_own" ON profiles
FOR SELECT
TO authenticated
USING ((SELECT auth.uid()) = user_id);
```

### 1.5 Use SECURITY DEFINER for Complex Policies

**Impact: CRITICAL (99.993% performance improvement - 178,000ms to 12ms)**

For policies requiring joins to other tables, use SECURITY DEFINER functions to execute with elevated privileges efficiently.

```sql
-- Create helper function with SECURITY DEFINER
CREATE OR REPLACE FUNCTION private.get_user_org_ids()
RETURNS uuid[]
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT ARRAY(
    SELECT organization_id
    FROM organization_members
    WHERE user_id = auth.uid()
  );
$$;

-- Use in policy
CREATE POLICY "org_access" ON documents
FOR SELECT TO authenticated
USING (
  organization_id = ANY((SELECT private.get_user_org_ids()))
);
```

### 1.6 Minimize Joins in RLS Policies

**Impact: HIGH (99.78% performance improvement - 9,000ms to 20ms)**

Avoid complex joins in policies. Prefer array-based lookups or SECURITY DEFINER functions.

```sql
-- Avoid: nested join
CREATE POLICY "org_access" ON documents
FOR SELECT TO authenticated
USING (
  EXISTS (
    SELECT 1 FROM org_members om
    JOIN orgs o ON o.id = om.org_id
    WHERE om.user_id = auth.uid()
    AND o.id = documents.org_id
  )
);

-- Prefer: array-based lookup
CREATE POLICY "org_access" ON documents
FOR SELECT TO authenticated
USING (
  org_id = ANY((SELECT private.get_user_org_ids()))
);
```

### 1.7 Use RESTRICTIVE Policies for Layered Security

**Impact: HIGH (Enables defense in depth)**

RESTRICTIVE policies must ALL pass for access. Use for additional constraints like MFA requirements.

```sql
-- Permissive: users see own data
CREATE POLICY "users_own_data" ON sensitive_data
AS PERMISSIVE
FOR SELECT TO authenticated
USING ((SELECT auth.uid()) = user_id);

-- Restrictive: require MFA
CREATE POLICY "require_mfa" ON sensitive_data
AS RESTRICTIVE
FOR SELECT TO authenticated
USING ((SELECT auth.jwt()->>'aal') = 'aal2');
```

---

## 2. Clerk Integration (CRITICAL)

Secure integration patterns for Clerk authentication with Supabase using Third-Party Auth.

### 2.1 Use Third-Party Auth Integration

**Impact: CRITICAL (Eliminates JWT secret sharing)**

Always use Supabase's native Third-Party Auth instead of deprecated JWT templates.

```toml
# supabase/config.toml (local development)
[auth.third_party.clerk]
enabled = true
domain = "your-instance.clerk.accounts.dev"
```

For production, configure in Supabase Dashboard:
1. Go to **Authentication** > **Sign In / Up**
2. Click **Add provider** > **Third-party Auth**
3. Select **Clerk** and enter your domain

### 2.2 Server-Side Supabase Client

**Impact: CRITICAL (Secure server-side authentication)**

Use the `accessToken` callback pattern for server-side clients.

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

### 2.3 Client-Side Supabase Client

**Impact: CRITICAL (Secure client-side authentication)**

Use `useSession()` hook for client-side token injection.

```typescript
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
        return session?.getToken() ?? null
      },
    },
  )
}
```

### 2.4 Configure Role Claim

**Impact: CRITICAL (Required for RLS)**

Ensure Clerk session tokens include the `role` claim with value `authenticated`.

Configure in Clerk Dashboard:
1. Go to **Sessions** > **Customize session token**
2. Add the claim:

```json
{
  "role": "authenticated"
}
```

### 2.5 Organization-Based RLS Policies

**Impact: HIGH (Multi-tenant security)**

Use Clerk's organization claims for multi-tenant RLS policies.

```sql
CREATE POLICY "org_members_can_access"
ON org_data
FOR SELECT TO authenticated
USING (
  organization_id = (
    SELECT COALESCE(
      auth.jwt()->>'org_id',
      auth.jwt()->'o'->>'id'
    )
  )
);

-- Admin-only operations
CREATE POLICY "org_admins_can_modify"
ON org_data
FOR UPDATE TO authenticated
USING (
  (
    (SELECT auth.jwt()->>'org_role') = 'org:admin'
    OR (SELECT auth.jwt()->'o'->>'rol') = 'admin'
  )
  AND organization_id = (
    SELECT COALESCE(auth.jwt()->>'org_id', auth.jwt()->'o'->>'id')
  )
);
```

### 2.6 MFA Enforcement in Policies

**Impact: HIGH (Enhanced security for sensitive operations)**

Use restrictive policies to enforce MFA using the `aal` claim.

```sql
CREATE POLICY "require_mfa_for_updates"
ON sensitive_table
AS RESTRICTIVE
FOR UPDATE TO authenticated
USING ((SELECT auth.jwt()->>'aal') = 'aal2');
```

### 2.7 Never Use Deprecated JWT Templates

**Impact: CRITICAL (Security risk)**

The JWT template approach shares your project's JWT secret with Clerk.

```typescript
// INCORRECT - deprecated approach
const token = await getToken({ template: 'supabase' })

// CORRECT - use native session tokens
const token = await session.getToken()
```

---

## 3. Database Security (HIGH)

Schema design patterns and database-level security configurations.

### 3.1 Use Versioned Migrations

**Impact: HIGH (Reproducible and auditable changes)**

All schema changes should be managed through versioned migration files.

```sql
-- supabase/migrations/20260118000000_add_orders.sql
BEGIN;

CREATE TABLE public.orders (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE,
  total_amount numeric(10,2) NOT NULL,
  created_at timestamptz DEFAULT now()
);

ALTER TABLE public.orders ENABLE ROW LEVEL SECURITY;

CREATE POLICY "users_own_orders"
ON public.orders
FOR ALL TO authenticated
USING ((SELECT auth.uid()) = user_id)
WITH CHECK ((SELECT auth.uid()) = user_id);

COMMIT;
```

```bash
# Apply migrations
supabase db push
supabase migration up
supabase migration list
```

### 3.2 Schema Design with Security Boundaries

**Impact: HIGH (Prevents data leaks)**

Separate public API-accessible tables from private internal tables.

```sql
-- Private schema for internal data
CREATE SCHEMA IF NOT EXISTS private;

-- Private tables not accessible via API
CREATE TABLE private.audit_logs (...);
CREATE TABLE private.system_config (...);

-- Public schema for API-accessible data with RLS
CREATE TABLE public.user_profiles (...);
ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;
```

### 3.3 Foreign Keys with Proper CASCADE Actions

**Impact: HIGH (Data integrity)**

Use foreign key constraints with appropriate cascade behavior.

```sql
CREATE TABLE orders (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  product_id uuid REFERENCES products(id) ON DELETE SET NULL
);
```

### 3.4 Secure Database Triggers

**Impact: HIGH (Prevents privilege escalation)**

Use SECURITY DEFINER for trigger functions and set explicit search_path.

```sql
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  INSERT INTO public.profiles (user_id, email)
  VALUES (NEW.id, NEW.email);
  RETURN NEW;
END;
$$;
```

### 3.5 Use SECURITY INVOKER for Views

**Impact: HIGH (Ensures RLS enforcement)**

Views in public schema should use SECURITY INVOKER to respect caller's RLS.

```sql
CREATE VIEW public.user_dashboard
WITH (security_invoker = on)
AS
SELECT p.*, o.total_orders, o.total_spent
FROM profiles p
LEFT JOIN order_summaries o ON o.user_id = p.user_id;
```

---

## 4. Authentication Patterns (HIGH)

JWT handling and secure authentication flows.

### 4.1 Validate JWT Claims

**Impact: HIGH (Prevents authorization bypass)**

Always validate JWT claims server-side before authorization decisions.

```typescript
async function getUserData(req: Request) {
  const { data: { user }, error } = await supabase.auth.getUser()

  if (error || !user) {
    throw new Error('Authentication required')
  }

  // Validate required claims
  if (!user.aud || user.aud !== 'authenticated') {
    throw new Error('Invalid token audience')
  }

  // Check role from app_metadata (not user_metadata!)
  const role = user.app_metadata?.role
  if (role !== 'admin') {
    throw new Error('Admin access required')
  }

  return getAllUsers()
}
```

### 4.2 Treat user_metadata as Untrusted

**Impact: HIGH (Prevents privilege escalation)**

Users can modify their own `user_metadata`. Never use it for authorization.

```typescript
// INCORRECT - user can set their own role
const role = user.user_metadata?.role

// CORRECT - use app_metadata (server-controlled)
const role = user.app_metadata?.role
```

### 4.3 Use app_metadata for Authorization

**Impact: HIGH (Server-controlled authorization)**

Store authorization data in `app_metadata` which only server can modify.

```typescript
// Server-side: Set app_metadata
await supabase.auth.admin.updateUserById(userId, {
  app_metadata: { role: 'admin', permissions: ['read', 'write'] }
})
```

```sql
-- RLS using app_metadata
CREATE POLICY "admins_only"
ON admin_data
FOR ALL TO authenticated
USING ((SELECT auth.jwt()->'app_metadata'->>'role') = 'admin');
```

---

## 5. API Security (HIGH)

Proper key management and query filtering.

### 5.1 Never Expose Service Role Key to Client

**Impact: CRITICAL (Prevents complete database compromise)**

The service role key bypasses all RLS and grants full admin access.

```typescript
// Server-only admin client
// lib/supabase-admin.ts
if (typeof window !== 'undefined') {
  throw new Error('supabase-admin.ts must only be used on the server')
}

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

```bash
# .env.local
# NEVER prefix service role key with NEXT_PUBLIC_
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIs...  # Server-only

# These are safe for client
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIs...
```

### 5.2 Always Filter Queries Even with RLS

**Impact: HIGH (Defense in depth)**

RLS is your safety net, not your only defense. Filter queries to optimize and provide defense in depth.

```typescript
// Instead of relying only on RLS
const { data } = await supabase.from('documents').select('*')

// Filter explicitly for efficiency and security
const { data } = await supabase
  .from('documents')
  .select('*')
  .eq('user_id', userId)
```

### 5.3 Use Publishable API Keys Correctly

**Impact: HIGH (Proper key management)**

Use the correct key type for each context.

| Key Type | Use Case | Client-Safe |
|----------|----------|-------------|
| `anon` key | Client-side, respects RLS | Yes |
| `service_role` key | Server-side admin operations | **NO** |

---

## 6. Storage Security (MEDIUM-HIGH)

Bucket configuration and file access patterns.

### 6.1 Create RLS Policies for Storage

**Impact: CRITICAL (Prevents unauthorized file access)**

Storage uses RLS on `storage.objects` table.

```sql
-- Allow authenticated users to upload to their own folder
CREATE POLICY "Users can upload to own folder"
ON storage.objects
FOR INSERT TO authenticated
WITH CHECK (
  bucket_id = 'user-files' AND
  (storage.foldername(name))[1] = (SELECT auth.uid()::text)
);

-- Allow users to read their own files
CREATE POLICY "Users can read own files"
ON storage.objects
FOR SELECT TO authenticated
USING (
  bucket_id = 'user-files' AND
  (storage.foldername(name))[1] = (SELECT auth.uid()::text)
);
```

### 6.2 Configure Bucket Security

**Impact: HIGH (Proper access control)**

```typescript
// Create private bucket (default)
await supabase.storage.createBucket('private-docs', {
  public: false,
  fileSizeLimit: 10485760, // 10MB
  allowedMimeTypes: ['application/pdf', 'image/*']
})

// Public bucket for assets (use sparingly)
await supabase.storage.createBucket('public-assets', {
  public: true
})
```

### 6.3 Use Signed URLs for Private Files

**Impact: HIGH (Time-limited secure access)**

```typescript
// Generate signed URL (expires in 1 hour)
const { data } = await supabase.storage
  .from('private-docs')
  .createSignedUrl('path/to/file.pdf', 3600)

// Download signed URL (includes download header)
const { data } = await supabase.storage
  .from('private-docs')
  .createSignedUrl('file.pdf', 3600, {
    download: true,
    transform: { width: 200, height: 200 }
  })
```

---

## 7. Realtime Security (MEDIUM)

Channel authorization and subscription management.

### 7.1 Enable RLS for Realtime Postgres Changes

**Impact: CRITICAL (Without RLS, all changes broadcast to all subscribers)**

```sql
-- Enable RLS FIRST
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

-- Create policy for room members only
CREATE POLICY "room_members_see_messages"
ON messages
FOR SELECT TO authenticated
USING (
  EXISTS (
    SELECT 1 FROM room_members rm
    WHERE rm.room_id = messages.room_id
    AND rm.user_id = (SELECT auth.uid())
  )
);

-- Create index for RLS performance
CREATE INDEX idx_room_members_lookup ON room_members(room_id, user_id);

-- NOW add to realtime publication
ALTER PUBLICATION supabase_realtime ADD TABLE messages;
```

### 7.2 Use Private Channels for Sensitive Data

**Impact: HIGH (Authenticated communication)**

```typescript
// Private channel requires authentication
const channel = supabase.channel('private-room', {
  config: {
    private: true
  }
})
```

### 7.3 Clean Up Subscriptions

**Impact: MEDIUM (Prevents memory leaks)**

```typescript
useEffect(() => {
  const channel = supabase
    .channel('my-channel')
    .on('postgres_changes', { event: '*', schema: 'public', table: 'posts' },
      (payload) => setPosts(prev => [...prev, payload.new]))
    .subscribe()

  // Cleanup on unmount
  return () => {
    supabase.removeChannel(channel)
  }
}, [])
```

---

## 8. Edge Functions (MEDIUM)

Serverless security patterns.

### 8.1 Verify JWT in Edge Functions

**Impact: CRITICAL (Prevents unauthorized access)**

```typescript
import "jsr:@supabase/functions-js/edge-runtime.d.ts"
import * as jose from "jsr:@panva/jose@6"

const SUPABASE_JWT_ISSUER = Deno.env.get("SUPABASE_URL") + "/auth/v1"
const SUPABASE_JWT_KEYS = jose.createRemoteJWKSet(
  new URL(Deno.env.get("SUPABASE_URL")! + "/auth/v1/.well-known/jwks.json")
)

async function verifyJWT(token: string) {
  return jose.jwtVerify(token, SUPABASE_JWT_KEYS, {
    issuer: SUPABASE_JWT_ISSUER,
  })
}

Deno.serve(async (req) => {
  const authHeader = req.headers.get('Authorization')
  if (!authHeader?.startsWith('Bearer ')) {
    return new Response(JSON.stringify({ error: 'Unauthorized' }), { status: 401 })
  }

  try {
    const { payload } = await verifyJWT(authHeader.slice(7))
    return new Response(JSON.stringify({ userId: payload.sub }))
  } catch {
    return new Response(JSON.stringify({ error: 'Invalid token' }), { status: 401 })
  }
})
```

### 8.2 Handle CORS Properly

**Impact: HIGH (Prevents unauthorized cross-origin access)**

```typescript
const corsHeaders = {
  'Access-Control-Allow-Origin': 'https://yourdomain.com',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, content-type',
  'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
}

Deno.serve(async (req) => {
  // Handle preflight
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders })
  }

  // Your logic here
  return new Response(JSON.stringify({ data: 'ok' }), {
    headers: { ...corsHeaders, 'Content-Type': 'application/json' }
  })
})
```

### 8.3 Use Secrets for Sensitive Data

**Impact: CRITICAL (Prevents credential exposure)**

```bash
# Set secrets via CLI
supabase secrets set STRIPE_SECRET_KEY=sk_live_xxx
supabase secrets set WEBHOOK_SECRET=whsec_xxx
```

```typescript
// Access in Edge Function
const stripeKey = Deno.env.get('STRIPE_SECRET_KEY')
```

---

## 9. Testing (MEDIUM)

RLS and integration testing patterns.

### 9.1 Test RLS Policies with pgTAP

**Impact: MEDIUM (Prevents security vulnerabilities in production)**

```sql
-- supabase/tests/database/todos_rls.test.sql
begin;

create extension if not exists pgtap with schema extensions;
select plan(4);

-- Setup test data
insert into auth.users (id, email) values
  ('11111111-1111-1111-1111-111111111111', 'user1@test.com'),
  ('22222222-2222-2222-2222-222222222222', 'user2@test.com');

insert into public.todos (task, user_id) values
  ('User 1 Task', '11111111-1111-1111-1111-111111111111'),
  ('User 2 Task', '22222222-2222-2222-2222-222222222222');

-- Test: User 1 sees only their todos
set local role authenticated;
set local request.jwt.claim.sub = '11111111-1111-1111-1111-111111111111';

select results_eq(
  'select count(*) from todos',
  ARRAY[1::bigint],
  'User 1 should only see their 1 todo'
);

-- Test: User 1 cannot create todos for other users
select throws_ok(
  $$insert into todos (task, user_id)
    values ('Malicious', '22222222-2222-2222-2222-222222222222'::uuid)$$,
  'User 1 cannot create todos for other users'
);

select * from finish();
rollback;
```

```bash
# Run tests
supabase test db
```

### 9.2 Use Transaction Isolation for Tests

**Impact: MEDIUM (Clean test state)**

```sql
begin;
-- All test setup and assertions here
-- Changes are rolled back automatically
rollback;
```

---

## 10. Performance Benchmarks

Based on [RLS Performance Tests](https://github.com/GaryAustin1/RLS-Performance):

| Optimization | Before | After | Improvement |
|-------------|--------|-------|-------------|
| Add indexes | 171ms | <0.1ms | **99.94%** |
| Wrap with SELECT | 179ms | 9ms | **94.97%** |
| Security definer | 178,000ms | 12ms | **99.993%** |
| Fix joins | 9,000ms | 20ms | **99.78%** |
| Specify TO role | 170ms | <0.1ms | **99.78%** |

---

## 11. Quick Reference Checklist

### Before Deployment

- [ ] RLS enabled on ALL public schema tables
- [ ] Auth functions wrapped with `(SELECT ...)`
- [ ] Indexes on all RLS policy columns
- [ ] All policies specify `TO authenticated` or `TO anon`
- [ ] Service role key is server-only (no `NEXT_PUBLIC_` prefix)
- [ ] Clerk Third-Party Auth configured (not JWT templates)
- [ ] Role claim configured in Clerk session token
- [ ] pgTAP tests for all RLS policies
- [ ] Migrations for all schema changes

### Security Checklist

- [ ] user_metadata not used for authorization
- [ ] app_metadata used for roles and permissions
- [ ] JWT claims validated before authorization
- [ ] Storage buckets have RLS policies
- [ ] Edge Functions verify JWT
- [ ] CORS configured with specific origins
- [ ] Secrets stored via `supabase secrets`
- [ ] Realtime tables have RLS before publication

### Clerk Integration Checklist

- [ ] Third-Party Auth enabled in config.toml
- [ ] Dashboard configured for production
- [ ] Server-side client uses `accessToken` callback
- [ ] Client-side client uses `useSession()` hook
- [ ] Role claim set to `authenticated`
- [ ] Organization claims used for multi-tenant RLS
- [ ] MFA enforcement via `aal` claim where needed

---

## References

### Official Documentation

- [Supabase RLS Guide](https://supabase.com/docs/guides/database/postgres/row-level-security)
- [Supabase + Clerk Integration](https://supabase.com/docs/guides/auth/third-party/clerk)
- [Clerk Supabase Integration](https://clerk.com/docs/integrations/databases/supabase)
- [JWT Claims Reference](https://supabase.com/docs/guides/auth/jwt-fields)
- [Storage Access Control](https://supabase.com/docs/guides/storage/security/access-control)
- [Realtime Authorization](https://supabase.com/docs/guides/realtime/authorization)
- [Edge Functions Auth](https://supabase.com/docs/guides/functions/auth)
- [Testing Overview](https://supabase.com/docs/guides/local-development/testing/overview)

### Community Resources

- [RLS Performance Discussion](https://github.com/orgs/supabase/discussions/14576)
- [RLS Performance Tests](https://github.com/GaryAustin1/RLS-Performance)
- [pgTAP Test Helpers](https://database.dev/basejump/supabase_test_helpers)

---

**Document Status:** Complete
**Rules Covered:** 38 rules across 10 categories
**Last Updated:** January 2026
