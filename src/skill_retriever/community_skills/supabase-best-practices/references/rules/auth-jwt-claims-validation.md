---
title: Validate JWT Claims Before Trusting
impact: HIGH
impactDescription: Prevents authorization bypass attacks
tags: auth, security, jwt, validation
---

## Validate JWT Claims Before Trusting

**Impact: HIGH (Prevents authorization bypass attacks)**

Always validate JWT claims server-side before making authorization decisions. While Supabase validates the JWT signature, your application must verify the claims match expected values and the token hasn't expired.

**Incorrect (trusting claims without validation):**

```typescript
// DON'T DO THIS - no validation of claims
async function getUserData(req: Request) {
  const { data: { user } } = await supabase.auth.getUser()

  // Blindly trusting user_metadata for authorization
  if (user?.user_metadata?.is_admin) {
    return getAllUsers() // Security vulnerability!
  }
}
```

```sql
-- DON'T DO THIS - no role check in RLS policy
CREATE POLICY "anyone_can_read"
ON sensitive_data
FOR SELECT
USING (true);  -- No authentication check!
```

**Correct (validating claims properly):**

```typescript
// Server-side validation of JWT claims
async function getUserData(req: Request) {
  const { data: { user }, error } = await supabase.auth.getUser()

  if (error || !user) {
    throw new Error('Authentication required')
  }

  // Validate required claims exist
  if (!user.aud || user.aud !== 'authenticated') {
    throw new Error('Invalid token audience')
  }

  // Check role from app_metadata (not user_metadata!)
  const role = user.app_metadata?.role
  if (role !== 'admin') {
    throw new Error('Admin access required')
  }

  // Verify authentication level for sensitive operations
  const aal = user.aal
  if (aal !== 'aal2') {
    throw new Error('MFA required for this operation')
  }

  return getAllUsers()
}
```

```sql
-- RLS policy with proper claim validation
CREATE POLICY "authenticated_users_can_read"
ON user_profiles
FOR SELECT
TO authenticated
USING (
  -- Verify user is authenticated and accessing their own data
  (SELECT auth.uid()) = user_id
  AND
  -- Verify role claim exists
  (SELECT auth.jwt()->>'role') = 'authenticated'
);

-- Admin policy with app_metadata check
CREATE POLICY "admins_can_read_all"
ON user_profiles
FOR SELECT
TO authenticated
USING (
  (SELECT auth.jwt()->'app_metadata'->>'role') = 'admin'
);
```

**Key JWT Claims to Validate:**

| Claim | Description | Validation |
|-------|-------------|------------|
| `sub` | User ID | Must exist, matches expected format (UUID) |
| `aud` | Audience | Must be `authenticated` for user tokens |
| `role` | User role | Must match expected role for operation |
| `aal` | Auth Assurance Level | `aal1` (single-factor) or `aal2` (MFA) |
| `exp` | Expiration | Must be in the future |
| `app_metadata` | Server-set data | Use for authorization (user can't modify) |

**When NOT to use this pattern:**
- Public endpoints that don't require authentication
- When using Supabase RLS which handles validation automatically (but still validate in application code for defense in depth)

Reference: [JWT Claims Reference](https://supabase.com/docs/guides/auth/jwt-fields)
