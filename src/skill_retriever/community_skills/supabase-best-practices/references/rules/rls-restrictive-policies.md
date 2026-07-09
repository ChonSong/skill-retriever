---
title: Use RESTRICTIVE Policies for Additional Constraints
impact: HIGH
impactDescription: Enables layered security with AND logic
tags: rls, security, policies
---

## Use RESTRICTIVE Policies for Additional Constraints

**Impact: HIGH (Enables layered security with AND logic)**

By default, RLS policies are PERMISSIVE and combined with OR logic. Use RESTRICTIVE policies (AS RESTRICTIVE) to add additional constraints that must ALL be satisfied, enabling defense-in-depth security patterns.

**Understanding policy combination:**

```sql
-- PERMISSIVE policies (default): Combined with OR
-- If ANY permissive policy passes, access is granted

-- RESTRICTIVE policies: Combined with AND
-- ALL restrictive policies must pass (in addition to at least one permissive)

-- Final check: (permissive1 OR permissive2 OR ...) AND restrictive1 AND restrictive2 AND ...
```

**Incorrect (single permissive policy for complex requirements):**

```sql
-- Trying to enforce multiple conditions in one policy
CREATE POLICY "complex_access"
ON sensitive_data
FOR SELECT
TO authenticated
USING (
  (SELECT auth.uid()) = user_id
  AND is_verified = true
  AND subscription_active = true
  AND (SELECT auth.jwt()->>'aal') = 'aal2'  -- MFA required
);

-- Hard to maintain and audit
```

**Correct (layered restrictive policies):**

```sql
-- Base permissive policy: user owns the data
CREATE POLICY "user_owns_data"
ON sensitive_data
FOR SELECT
TO authenticated
USING ((SELECT auth.uid()) = user_id);

-- Restrictive: require email verification
CREATE POLICY "require_verified"
ON sensitive_data
AS RESTRICTIVE
FOR SELECT
TO authenticated
USING (is_verified = true);

-- Restrictive: require active subscription
CREATE POLICY "require_subscription"
ON sensitive_data
AS RESTRICTIVE
FOR SELECT
TO authenticated
USING (subscription_active = true);

-- Restrictive: require MFA for sensitive operations
CREATE POLICY "require_mfa"
ON sensitive_data
AS RESTRICTIVE
FOR SELECT
TO authenticated
USING ((SELECT auth.jwt()->>'aal') = 'aal2');
```

**Common use cases for RESTRICTIVE policies:**

```sql
-- 1. MFA enforcement for sensitive tables
CREATE POLICY "mfa_required"
ON financial_data
AS RESTRICTIVE
FOR ALL
TO authenticated
USING ((SELECT auth.jwt()->>'aal') = 'aal2');

-- 2. IP allowlist (using custom claim)
CREATE POLICY "ip_allowlist"
ON admin_data
AS RESTRICTIVE
FOR ALL
TO authenticated
USING ((SELECT auth.jwt()->>'allowed_ip') = 'true');

-- 3. Time-based access restrictions
CREATE POLICY "business_hours_only"
ON audit_logs
AS RESTRICTIVE
FOR INSERT
TO authenticated
USING (
  EXTRACT(HOUR FROM NOW()) BETWEEN 9 AND 17
  AND EXTRACT(DOW FROM NOW()) BETWEEN 1 AND 5
);

-- 4. Soft delete filter
CREATE POLICY "exclude_deleted"
ON all_data
AS RESTRICTIVE
FOR SELECT
TO authenticated, anon
USING (deleted_at IS NULL);
```

**When NOT to use this pattern:**
- Simple access patterns with single condition
- When policies should be alternatives (OR logic)
- Performance-critical paths where policy count matters

Reference: [PostgreSQL RESTRICTIVE Policies](https://www.postgresql.org/docs/current/sql-createpolicy.html)
