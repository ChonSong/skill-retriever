---
title: Use Third-Party Auth Integration with Clerk
impact: CRITICAL
impactDescription: Eliminates JWT secret sharing security risk
tags: clerk, security, authentication, setup
---

## Use Third-Party Auth Integration with Clerk

**Impact: CRITICAL (Eliminates JWT secret sharing security risk)**

Always use Supabase's native Third-Party Auth integration with Clerk instead of deprecated JWT templates. The Third-Party Auth approach uses asymmetric keys (public/private key pairs), which means your Supabase project's JWT secret is never shared with Clerk.

**Incorrect (deprecated JWT template approach):**

```toml
# supabase/config.toml - DON'T DO THIS
# No Clerk configuration - relies on JWT templates

# In application code:
```

```typescript
// DON'T DO THIS - deprecated approach that shares JWT secret
const token = await getToken({ template: 'supabase' })

const supabase = createClient(url, anonKey, {
  global: {
    headers: { Authorization: `Bearer ${token}` }
  }
})
```

**Correct (Third-Party Auth integration):**

```toml
# supabase/config.toml (local development)
[auth.third_party.clerk]
enabled = true
domain = "your-instance.clerk.accounts.dev"
```

For production, configure in Supabase Dashboard:
1. Go to **Authentication** > **Sign In / Up**
2. Click **Add provider** > **Third-party Auth**
3. Select **Clerk** and enter your Clerk domain

```typescript
// Application code uses native session tokens
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(url, anonKey, {
  async accessToken() {
    return session?.getToken() ?? null
  }
})
```

**Why this matters:**

1. **Security**: JWT templates require sharing your Supabase JWT secret with Clerk, creating a security risk. Third-Party Auth uses asymmetric cryptography where only Clerk holds the private key.

2. **Official recommendation**: Both Supabase and Clerk recommend this approach as of April 2025.

3. **Simpler setup**: No need to create and maintain JWT templates in Clerk Dashboard.

4. **Better token handling**: Automatic token refresh and validation.

**When NOT to use this pattern:**

- Legacy projects that cannot migrate from JWT templates (plan migration)
- Using a Clerk version that doesn't support Third-Party Auth (upgrade Clerk)

Reference: [Supabase + Clerk Integration](https://supabase.com/docs/guides/auth/third-party/clerk)
