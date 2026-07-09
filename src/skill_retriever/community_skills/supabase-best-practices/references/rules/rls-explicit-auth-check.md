---
title: Always Include Explicit Auth Check in Policies
impact: HIGH
impactDescription: Prevents null user_id bypass attacks
tags: rls, security, authentication
---

## Always Include Explicit Auth Check in Policies

**Impact: HIGH (Prevents null user_id bypass attacks)**

RLS policies should explicitly verify authentication state, not just compare user IDs. A null `auth.uid()` compared to a null `user_id` column could potentially allow unauthorized access in certain conditions.

**Incorrect (relies only on equality check):**

```sql
-- If auth.uid() returns null AND user_id is null, this could match
CREATE POLICY "users_own_data"
ON user_data
FOR SELECT
USING ((SELECT auth.uid()) = user_id);

-- Edge case: orphaned rows with null user_id could be exposed
```

**Correct (explicit authentication verification):**

```sql
-- First verify user is authenticated, then check ownership
CREATE POLICY "users_own_data"
ON user_data
FOR SELECT
TO authenticated
USING (
  (SELECT auth.uid()) IS NOT NULL
  AND (SELECT auth.uid()) = user_id
);

-- Or rely on TO authenticated (which already ensures auth.uid() is not null)
-- and add NOT NULL constraint on user_id column
```

**Best practice: Combine with schema constraints:**

```sql
-- Ensure user_id can never be null
CREATE TABLE user_data (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  data jsonb
);

-- With NOT NULL constraint, this policy is safe
CREATE POLICY "users_own_data"
ON user_data
FOR SELECT
TO authenticated  -- Guarantees auth.uid() is not null
USING ((SELECT auth.uid()) = user_id);
```

**For INSERT policies, validate ownership:**

```sql
-- Ensure users can only insert data for themselves
CREATE POLICY "users_insert_own_data"
ON user_data
FOR INSERT
TO authenticated
WITH CHECK (
  (SELECT auth.uid()) IS NOT NULL
  AND (SELECT auth.uid()) = user_id
);
```

**When NOT to use this pattern:**
- When the column has a NOT NULL constraint AND using `TO authenticated`
- Tables where null ownership is a valid state (use different approach)
- Public read-only tables where ownership doesn't apply

Reference: [Supabase RLS Best Practices](https://supabase.com/docs/guides/database/postgres/row-level-security#best-practices)
