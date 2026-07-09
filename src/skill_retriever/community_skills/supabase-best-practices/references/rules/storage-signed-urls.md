---
title: Use Signed URLs for Private File Access
impact: HIGH
impactDescription: Secure time-limited file sharing
tags: storage, security, signed-urls
---

## Use Signed URLs for Private File Access

**Impact: HIGH (Secure time-limited file sharing)**

For private buckets, use signed URLs to grant temporary access to files. Signed URLs include a token that expires after a specified duration, preventing long-term unauthorized access. Always set appropriate expiration times based on the use case - shorter for sensitive files, longer for downloads.

**Incorrect (exposing files without time limits):**

```typescript
// DON'T DO THIS - bypasses security with service role
const supabase = createClient(url, serviceRoleKey) // Never on client!

// Or sharing permanent public URL for private files
const url = `${SUPABASE_URL}/storage/v1/object/public/private-bucket/file.pdf`
// This won't work for private buckets anyway, but shows wrong approach
```

**Correct (time-limited signed URLs):**

```typescript
// Generate signed URL with appropriate expiration
const { data, error } = await supabase.storage
  .from('private-bucket')
  .createSignedUrl('documents/report.pdf', 3600) // 1 hour

if (data) {
  // Share this URL - expires in 1 hour
  console.log(data.signedUrl)
}

// For sensitive files, use shorter expiration
const { data: sensitiveUrl } = await supabase.storage
  .from('private-bucket')
  .createSignedUrl('contracts/nda.pdf', 300) // 5 minutes

// Generate multiple signed URLs at once
const { data: urls } = await supabase.storage
  .from('private-bucket')
  .createSignedUrls([
    'documents/report1.pdf',
    'documents/report2.pdf',
    'images/chart.png',
  ], 3600)
```

**Server-Side Signed URL Generation:**

```typescript
// Server-side: Generate signed URL for authenticated user
// lib/storage.ts
import { createServerSupabaseClient } from '@/lib/supabase/server'

export async function getSecureDownloadUrl(
  bucket: string,
  path: string,
  expiresIn: number = 3600
) {
  const supabase = createServerSupabaseClient()

  // Verify user has access (RLS handles this automatically)
  const { data, error } = await supabase.storage
    .from(bucket)
    .createSignedUrl(path, expiresIn)

  if (error) {
    throw new Error(`Failed to generate signed URL: ${error.message}`)
  }

  return data.signedUrl
}

// API route usage
export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const path = searchParams.get('path')

  if (!path) {
    return Response.json({ error: 'Path required' }, { status: 400 })
  }

  try {
    const url = await getSecureDownloadUrl('documents', path, 300)
    return Response.json({ url })
  } catch (error) {
    return Response.json({ error: 'Access denied' }, { status: 403 })
  }
}
```

**Signed URLs with Image Transformations:**

```typescript
// Generate signed URL for transformed image
const { data } = await supabase.storage
  .from('images')
  .createSignedUrl('photos/original.jpg', 3600, {
    transform: {
      width: 400,
      height: 300,
      quality: 80,
    },
  })

// Transformation options are embedded in the token
// They cannot be modified after signing
```

**Signed Upload URLs (Server-Generated):**

```typescript
// Generate URL that allows upload without exposing keys
const { data, error } = await supabase.storage
  .from('uploads')
  .createSignedUploadUrl('user-uploads/file.pdf')

if (data) {
  // Client can upload directly to this URL
  const { signedUrl, token, path } = data

  // Client-side upload
  await supabase.storage
    .from('uploads')
    .uploadToSignedUrl(path, token, file)
}
```

**Expiration Time Guidelines:**

| Use Case | Recommended Expiration |
|----------|----------------------|
| Immediate download | 60-300 seconds |
| Share link (email) | 3600 seconds (1 hour) |
| Temporary access | 86400 seconds (1 day) |
| Extended sharing | 604800 seconds (1 week) |
| Sensitive documents | 60-300 seconds |

**When NOT to use this pattern:**
- Public assets that don't require access control
- Files that need permanent public URLs
- Static website assets served via CDN

Reference: [Serving Assets from Storage](https://supabase.com/docs/guides/storage/serving/downloads)
