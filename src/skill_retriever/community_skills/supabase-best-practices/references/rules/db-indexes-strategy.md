---
title: Create Indexes for RLS Policy Columns
impact: HIGH
impactDescription: 99.94% performance improvement for RLS queries
tags: database, indexes, performance, rls
---

## Create Indexes for RLS Policy Columns

**Impact: HIGH (99.94% performance improvement for RLS queries)**

Always create indexes on columns used in RLS policies and frequently queried columns. Without proper indexes, RLS policies can cause full table scans on every request, severely impacting performance.

**Incorrect (missing indexes on RLS columns):**

```sql
-- Table without indexes
CREATE TABLE public.documents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES auth.users(id),
  organization_id uuid,
  title text,
  content text,
  created_at timestamptz DEFAULT now()
);

ALTER TABLE public.documents ENABLE ROW LEVEL SECURITY;

-- RLS policy uses user_id and organization_id - but no indexes!
CREATE POLICY "users_access_org_documents"
ON public.documents
FOR ALL
TO authenticated
USING (
  user_id = (SELECT auth.uid())
  OR
  organization_id IN (
    SELECT org_id FROM public.org_members
    WHERE member_id = (SELECT auth.uid())
  )
);

-- Every query does a full table scan: 171ms+ per query
```

**Correct (indexes on all RLS-referenced columns):**

```sql
CREATE TABLE public.documents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES auth.users(id),
  organization_id uuid,
  title text,
  content text,
  created_at timestamptz DEFAULT now()
);

-- Index for user_id lookups in RLS
CREATE INDEX idx_documents_user_id
ON public.documents(user_id);

-- Index for organization_id lookups in RLS
CREATE INDEX idx_documents_organization_id
ON public.documents(organization_id);

-- Composite index for common query patterns
CREATE INDEX idx_documents_user_created
ON public.documents(user_id, created_at DESC);

-- Index on org_members for the subquery
CREATE INDEX idx_org_members_member_id
ON public.org_members(member_id);

ALTER TABLE public.documents ENABLE ROW LEVEL SECURITY;

-- Same policy, but now uses indexes: <0.1ms per query
CREATE POLICY "users_access_org_documents"
ON public.documents
FOR ALL
TO authenticated
USING (
  user_id = (SELECT auth.uid())
  OR
  organization_id IN (
    SELECT org_id FROM public.org_members
    WHERE member_id = (SELECT auth.uid())
  )
);
```

**Index types for different use cases:**

```sql
-- B-tree (default): Equality and range queries
CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_orders_created ON orders(created_at DESC);

-- GIN: JSONB and array columns
CREATE INDEX idx_metadata_gin ON documents USING GIN(metadata);
CREATE INDEX idx_tags_gin ON posts USING GIN(tags);

-- Partial index: Only index relevant rows
CREATE INDEX idx_active_users ON users(email)
WHERE deleted_at IS NULL;

-- Covering index: Include columns to avoid table lookup
CREATE INDEX idx_orders_user_covering ON orders(user_id)
INCLUDE (total_amount, status);
```

**Analyze query performance:**

```sql
-- Check if indexes are being used
EXPLAIN ANALYZE
SELECT * FROM documents
WHERE user_id = '123e4567-e89b-12d3-a456-426614174000';

-- Find missing indexes (look for sequential scans)
SELECT
  schemaname,
  tablename,
  seq_scan,
  seq_tup_read,
  idx_scan,
  idx_tup_fetch
FROM pg_stat_user_tables
WHERE seq_scan > idx_scan
ORDER BY seq_tup_read DESC;
```

**When NOT to use this pattern:**
- Very small tables (< 1000 rows) where sequential scan is faster
- Columns with very low cardinality (e.g., boolean flags)
- Write-heavy tables where index maintenance overhead is significant

Reference: [Supabase RLS Performance](https://supabase.com/docs/guides/database/postgres/row-level-security#add-indexes)
