---
title: Configure Role Claim for Supabase RLS
impact: CRITICAL
impactDescription: Required for RLS policies to work correctly
tags: clerk, security, authentication, rls, jwt
---

## Configure Role Claim for Supabase RLS

**Impact: CRITICAL (Required for RLS policies to work correctly)**

Ensure Clerk session tokens include the `role` claim with value `authenticated`. This claim is required for Supabase RLS policies that use the `TO authenticated` clause to work correctly.

**Incorrect (missing role claim):**

```json
// Clerk session token without role claim - DON'T DO THIS
{
  "sub": "user_2abc123",
  "email": "user@example.com",
  "iat": 1234567890,
  "exp": 1234567890
}
```

```sql
-- This policy will NOT work without the role claim
CREATE POLICY "Users can read own data"
ON profiles
FOR SELECT
TO authenticated  -- This role check fails without the claim
USING (user_id = auth.uid());
```

**Correct (role claim configured):**

**Step 1: Configure in Clerk Dashboard**

1. Go to **Sessions** in Clerk Dashboard
2. Click **Customize session token**
3. Add the following claim:

```json
{
  "role": "authenticated"
}
```

**Step 2: Verify the token includes the claim**

```json
// Clerk session token with role claim
{
  "sub": "user_2abc123",
  "email": "user@example.com",
  "role": "authenticated",
  "iat": 1234567890,
  "exp": 1234567890
}
```

**Step 3: RLS policies now work correctly**

```sql
-- This policy works with the role claim
CREATE POLICY "Users can read own data"
ON profiles
FOR SELECT
TO authenticated  -- Role check passes with "authenticated" claim
USING (user_id = auth.uid());
```

**Debugging token claims:**

```typescript
// Debug: Log the token to verify claims
import { useSession } from '@clerk/nextjs'

function DebugToken() {
  const { session } = useSession()

  async function checkToken() {
    const token = await session?.getToken()
    if (token) {
      // Decode and log the payload (for debugging only)
      const payload = JSON.parse(atob(token.split('.')[1]))
      console.log('Token claims:', payload)
      console.log('Has role claim:', 'role' in payload)
    }
  }

  return <button onClick={checkToken}>Check Token</button>
}
```

**Verify in SQL:**

```sql
-- Check the current JWT claims in a Supabase query
SELECT
  auth.uid() as user_id,
  auth.jwt()->>'role' as role,
  auth.jwt()->>'email' as email;
```

**Why this matters:**

1. **RLS enforcement**: Supabase uses the `role` claim to determine which policies apply. Without it, `TO authenticated` policies won't match.

2. **Security boundary**: The `authenticated` role distinguishes logged-in users from anonymous/public access.

3. **Policy granularity**: Allows different policies for `anon` vs `authenticated` roles.

**Common issues:**

| Issue | Cause | Solution |
|-------|-------|----------|
| RLS policies not applying | Missing `role` claim | Add `role: authenticated` in Clerk |
| `permission denied` errors | Role mismatch | Verify token has correct role |
| Policies work in Dashboard but not app | Different auth context | Check token is being sent correctly |

**When NOT to use this pattern:**

- Custom role-based access (use custom claims like `app_role` instead)
- Service-to-service auth (use service role key on server)

Reference: [Supabase JWT Fields](https://supabase.com/docs/guides/auth/jwt-fields)
