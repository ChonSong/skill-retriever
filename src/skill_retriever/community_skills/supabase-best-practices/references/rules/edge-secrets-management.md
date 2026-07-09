---
title: Manage Secrets Securely in Edge Functions
impact: CRITICAL
impactDescription: Prevents credential exposure and security breaches
tags: edge-functions, security, secrets, environment-variables
---

## Manage Secrets Securely in Edge Functions

**Impact: CRITICAL (Prevents credential exposure and security breaches)**

Edge Functions provide secure access to environment variables and secrets. Never hardcode sensitive credentials in your function code. Use Supabase's secrets management to store API keys, database credentials, and other sensitive data securely.

**Incorrect (hardcoded secrets - SECURITY VULNERABILITY):**

```typescript
// ❌ NEVER hardcode secrets - they will be exposed in source control
import "jsr:@supabase/functions-js/edge-runtime.d.ts"

const STRIPE_SECRET_KEY = 'sk_live_abc123...' // EXPOSED!
const DATABASE_URL = 'postgresql://user:password@host:5432/db' // EXPOSED!

Deno.serve(async (req) => {
  // Using hardcoded secrets - dangerous!
  const stripe = new Stripe(STRIPE_SECRET_KEY)
  // ...
})
```

**Correct (use Deno.env.get for environment variables):**

```typescript
// ✅ Access secrets via environment variables
import "jsr:@supabase/functions-js/edge-runtime.d.ts"
import { createClient } from "npm:@supabase/supabase-js@2"
import Stripe from "npm:stripe"

// Default Supabase secrets (automatically available)
const supabaseUrl = Deno.env.get('SUPABASE_URL')!
const supabaseAnonKey = Deno.env.get('SUPABASE_ANON_KEY')!
const supabaseServiceRoleKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
const databaseUrl = Deno.env.get('SUPABASE_DB_URL')!

// Custom secrets (set via CLI or Dashboard)
const stripeSecretKey = Deno.env.get('STRIPE_SECRET_KEY')!

const supabase = createClient(supabaseUrl, supabaseAnonKey)
const stripe = new Stripe(stripeSecretKey)

Deno.serve(async (req) => {
  // Use the securely loaded clients
  const { data } = await supabase.from('orders').select('*')
  return new Response(JSON.stringify(data))
})
```

**Default secrets available in Edge Functions:**

| Secret | Description | Security Level |
|--------|-------------|----------------|
| `SUPABASE_URL` | API gateway URL | Safe for client |
| `SUPABASE_ANON_KEY` | Public anonymous key | Safe for client (with RLS) |
| `SUPABASE_SERVICE_ROLE_KEY` | Admin key (bypasses RLS) | Server-only |
| `SUPABASE_DB_URL` | Direct database connection | Server-only |

**Setting secrets for local development:**

```bash
# Create .env file in supabase/functions/.env
# ⚠️ Add .env to .gitignore!
echo "STRIPE_SECRET_KEY=sk_test_..." >> supabase/functions/.env

# Secrets are automatically loaded on supabase start
supabase start
supabase functions serve

# Or specify a custom env file
supabase functions serve --env-file .env.local
```

**Setting secrets for production:**

```bash
# Option 1: Set from .env file
supabase secrets set --env-file supabase/functions/.env

# Option 2: Set individual secrets
supabase secrets set STRIPE_SECRET_KEY=sk_live_...

# Option 3: Set via Dashboard
# Navigate to: Project Settings > Edge Functions > Secrets

# List all secrets (values are hidden)
supabase secrets list
```

**Correct (validate required secrets on startup):**

```typescript
// ✅ Validate required secrets at function startup
import "jsr:@supabase/functions-js/edge-runtime.d.ts"

// Validate required secrets exist
const requiredSecrets = [
  'SUPABASE_URL',
  'SUPABASE_ANON_KEY',
  'STRIPE_SECRET_KEY',
  'OPENAI_API_KEY',
]

for (const secret of requiredSecrets) {
  if (!Deno.env.get(secret)) {
    throw new Error(`Missing required secret: ${secret}`)
  }
}

// Now safe to use secrets
const stripeKey = Deno.env.get('STRIPE_SECRET_KEY')!
const openaiKey = Deno.env.get('OPENAI_API_KEY')!

Deno.serve(async (req) => {
  // Function logic with validated secrets
})
```

**Correct (different clients based on operation type):**

```typescript
// ✅ Use appropriate key based on operation
import "jsr:@supabase/functions-js/edge-runtime.d.ts"
import { createClient } from "npm:@supabase/supabase-js@2"

const supabaseUrl = Deno.env.get('SUPABASE_URL')!
const supabaseAnonKey = Deno.env.get('SUPABASE_ANON_KEY')!
const supabaseServiceRoleKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!

// Client for user-facing operations (respects RLS)
function createUserClient(authHeader: string) {
  return createClient(supabaseUrl, supabaseAnonKey, {
    global: {
      headers: { Authorization: authHeader },
    },
  })
}

// Admin client for server-side operations (bypasses RLS)
const supabaseAdmin = createClient(supabaseUrl, supabaseServiceRoleKey)

Deno.serve(async (req) => {
  // User operations - use their JWT context
  const userClient = createUserClient(req.headers.get('Authorization')!)
  const { data: userPosts } = await userClient
    .from('posts')
    .select('*') // RLS filters to user's posts

  // Admin operations - use service role
  const { data: allUsers } = await supabaseAdmin
    .from('users')
    .select('id, email') // Bypasses RLS

  return new Response(JSON.stringify({ userPosts }))
})
```

**Never log secrets:**

```typescript
// ❌ NEVER log secret values
console.log('API Key:', Deno.env.get('STRIPE_SECRET_KEY'))

// ✅ Log only that secret exists (for debugging)
console.log('Stripe key configured:', !!Deno.env.get('STRIPE_SECRET_KEY'))

// ✅ Log truncated/hashed version if needed
const key = Deno.env.get('STRIPE_SECRET_KEY')
console.log('Stripe key prefix:', key?.slice(0, 7) + '...')
```

**Recommended .gitignore entries:**

```gitignore
# Environment files with secrets
.env
.env.local
.env.*.local
supabase/functions/.env
supabase/.env

# Never commit these
*.pem
*.key
secrets.json
```

**When NOT to use this pattern:**
- Public configuration values that aren't sensitive (use regular constants)
- Values that need to be different per-request (use request parameters)

Reference: [Edge Functions Environment Variables](https://supabase.com/docs/guides/functions/secrets)
