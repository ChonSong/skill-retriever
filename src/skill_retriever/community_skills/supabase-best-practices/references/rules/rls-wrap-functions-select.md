---
title: Wrap Auth Functions with SELECT
impact: CRITICAL
impactDescription: 94.97% performance improvement
tags: rls, performance, optimization
---

## Wrap Auth Functions with SELECT

**Impact: CRITICAL (94.97% performance improvement - 179ms to 9ms)**

PostgreSQL evaluates RLS policy expressions for each row. When using `auth.uid()` or `auth.jwt()` directly, the function is called repeatedly. Wrapping with `(SELECT ...)` forces PostgreSQL to evaluate the function once and cache the result.

**Incorrect (function called per row):**

```sql
-- auth.uid() is called for EVERY row being checked
CREATE POLICY "users_own_data"
ON documents
FOR SELECT
TO authenticated
USING (auth.uid() = user_id);

-- With 10,000 rows, auth.uid() is called 10,000 times
```

**Correct (function evaluated once):**

```sql
-- Wrapping with SELECT caches the result
CREATE POLICY "users_own_data"
ON documents
FOR SELECT
TO authenticated
USING ((SELECT auth.uid()) = user_id);

-- auth.uid() is called once, then compared against all rows
```

**Multiple function calls example:**

```sql
-- Incorrect: Multiple function calls per row
CREATE POLICY "org_members_access"
ON org_data
FOR SELECT
TO authenticated
USING (
  auth.uid() = user_id
  OR auth.jwt()->>'org_id' = organization_id
);

-- Correct: Each function wrapped and evaluated once
CREATE POLICY "org_members_access"
ON org_data
FOR SELECT
TO authenticated
USING (
  (SELECT auth.uid()) = user_id
  OR (SELECT auth.jwt()->>'org_id') = organization_id
);
```

**When NOT to use this pattern:**
- When the function must be evaluated per-row by design (rare)
- Simple policies on small tables (<100 rows) where performance is not critical

Reference: [RLS Performance Discussion](https://github.com/orgs/supabase/discussions/14576)
