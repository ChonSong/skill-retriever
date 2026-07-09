---
title: Design Schemas with Security Boundaries
impact: HIGH
impactDescription: Prevents accidental data exposure through API
tags: database, schema, security, architecture
---

## Design Schemas with Security Boundaries

**Impact: HIGH (Prevents accidental data exposure through API)**

Use separate schemas to create security boundaries. The `public` schema is exposed via the Supabase API by default, so sensitive tables and functions should be placed in private schemas that are not API-accessible.

**Incorrect (everything in public schema):**

```sql
-- DON'T: Put internal tables in public schema
CREATE TABLE public.internal_audit_logs (
  id uuid PRIMARY KEY,
  user_id uuid,
  action text,
  ip_address inet,
  raw_request jsonb  -- Sensitive data exposed to API
);

-- DON'T: Put helper functions with elevated privileges in public
CREATE FUNCTION public.get_all_users()
RETURNS SETOF auth.users
LANGUAGE sql
SECURITY DEFINER
AS $$
  SELECT * FROM auth.users;  -- Exposes all user data!
$$;
```

**Correct (security boundaries with private schemas):**

```sql
-- Create a private schema for internal operations
CREATE SCHEMA IF NOT EXISTS private;

-- Revoke API access to private schema
REVOKE ALL ON SCHEMA private FROM anon, authenticated;

-- Internal tables go in private schema
CREATE TABLE private.audit_logs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES auth.users(id),
  action text NOT NULL,
  ip_address inet,
  raw_request jsonb,
  created_at timestamptz DEFAULT now()
);

-- Helper functions with elevated privileges go in private schema
CREATE FUNCTION private.get_user_by_id(user_uuid uuid)
RETURNS TABLE(id uuid, email text, created_at timestamptz)
LANGUAGE sql
SECURITY DEFINER
SET search_path = ''
AS $$
  SELECT id, email, created_at
  FROM auth.users
  WHERE id = user_uuid;
$$;

-- Public schema only contains user-facing tables with RLS
CREATE TABLE public.user_profiles (
  id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  display_name text,
  avatar_url text,
  bio text
);

ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "profiles_are_viewable_by_everyone"
ON public.user_profiles
FOR SELECT
TO authenticated, anon
USING (true);

CREATE POLICY "users_can_update_own_profile"
ON public.user_profiles
FOR UPDATE
TO authenticated
USING ((SELECT auth.uid()) = id)
WITH CHECK ((SELECT auth.uid()) = id);
```

**Schema organization pattern:**

```sql
-- Schema structure
-- public.*     - API-accessible, RLS-protected user data
-- private.*    - Internal tables, not API-accessible
-- internal.*   - Helper functions, background jobs
-- auth.*       - Supabase Auth (managed by Supabase)
-- storage.*    - Supabase Storage (managed by Supabase)

-- Example: Expose computed data via secure function
CREATE FUNCTION public.get_my_profile()
RETURNS TABLE(
  id uuid,
  display_name text,
  avatar_url text,
  total_orders bigint
)
LANGUAGE sql
SECURITY INVOKER  -- Respects RLS
SET search_path = ''
AS $$
  SELECT
    p.id,
    p.display_name,
    p.avatar_url,
    (SELECT COUNT(*) FROM public.orders o WHERE o.user_id = p.id)
  FROM public.user_profiles p
  WHERE p.id = (SELECT auth.uid());
$$;
```

**When NOT to use this pattern:**
- Simple applications with only user-facing data
- Prototyping (but refactor before production)
- When all data should be API-accessible with proper RLS

Reference: [Supabase Database Guide](https://supabase.com/docs/guides/database)
