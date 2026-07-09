---
title: Add Indexes on RLS Policy Columns
impact: CRITICAL
impactDescription: 99.94% performance improvement
tags: rls, performance, indexes, database
---

## Add Indexes on RLS Policy Columns

**Impact: CRITICAL (99.94% performance improvement - 171ms to <0.1ms)**

RLS policies act as WHERE clauses appended to every query. Without proper indexes, PostgreSQL performs full table scans to evaluate policies. Adding indexes on columns used in RLS policies dramatically improves performance.

**Incorrect (no index on policy column):**

```sql
CREATE TABLE documents (
  id uuid PRIMARY KEY,
  user_id uuid NOT NULL,
  title text,
  content text
);

ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

-- Policy uses user_id but there's no index
CREATE POLICY "users_own_documents"
ON documents
FOR ALL
TO authenticated
USING ((SELECT auth.uid()) = user_id);

-- Every query scans the entire table to find matching user_id values
```

**Correct (indexed policy column):**

```sql
CREATE TABLE documents (
  id uuid PRIMARY KEY,
  user_id uuid NOT NULL,
  title text,
  content text
);

-- Add index on the column used in RLS policy
CREATE INDEX idx_documents_user_id ON documents(user_id);

ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

CREATE POLICY "users_own_documents"
ON documents
FOR ALL
TO authenticated
USING ((SELECT auth.uid()) = user_id);

-- Queries use the index for O(log n) lookups instead of O(n) scans
```

**Multi-column policy example:**

```sql
-- Policy checking both org_id and user_id
CREATE POLICY "org_member_access"
ON projects
FOR SELECT
TO authenticated
USING (
  (SELECT auth.jwt()->>'org_id') = organization_id
  OR (SELECT auth.uid()) = owner_id
);

-- Create indexes for both columns
CREATE INDEX idx_projects_organization_id ON projects(organization_id);
CREATE INDEX idx_projects_owner_id ON projects(owner_id);

-- For frequent AND conditions, consider composite index
CREATE INDEX idx_projects_org_owner ON projects(organization_id, owner_id);
```

**When NOT to use this pattern:**
- Very small tables (<1000 rows) where index overhead exceeds benefit
- Columns with very low cardinality (e.g., boolean flags)
- Write-heavy tables where index maintenance cost is prohibitive

Reference: [RLS Performance Tests](https://github.com/GaryAustin1/RLS-Performance)
