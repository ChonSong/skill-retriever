---
title: MFA Enforcement in RLS Policies
impact: HIGH
impactDescription: Require multi-factor authentication for sensitive operations
tags: clerk, security, rls, mfa, authentication
---

## MFA Enforcement in RLS Policies

**Impact: HIGH (Require multi-factor authentication for sensitive operations)**

Use restrictive policies to enforce MFA (Multi-Factor Authentication) for sensitive operations. Clerk provides the `aal` (Authentication Assurance Level) claim that indicates whether MFA was used.

**Incorrect (no MFA enforcement):**

```sql
-- DON'T DO THIS - sensitive data accessible without MFA
CREATE POLICY "Users can access financial data"
ON financial_records
FOR SELECT
TO authenticated
USING (user_id = auth.uid());  -- No MFA check!
```

**Correct (MFA enforcement with restrictive policy):**

**Step 1: Configure MFA claims in Clerk**

Clerk automatically includes these claims when MFA is configured:

```json
{
  "sub": "user_2abc123",
  "role": "authenticated",
  "aal": "aal2",           // aal1 = password only, aal2 = MFA verified
  "fva": [1234567890, 0]   // Factor verification age [first, second]
}
```

**Step 2: Create base access policy**

```sql
-- Base policy: users can access their own records
CREATE POLICY "Users can access own financial data"
ON financial_records
FOR SELECT
TO authenticated
USING (user_id = auth.uid());
```

**Step 3: Add restrictive MFA policy**

```sql
-- RESTRICTIVE policy: require MFA for all access
CREATE POLICY "Require MFA for financial data"
ON financial_records
AS RESTRICTIVE  -- Must pass IN ADDITION to other policies
FOR ALL
TO authenticated
USING (
  (SELECT auth.jwt()->>'aal') = 'aal2'
);
```

**Step 4: Combine for write operations**

```sql
-- Require MFA for updates to sensitive data
CREATE POLICY "MFA required for financial updates"
ON financial_records
AS RESTRICTIVE
FOR UPDATE
TO authenticated
USING (
  (SELECT auth.jwt()->>'aal') = 'aal2'
)
WITH CHECK (
  (SELECT auth.jwt()->>'aal') = 'aal2'
);

-- Require MFA for deletes
CREATE POLICY "MFA required for financial deletes"
ON financial_records
AS RESTRICTIVE
FOR DELETE
TO authenticated
USING (
  (SELECT auth.jwt()->>'aal') = 'aal2'
);
```

**Fresh MFA verification (time-based):**

```sql
-- Require recent MFA verification (within last 10 minutes)
CREATE POLICY "Require fresh MFA for transfers"
ON money_transfers
AS RESTRICTIVE
FOR INSERT
TO authenticated
WITH CHECK (
  -- fva[1] is the timestamp of last second factor verification
  -- Check if it was within the last 600 seconds (10 minutes)
  (
    EXTRACT(EPOCH FROM now()) -
    ((SELECT auth.jwt()->'fva'->>1)::bigint)
  ) < 600
);
```

**Helper function for MFA checks:**

```sql
-- Create a helper function for cleaner policies
CREATE OR REPLACE FUNCTION auth.has_mfa()
RETURNS boolean
LANGUAGE sql
STABLE
AS $$
  SELECT (auth.jwt()->>'aal') = 'aal2'
$$;

CREATE OR REPLACE FUNCTION auth.mfa_verified_within(seconds int)
RETURNS boolean
LANGUAGE sql
STABLE
AS $$
  SELECT (
    EXTRACT(EPOCH FROM now()) -
    COALESCE((auth.jwt()->'fva'->>1)::bigint, 0)
  ) < seconds
$$;

-- Use in policies
CREATE POLICY "Require MFA"
ON sensitive_table
AS RESTRICTIVE
FOR ALL
TO authenticated
USING ((SELECT auth.has_mfa()));

CREATE POLICY "Require fresh MFA"
ON very_sensitive_table
AS RESTRICTIVE
FOR ALL
TO authenticated
USING ((SELECT auth.mfa_verified_within(300)));  -- 5 minutes
```

**Authentication Assurance Levels:**

| Level | Description | Clerk Context |
|-------|-------------|---------------|
| `aal1` | Single factor (password/OAuth) | User logged in without MFA |
| `aal2` | Multi-factor authenticated | User completed MFA challenge |

**Why this matters:**

1. **Compliance**: Many regulations (PCI-DSS, SOC2) require MFA for sensitive data access.

2. **Defense in depth**: Even if credentials are compromised, MFA adds a barrier.

3. **Granular control**: Require MFA only for sensitive operations, not all access.

4. **Session freshness**: Time-based checks ensure recent verification.

**Application-side handling:**

```typescript
// Prompt for MFA before sensitive operations
import { useClerk } from '@clerk/nextjs'

function SensitiveAction() {
  const { session } = useClerk()

  async function performSensitiveAction() {
    // Check if MFA is verified
    const factors = session?.user?.twoFactorEnabled

    if (!factors) {
      // Redirect to MFA setup
      window.location.href = '/user/security'
      return
    }

    // Proceed with action
    const supabase = createClient(...)
    await supabase.from('financial_records').update(...)
  }
}
```

**When NOT to use this pattern:**

- Non-sensitive data that doesn't require additional protection
- Applications where MFA is not enabled for users
- Read-only public data

Reference: [Clerk Multi-factor Authentication](https://clerk.com/docs/authentication/configuration/sign-up-sign-in-options#multi-factor-authentication)
