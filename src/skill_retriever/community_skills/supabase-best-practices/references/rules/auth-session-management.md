---
title: Implement Proper Session Management
impact: HIGH
impactDescription: Prevents session hijacking and stale access
tags: auth, security, session, jwt
---

## Implement Proper Session Management

**Impact: HIGH (Prevents session hijacking and stale access)**

Proper session management ensures tokens are refreshed correctly, sessions are invalidated when needed, and users can't access resources after logout or permission changes. Deleting a user from `auth.users` does not automatically invalidate their JWT until it expires.

**Incorrect (poor session management):**

```typescript
// DON'T DO THIS - storing token and never refreshing
const token = localStorage.getItem('supabase_token')
// Token might be expired!

// DON'T DO THIS - not handling auth state changes
const supabase = createClient(url, key)
// No listener for session changes

// DON'T DO THIS - assuming deletion invalidates tokens immediately
await supabaseAdmin.auth.admin.deleteUser(userId)
// User's existing JWT is still valid until expiration!
```

**Correct (proper session management):**

```typescript
// Set up auth state listener for automatic session handling
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
)

// Listen for auth state changes (handles token refresh automatically)
supabase.auth.onAuthStateChange((event, session) => {
  console.log('Auth event:', event)

  switch (event) {
    case 'SIGNED_IN':
      // User signed in, session contains fresh tokens
      break
    case 'SIGNED_OUT':
      // Clear any cached user data
      clearUserCache()
      break
    case 'TOKEN_REFRESHED':
      // Token was automatically refreshed
      break
    case 'USER_UPDATED':
      // User data changed, might need to re-fetch permissions
      refreshUserPermissions()
      break
  }
})
```

```typescript
// Proper sign out - invalidates session server-side
async function signOut() {
  // Sign out from all devices (global sign out)
  const { error } = await supabase.auth.signOut({ scope: 'global' })

  if (error) {
    console.error('Sign out error:', error)
  }

  // Clear local state
  clearUserCache()
  router.push('/login')
}

// Sign out from current device only
async function signOutCurrentDevice() {
  const { error } = await supabase.auth.signOut({ scope: 'local' })
}
```

```typescript
// Server-side: Force sign out when revoking access
async function revokeUserAccess(userId: string) {
  const supabaseAdmin = createClient(
    process.env.SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!
  )

  // Sign out user from all sessions
  await supabaseAdmin.auth.admin.signOut(userId, 'global')

  // Optionally: Update app_metadata to flag account
  await supabaseAdmin.auth.admin.updateUserById(userId, {
    app_metadata: {
      access_revoked: true,
      revoked_at: new Date().toISOString()
    }
  })
}
```

```typescript
// Validate session before sensitive operations
async function performSensitiveOperation() {
  // Get fresh user data (validates token server-side)
  const { data: { user }, error } = await supabase.auth.getUser()

  if (error || !user) {
    throw new Error('Session expired or invalid')
  }

  // Check if access was revoked
  if (user.app_metadata?.access_revoked) {
    await supabase.auth.signOut()
    throw new Error('Access has been revoked')
  }

  // Check session freshness for sensitive operations
  const { data: { session } } = await supabase.auth.getSession()

  if (session) {
    const tokenAge = Date.now() / 1000 - (session.expires_at! - 3600)
    if (tokenAge > 300) { // More than 5 minutes old
      // Optionally require re-authentication for very sensitive ops
    }
  }

  // Proceed with operation
}
```

```sql
-- RLS policy that checks for revoked access
CREATE POLICY "check_access_not_revoked"
ON sensitive_data
AS RESTRICTIVE
FOR ALL
TO authenticated
USING (
  -- Deny if access_revoked flag is set
  COALESCE(
    (SELECT auth.jwt()->'app_metadata'->>'access_revoked')::boolean,
    false
  ) = false
);
```

**Session Configuration (supabase/config.toml):**

```toml
[auth]
# JWT expiration time (default: 3600 seconds = 1 hour)
jwt_expiry = 3600

# Refresh token rotation (recommended for security)
refresh_token_rotation_enabled = true

# Reuse interval for refresh tokens (in seconds)
refresh_token_reuse_interval = 10
```

**Key Session Events:**

| Event | Description | Action |
|-------|-------------|--------|
| `SIGNED_IN` | User signed in | Initialize user state |
| `SIGNED_OUT` | User signed out | Clear all user data |
| `TOKEN_REFRESHED` | Access token refreshed | Update cached token |
| `USER_UPDATED` | User profile changed | Refresh permissions |
| `PASSWORD_RECOVERY` | Password reset initiated | Handle recovery flow |

**When NOT to use this pattern:**
- Stateless APIs that validate JWT on every request (still need expiration checks)
- Service-to-service communication with long-lived service role keys

Reference: [Session Management](https://supabase.com/docs/guides/auth/sessions)
