---
title: Always Specify Roles with TO Clause
impact: CRITICAL
impactDescription: 99.78% performance improvement
tags: rls, performance, security, roles
---

## Always Specify Roles with TO Clause

**Impact: CRITICAL (99.78% performance improvement - 170ms to <0.1ms)**

When creating RLS policies, always specify the target role using the `TO` clause. Without it, PostgreSQL evaluates the policy for ALL roles including internal system roles, causing unnecessary overhead.

**Incorrect (policy applies to all roles):**

```sql
-- No TO clause means policy is evaluated for every role
CREATE POLICY "users_own_data"
ON user_data
FOR SELECT
USING ((SELECT auth.uid()) = user_id);

-- This policy runs for anon, authenticated, service_role, and system roles
-- Even when service_role (which bypasses RLS) makes a query
```

**Correct (explicit role specification):**

```sql
-- Policy only evaluated for authenticated users
CREATE POLICY "users_own_data"
ON user_data
FOR SELECT
TO authenticated
USING ((SELECT auth.uid()) = user_id);
```

**Multiple roles example:**

```sql
-- Allow both authenticated users and anonymous read access
CREATE POLICY "public_read_access"
ON public_content
FOR SELECT
TO authenticated, anon
USING (published = true);

-- Separate policy for authenticated-only writes
CREATE POLICY "authenticated_write"
ON public_content
FOR INSERT
TO authenticated
WITH CHECK ((SELECT auth.uid()) = author_id);
```

**Common Supabase roles:**

| Role | Description |
|------|-------------|
| `anon` | Anonymous/unauthenticated requests |
| `authenticated` | Logged-in users |
| `service_role` | Server-side with elevated privileges (bypasses RLS) |

**When NOT to use this pattern:**
- Policies that genuinely need to apply to all roles (very rare)
- When creating base policies that should be inherited

Reference: [Supabase Auth Roles](https://supabase.com/docs/guides/auth/row-level-security#roles)
