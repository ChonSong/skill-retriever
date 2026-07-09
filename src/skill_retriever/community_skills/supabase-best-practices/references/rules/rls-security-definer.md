---
title: Use SECURITY DEFINER Functions for Complex Lookups
impact: CRITICAL
impactDescription: 99.993% performance improvement
tags: rls, performance, functions, security
---

## Use SECURITY DEFINER Functions for Complex Lookups

**Impact: CRITICAL (99.993% performance improvement - 178,000ms to 12ms)**

When RLS policies require lookups to other tables (e.g., checking membership), create SECURITY DEFINER functions that bypass RLS for those lookups. This prevents nested RLS evaluation and dramatically improves performance.

**Incorrect (nested RLS evaluation):**

```sql
-- Policy checks against another RLS-protected table
CREATE POLICY "team_members_access"
ON team_documents
FOR SELECT
TO authenticated
USING (
  EXISTS (
    SELECT 1 FROM team_memberships
    WHERE team_memberships.team_id = team_documents.team_id
    AND team_memberships.user_id = (SELECT auth.uid())
  )
);

-- team_memberships also has RLS, causing nested evaluation
-- Performance degrades exponentially with data size
```

**Correct (SECURITY DEFINER function):**

```sql
-- Create a function that runs as the definer (postgres), bypassing RLS
CREATE OR REPLACE FUNCTION public.is_team_member(check_team_id uuid)
RETURNS boolean
LANGUAGE sql
SECURITY DEFINER
STABLE
SET search_path = public
AS $$
  SELECT EXISTS (
    SELECT 1 FROM team_memberships
    WHERE team_id = check_team_id
    AND user_id = auth.uid()
  );
$$;

-- Revoke execute from public, grant only to authenticated
REVOKE EXECUTE ON FUNCTION public.is_team_member FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.is_team_member TO authenticated;

-- Policy uses the optimized function
CREATE POLICY "team_members_access"
ON team_documents
FOR SELECT
TO authenticated
USING (public.is_team_member(team_id));
```

**Security considerations:**

```sql
-- Always set search_path to prevent search path injection
SET search_path = public

-- Limit function access to required roles only
REVOKE EXECUTE ON FUNCTION ... FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ... TO authenticated;

-- Use STABLE for functions that don't modify data
-- This allows PostgreSQL to optimize repeated calls
```

**When NOT to use this pattern:**
- Simple policies that don't require cross-table lookups
- When the lookup table is not RLS-protected
- When you need the nested RLS check for security (user should only see memberships they're authorized to see)

Reference: [PostgreSQL SECURITY DEFINER](https://www.postgresql.org/docs/current/sql-createfunction.html#SQL-CREATEFUNCTION-SECURITY)
