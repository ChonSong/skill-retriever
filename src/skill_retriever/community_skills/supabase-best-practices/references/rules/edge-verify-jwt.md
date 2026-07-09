---
title: Verify JWT in Edge Functions
impact: CRITICAL
impactDescription: Prevents unauthorized access to serverless endpoints
tags: edge-functions, security, jwt, authentication
---

## Verify JWT in Edge Functions

**Impact: CRITICAL (Prevents unauthorized access to serverless endpoints)**

Edge Functions should verify JWT tokens to ensure only authenticated users can access protected endpoints. With the new JWT Signing Keys (replacing the deprecated symmetric secret), you should implement explicit JWT verification instead of relying on the `verify_jwt` flag.

**Incorrect (no JWT verification - anyone can access):**

```typescript
// ❌ No authentication - endpoint is publicly accessible
import "jsr:@supabase/functions-js/edge-runtime.d.ts"

Deno.serve(async (req) => {
  // Anyone can call this endpoint!
  const { data } = await req.json()

  return new Response(JSON.stringify({ result: data }), {
    headers: { 'Content-Type': 'application/json' }
  })
})
```

**Correct (verify JWT using Supabase Auth):**

```typescript
// ✅ Verify JWT token before processing request
import "jsr:@supabase/functions-js/edge-runtime.d.ts"
import { createClient } from "npm:@supabase/supabase-js@2"

const supabase = createClient(
  Deno.env.get('SUPABASE_URL')!,
  Deno.env.get('SUPABASE_ANON_KEY')!
)

Deno.serve(async (req) => {
  const authHeader = req.headers.get('Authorization')
  if (!authHeader) {
    return new Response(
      JSON.stringify({ error: 'Missing authorization header' }),
      { status: 401, headers: { 'Content-Type': 'application/json' } }
    )
  }

  const token = authHeader.replace('Bearer ', '')
  const { data, error } = await supabase.auth.getClaims(token)

  if (error || !data?.claims?.sub) {
    return new Response(
      JSON.stringify({ error: 'Invalid or expired token' }),
      { status: 401, headers: { 'Content-Type': 'application/json' } }
    )
  }

  const userId = data.claims.sub
  // Process authenticated request...

  return new Response(
    JSON.stringify({ message: `Hello user ${userId}` }),
    { headers: { 'Content-Type': 'application/json' } }
  )
})
```

**Correct (using jose library for JWT verification with JWKS):**

```typescript
// ✅ Verify JWT using jose library with asymmetric keys
import "jsr:@supabase/functions-js/edge-runtime.d.ts"
import * as jose from "jsr:@panva/jose@6"

const SUPABASE_JWT_ISSUER = Deno.env.get("SUPABASE_URL") + "/auth/v1"
const SUPABASE_JWT_KEYS = jose.createRemoteJWKSet(
  new URL(Deno.env.get("SUPABASE_URL")! + "/auth/v1/.well-known/jwks.json")
)

async function verifyJWT(token: string) {
  return jose.jwtVerify(token, SUPABASE_JWT_KEYS, {
    issuer: SUPABASE_JWT_ISSUER,
  })
}

Deno.serve(async (req) => {
  const authHeader = req.headers.get('Authorization')
  if (!authHeader?.startsWith('Bearer ')) {
    return new Response(
      JSON.stringify({ error: 'Missing or invalid authorization header' }),
      { status: 401, headers: { 'Content-Type': 'application/json' } }
    )
  }

  const token = authHeader.slice(7)

  try {
    const { payload } = await verifyJWT(token)
    const userId = payload.sub

    return new Response(
      JSON.stringify({ message: `Authenticated as ${userId}` }),
      { headers: { 'Content-Type': 'application/json' } }
    )
  } catch (error) {
    return new Response(
      JSON.stringify({ error: 'Invalid token' }),
      { status: 401, headers: { 'Content-Type': 'application/json' } }
    )
  }
})
```

**Correct (reusable auth middleware pattern):**

```typescript
// ✅ Create reusable auth middleware
// _shared/auth.ts
import * as jose from "jsr:@panva/jose@6"

const SUPABASE_JWT_ISSUER = Deno.env.get("SUPABASE_URL") + "/auth/v1"
const SUPABASE_JWT_KEYS = jose.createRemoteJWKSet(
  new URL(Deno.env.get("SUPABASE_URL")! + "/auth/v1/.well-known/jwks.json")
)

export async function authMiddleware(
  req: Request,
  handler: (req: Request, userId: string) => Promise<Response>
): Promise<Response> {
  // Allow CORS preflight requests
  if (req.method === "OPTIONS") {
    return new Response(null, { status: 204 })
  }

  const authHeader = req.headers.get("Authorization")
  if (!authHeader?.startsWith("Bearer ")) {
    return new Response(
      JSON.stringify({ error: "Unauthorized" }),
      { status: 401, headers: { "Content-Type": "application/json" } }
    )
  }

  try {
    const token = authHeader.slice(7)
    const { payload } = await jose.jwtVerify(token, SUPABASE_JWT_KEYS, {
      issuer: SUPABASE_JWT_ISSUER,
    })

    return handler(req, payload.sub as string)
  } catch {
    return new Response(
      JSON.stringify({ error: "Invalid token" }),
      { status: 401, headers: { "Content-Type": "application/json" } }
    )
  }
}

// index.ts - Using the middleware
import { authMiddleware } from "../_shared/auth.ts"

Deno.serve((req) =>
  authMiddleware(req, async (req, userId) => {
    const body = await req.json()
    return new Response(
      JSON.stringify({ userId, data: body }),
      { headers: { "Content-Type": "application/json" } }
    )
  })
)
```

**When NOT to use this pattern:**
- Public webhook endpoints that receive callbacks from external services (Stripe, GitHub, etc.) - use webhook signature verification instead
- Public health check endpoints
- Static asset serving

Reference: [Securing Edge Functions](https://supabase.com/docs/guides/functions/auth)
