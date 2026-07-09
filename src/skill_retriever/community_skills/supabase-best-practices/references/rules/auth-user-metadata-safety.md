---
title: Treat User Metadata as Untrusted Input
impact: HIGH
impactDescription: Prevents privilege escalation attacks
tags: auth, security, metadata, validation
---

## Treat User Metadata as Untrusted Input

**Impact: HIGH (Prevents privilege escalation attacks)**

User metadata (`user_metadata` / `raw_user_meta_data`) is user-modifiable and should never be used for authorization decisions. Users can update their own metadata, making it unsuitable for storing roles, permissions, or any security-sensitive data.

**Incorrect (using user_metadata for authorization):**

```typescript
// DON'T DO THIS - user can modify their own metadata
const { data: { user } } = await supabase.auth.getUser()

// DANGEROUS: User can set is_admin to true themselves!
if (user?.user_metadata?.is_admin) {
  return adminDashboard()
}

// DANGEROUS: User can grant themselves any role
if (user?.user_metadata?.role === 'moderator') {
  return moderatorTools()
}
```

```sql
-- DON'T DO THIS - user_metadata is user-modifiable
CREATE POLICY "admins_only"
ON admin_data
FOR ALL
TO authenticated
USING (
  -- User can change this themselves!
  (SELECT auth.jwt()->'user_metadata'->>'is_admin')::boolean = true
);
```

```typescript
// User can exploit this by updating their metadata:
await supabase.auth.updateUser({
  data: { is_admin: true, role: 'admin' }  // Self-granted admin!
})
```

**Correct (user_metadata for non-sensitive data only):**

```typescript
// User metadata is fine for preferences and display data
const { data: { user } } = await supabase.auth.signUp({
  email: 'user@example.com',
  password: 'secure-password',
  options: {
    data: {
      // Safe: display name, preferences, non-sensitive info
      full_name: 'John Doe',
      avatar_url: 'https://example.com/avatar.jpg',
      theme: 'dark',
      locale: 'en-US',
    }
  }
})

// Reading user metadata for display purposes (safe)
const displayName = user?.user_metadata?.full_name ?? 'Anonymous'
const theme = user?.user_metadata?.theme ?? 'light'
```

```typescript
// For authorization, use app_metadata (server-only modifiable)
// This requires admin/service role key - users cannot modify
const { data, error } = await supabaseAdmin.auth.admin.updateUserById(
  userId,
  {
    app_metadata: {
      role: 'admin',        // Only server can set this
      permissions: ['read', 'write', 'delete']
    }
  }
)
```

```sql
-- Correct: Use app_metadata for authorization
CREATE POLICY "admins_only"
ON admin_data
FOR ALL
TO authenticated
USING (
  -- app_metadata cannot be modified by users
  (SELECT auth.jwt()->'app_metadata'->>'role') = 'admin'
);
```

**Safe Uses for user_metadata:**

| Safe | Unsafe |
|------|--------|
| Display name | Roles |
| Avatar URL | Permissions |
| Theme preference | Admin flags |
| Locale/timezone | Access levels |
| Bio/description | Subscription tier |
| Notification settings | Feature flags |

**When NOT to use this pattern:**
- Internal admin tools where all users are trusted (still not recommended)
- When validating the metadata value against a separate authoritative source

Reference: [User Management](https://supabase.com/docs/guides/auth/managing-user-data)
