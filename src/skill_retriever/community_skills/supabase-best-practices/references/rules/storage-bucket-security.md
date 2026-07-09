---
title: Configure Bucket Security Settings
impact: HIGH
impactDescription: Prevents data exposure and enforces upload restrictions
tags: storage, security, buckets
---

## Configure Bucket Security Settings

**Impact: HIGH (Prevents data exposure and enforces upload restrictions)**

Storage buckets have two access models: public and private. Choose the appropriate model based on your security requirements. Private buckets enforce RLS for all operations including downloads. Public buckets bypass access control for downloads but still enforce RLS for uploads, updates, and deletes.

**Incorrect (using public bucket for sensitive data):**

```typescript
// DON'T DO THIS - sensitive documents in public bucket
const { data, error } = await supabase.storage.createBucket('user-documents', {
  public: true, // Anyone with URL can access!
})

// Upload sensitive file to public bucket
await supabase.storage.from('user-documents').upload(
  'contracts/confidential.pdf',
  file
)
// URL is now publicly accessible:
// https://project.supabase.co/storage/v1/object/public/user-documents/contracts/confidential.pdf
```

**Correct (private bucket with upload restrictions):**

```typescript
// Create private bucket with security restrictions
const { data, error } = await supabase.storage.createBucket('user-documents', {
  public: false, // Requires auth for downloads
  fileSizeLimit: 10485760, // 10MB max
  allowedMimeTypes: ['application/pdf', 'image/png', 'image/jpeg'],
})

// Access requires authentication
const { data } = await supabase.storage
  .from('user-documents')
  .download('contracts/confidential.pdf')
```

**Bucket Configuration Patterns:**

```typescript
// Private bucket for sensitive user data
const { error } = await supabase.storage.createBucket('private-files', {
  public: false,
  fileSizeLimit: 52428800, // 50MB
  allowedMimeTypes: [
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  ],
})

// Public bucket for profile images (optimized caching)
const { error } = await supabase.storage.createBucket('avatars', {
  public: true, // Better CDN caching for public assets
  fileSizeLimit: 1048576, // 1MB
  allowedMimeTypes: ['image/png', 'image/jpeg', 'image/webp'],
})

// Private bucket for organization files
const { error } = await supabase.storage.createBucket('org-files', {
  public: false,
  fileSizeLimit: 104857600, // 100MB
  allowedMimeTypes: [
    'application/pdf',
    'application/zip',
    'image/*',
  ],
})
```

**Migration for Bucket Configuration:**

```sql
-- Create private bucket via migration
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'secure-documents',
  'secure-documents',
  false,
  52428800, -- 50MB
  ARRAY['application/pdf', 'image/png', 'image/jpeg']
);

-- Update existing bucket to be private
UPDATE storage.buckets
SET public = false
WHERE id = 'my-bucket';
```

**Access Model Comparison:**

| Feature | Public Bucket | Private Bucket |
|---------|--------------|----------------|
| Download without auth | Yes | No |
| CDN caching | High HIT ratio | Lower HIT ratio |
| Upload RLS | Enforced | Enforced |
| Delete RLS | Enforced | Enforced |
| Use case | Public media | Sensitive files |

**When NOT to use this pattern:**
- Static website assets that must be publicly accessible
- Public CDN-served images where performance is critical
- Open data that doesn't require access control

Reference: [Storage Buckets](https://supabase.com/docs/guides/storage/buckets/fundamentals)
