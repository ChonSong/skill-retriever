---
title: Create RLS Policies for Storage Objects
impact: CRITICAL
impactDescription: Prevents unauthorized file access
tags: storage, security, rls
---

## Create RLS Policies for Storage Objects

**Impact: CRITICAL (Prevents unauthorized file access)**

Supabase Storage uses Postgres Row Level Security (RLS) to control access to files. By default, Storage does not allow any uploads to buckets without RLS policies. You must create policies on the `storage.objects` table to allow operations. Always specify the `TO authenticated` clause and restrict access to specific buckets.

**Incorrect (overly permissive policy):**

```sql
-- DON'T DO THIS - allows anyone to upload anywhere
CREATE POLICY "Allow all uploads"
ON storage.objects
FOR INSERT
WITH CHECK (true);
```

**Correct (scoped policies with authentication):**

```sql
-- Allow authenticated users to upload to their own folder
CREATE POLICY "Users can upload to own folder"
ON storage.objects
FOR INSERT
TO authenticated
WITH CHECK (
  bucket_id = 'user-files' AND
  (storage.foldername(name))[1] = (SELECT auth.uid()::text)
);

-- Allow users to read their own files
CREATE POLICY "Users can read own files"
ON storage.objects
FOR SELECT
TO authenticated
USING (
  bucket_id = 'user-files' AND
  (storage.foldername(name))[1] = (SELECT auth.uid()::text)
);

-- Allow users to update their own files
CREATE POLICY "Users can update own files"
ON storage.objects
FOR UPDATE
TO authenticated
USING (
  bucket_id = 'user-files' AND
  owner_id = (SELECT auth.uid()::text)
);

-- Allow users to delete their own files
CREATE POLICY "Users can delete own files"
ON storage.objects
FOR DELETE
TO authenticated
USING (
  bucket_id = 'user-files' AND
  owner_id = (SELECT auth.uid()::text)
);
```

**Organization-based Storage Policies (with Clerk):**

```sql
-- Allow organization members to access org files
CREATE POLICY "Org members can read org files"
ON storage.objects
FOR SELECT
TO authenticated
USING (
  bucket_id = 'org-files' AND
  (storage.foldername(name))[1] = (
    SELECT COALESCE(
      auth.jwt()->>'org_id',
      auth.jwt()->'o'->>'id'
    )
  )
);

-- Only org admins can upload
CREATE POLICY "Org admins can upload"
ON storage.objects
FOR INSERT
TO authenticated
WITH CHECK (
  bucket_id = 'org-files' AND
  (storage.foldername(name))[1] = (
    SELECT COALESCE(
      auth.jwt()->>'org_id',
      auth.jwt()->'o'->>'id'
    )
  ) AND
  (
    (SELECT auth.jwt()->>'org_role') = 'org:admin' OR
    (SELECT auth.jwt()->'o'->>'rol') = 'admin'
  )
);
```

**Required Operations by Policy Type:**

| Operation | Required Policy |
|-----------|----------------|
| `upload()` | INSERT |
| `upload()` with upsert | INSERT, SELECT, UPDATE |
| `download()` | SELECT |
| `update()` | SELECT, UPDATE |
| `move()` | SELECT, UPDATE |
| `copy()` | SELECT, INSERT |
| `remove()` | SELECT, DELETE |
| `list()` | SELECT |

**When NOT to use this pattern:**
- Public buckets for truly public assets (profile pictures, blog images) - downloads bypass RLS
- Server-side operations using service role key (bypasses RLS entirely)

Reference: [Storage Access Control](https://supabase.com/docs/guides/storage/security/access-control)
