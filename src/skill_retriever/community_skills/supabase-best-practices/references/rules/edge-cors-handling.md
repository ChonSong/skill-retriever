---
title: Handle CORS in Edge Functions
impact: HIGH
impactDescription: Enables browser-based invocation of Edge Functions
tags: edge-functions, cors, security, browser
---

## Handle CORS in Edge Functions

**Impact: HIGH (Enables browser-based invocation of Edge Functions)**

When invoking Edge Functions from a browser, you must handle CORS (Cross-Origin Resource Sharing) preflight requests. Without proper CORS headers, browsers will block requests to your Edge Functions from your web application.

**Incorrect (no CORS handling - browser requests fail):**

```typescript
// ❌ Missing CORS headers - browser requests will be blocked
import "jsr:@supabase/functions-js/edge-runtime.d.ts"

Deno.serve(async (req) => {
  const { name } = await req.json()

  return new Response(
    JSON.stringify({ message: `Hello ${name}!` }),
    { headers: { 'Content-Type': 'application/json' } }
  )
})
```

**Correct (shared CORS headers in _shared folder):**

```typescript
// ✅ Create reusable CORS headers
// _shared/cors.ts
export const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}
```

```typescript
// ✅ Use CORS headers in your function
// hello/index.ts
import "jsr:@supabase/functions-js/edge-runtime.d.ts"
import { corsHeaders } from '../_shared/cors.ts'

Deno.serve(async (req) => {
  // Handle CORS preflight requests
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    const { name } = await req.json()
    const data = {
      message: `Hello ${name}!`,
    }

    return new Response(JSON.stringify(data), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      status: 200,
    })
  } catch (error) {
    return new Response(JSON.stringify({ error: error.message }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      status: 400,
    })
  }
})
```

**Correct (restrictive CORS for production - specify allowed origins):**

```typescript
// ✅ Restrict CORS to specific origins in production
// _shared/cors.ts
const ALLOWED_ORIGINS = [
  'https://your-app.com',
  'https://www.your-app.com',
  'http://localhost:3000', // For local development
]

export function getCorsHeaders(origin: string | null): Record<string, string> {
  // Check if origin is allowed
  const allowedOrigin = origin && ALLOWED_ORIGINS.includes(origin)
    ? origin
    : ALLOWED_ORIGINS[0] // Fallback to primary domain

  return {
    'Access-Control-Allow-Origin': allowedOrigin,
    'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
    'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
    'Access-Control-Max-Age': '86400', // Cache preflight for 24 hours
  }
}

// Usage in function
// hello/index.ts
import "jsr:@supabase/functions-js/edge-runtime.d.ts"
import { getCorsHeaders } from '../_shared/cors.ts'

Deno.serve(async (req) => {
  const origin = req.headers.get('Origin')
  const corsHeaders = getCorsHeaders(origin)

  if (req.method === 'OPTIONS') {
    return new Response(null, {
      status: 204,
      headers: corsHeaders
    })
  }

  const { name } = await req.json()

  return new Response(
    JSON.stringify({ message: `Hello ${name}!` }),
    {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      status: 200,
    }
  )
})
```

**Correct (complete CORS handling pattern):**

```typescript
// ✅ Complete CORS handling with all necessary headers
import "jsr:@supabase/functions-js/edge-runtime.d.ts"

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
  'Access-Control-Max-Age': '86400',
}

Deno.serve(async (req) => {
  // Always handle OPTIONS for CORS preflight
  if (req.method === 'OPTIONS') {
    return new Response(null, {
      status: 204,
      headers: corsHeaders,
    })
  }

  try {
    // Your function logic here
    const result = await processRequest(req)

    return new Response(JSON.stringify(result), {
      status: 200,
      headers: {
        ...corsHeaders,
        'Content-Type': 'application/json',
      },
    })
  } catch (error) {
    // Always include CORS headers in error responses too
    return new Response(
      JSON.stringify({ error: error.message }),
      {
        status: error.status || 500,
        headers: {
          ...corsHeaders,
          'Content-Type': 'application/json',
        },
      }
    )
  }
})

async function processRequest(req: Request) {
  // Process the request based on method
  switch (req.method) {
    case 'GET':
      return { data: 'GET response' }
    case 'POST':
      const body = await req.json()
      return { data: body }
    default:
      throw { message: 'Method not allowed', status: 405 }
  }
}
```

**Recommended folder structure:**

```
└── supabase
    └── functions
        ├── _shared
        │   └── cors.ts          # Reusable CORS headers
        ├── function-one
        │   └── index.ts
        └── function-two
            └── index.ts
```

**When NOT to use this pattern:**
- Server-to-server communication (CORS only applies to browser requests)
- Edge Functions invoked only via Supabase client libraries (they handle CORS internally)
- Webhook endpoints that receive callbacks from external services

Reference: [CORS Support for Edge Functions](https://supabase.com/docs/guides/functions/cors)
