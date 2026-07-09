---
title: Always Enable RLS on Public Schema Tables
impact: CRITICAL
impactDescription: Prevents unauthorized data access
tags: rls, security, database
---

## Always Enable RLS on Public Schema Tables

**Impact: CRITICAL (Prevents unauthorized data access)**

Row Level Security (RLS) is the foundation of Supabase security. Any table in the public schema is accessible via the API, making RLS essential for data protection. Without RLS, all authenticated users can read and modify all data.

**Incorrect (table exposed without protection):**

```sql
-- Table is created but RLS is not enabled
CREATE TABLE public.user_profiles (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES auth.users(id),
  full_name text,
  email text
);

-- Anyone with the anon or authenticated key can read ALL profiles
```

**Correct (RLS enabled with restrictive policy):**

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

CREATE POLICY "users_can_update_own_profile"
ON public.user_profiles
FOR UPDATE
TO authenticated
USING ((SELECT auth.uid()) = user_id)
WITH CHECK ((SELECT auth.uid()) = user_id);
```

**When NOT to use this pattern:**
- Tables in private schemas not exposed via API (but still recommended)
- Lookup tables with truly public data (e.g., country codes) - still enable RLS with permissive SELECT policy
- When using service role exclusively server-side (RLS is bypassed, but enable anyway for defense in depth)

Reference: [Supabase RLS Guide](https://supabase.com/docs/guides/database/postgres/row-level-security)
