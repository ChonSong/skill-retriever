---
title: Use App Metadata for Authorization Data
impact: HIGH
impactDescription: Secure server-controlled authorization
tags: auth, security, metadata, authorization
---

## Use App Metadata for Authorization Data

**Impact: HIGH (Secure server-controlled authorization)**

App metadata (`app_metadata` / `raw_app_meta_data`) can only be modified by the server using service role or admin keys. Use it to store roles, permissions, subscription tiers, and other authorization-related data that users should not be able to modify.

**Incorrect (not using app_metadata for authorization):**

```typescript
// DON'T DO THIS - storing roles in user_metadata (user-modifiable)
const { data, error } = await supabase.auth.signUp({
  email: 'user@example.com',
  password: 'password',
  options: {
    data: {
      role: 'admin',  // User could modify this later!
    }
  }
})

// DON'T DO THIS - storing permissions in a public table
await supabase
  .from('user_permissions')
  .insert({ user_id: userId, role: 'admin' })
  // User might be able to modify this depending on RLS
```

**Correct (using app_metadata with admin API):**

```typescript
// Server-side: Set roles using admin API (service role key required)
import { createClient } from '@supabase/supabase-js'

const supabaseAdmin = createClient(
  process.env.SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!  // Server-side only!
)

// Assign role to user (only server can do this)
async function assignRole(userId: string, role: string) {
  const { data, error } = await supabaseAdmin.auth.admin.updateUserById(
    userId,
    {
      app_metadata: {
        role: role,
        permissions: getPermissionsForRole(role),
        subscription_tier: 'pro',
        feature_flags: ['beta_features', 'new_dashboard']
      }
    }
  )

  if (error) throw error
  return data
}

// Create user with initial app_metadata
async function createAdminUser(email: string, password: string) {
  const { data, error } = await supabaseAdmin.auth.admin.createUser({
    email,
    password,
    email_confirm: true,
    app_metadata: {
      role: 'admin',
      created_by: 'system'
    }
  })

  if (error) throw error
  return data
}
```

```sql
-- RLS policies using app_metadata (secure)
CREATE POLICY "admins_full_access"
ON all_data
FOR ALL
TO authenticated
USING (
  (SELECT auth.jwt()->'app_metadata'->>'role') = 'admin'
);

-- Subscription-based access control
CREATE POLICY "pro_users_can_access_premium"
ON premium_features
FOR SELECT
TO authenticated
USING (
  (SELECT auth.jwt()->'app_metadata'->>'subscription_tier') IN ('pro', 'enterprise')
);

-- Permission-based access
CREATE POLICY "users_with_delete_permission"
ON resources
FOR DELETE
TO authenticated
USING (
  (SELECT auth.jwt()->'app_metadata'->'permissions') ? 'delete'
);
```

**Reading app_metadata in application code:**

```typescript
// Server-side: Read app_metadata for authorization decisions
async function checkAuthorization(requiredRole: string) {
  const { data: { user }, error } = await supabase.auth.getUser()

  if (error || !user) {
    throw new Error('Authentication required')
  }

  const userRole = user.app_metadata?.role
  const permissions = user.app_metadata?.permissions || []

  if (userRole !== requiredRole && !permissions.includes(requiredRole)) {
    throw new Error(`Required role: ${requiredRole}`)
  }

  return true
}

// Check subscription tier
function hasProAccess(user: User): boolean {
  const tier = user.app_metadata?.subscription_tier
  return tier === 'pro' || tier === 'enterprise'
}
```

**Recommended app_metadata Structure:**

```typescript
interface AppMetadata {
  // Role-based access control
  role: 'user' | 'moderator' | 'admin' | 'super_admin'

  // Fine-grained permissions
  permissions: string[]  // ['read', 'write', 'delete', 'admin']

  // Subscription/billing
  subscription_tier: 'free' | 'pro' | 'enterprise'
  subscription_status: 'active' | 'canceled' | 'past_due'

  // Feature flags (server-controlled)
  feature_flags: string[]

  // Organization membership (if not using Clerk)
  organization_id?: string
  organization_role?: string

  // Audit trail
  created_by?: string
  role_assigned_at?: string
}
```

**When NOT to use this pattern:**
- For user-editable preferences (use user_metadata instead)
- When using Clerk (use Clerk's organization and role claims)
- For data that needs to be queried/joined frequently (use a database table instead)

Reference: [User Management](https://supabase.com/docs/guides/auth/managing-user-data)
