---
title: Minimize Joins in RLS Policies
impact: CRITICAL
impactDescription: 99.78% performance improvement
tags: rls, performance, optimization
---

## Minimize Joins in RLS Policies

**Impact: CRITICAL (99.78% performance improvement - 9,000ms to 20ms)**

Joins in RLS policies are evaluated for every row access, causing severe performance degradation. Where possible, denormalize data or use SECURITY DEFINER functions to avoid joins in policy expressions.

**Incorrect (multiple joins in policy):**

```sql
-- Policy requires joining through multiple tables
CREATE POLICY "org_documents_access"
ON documents
FOR SELECT
TO authenticated
USING (
  EXISTS (
    SELECT 1
    FROM projects p
    JOIN organizations o ON o.id = p.organization_id
    JOIN organization_members om ON om.organization_id = o.id
    WHERE p.id = documents.project_id
    AND om.user_id = (SELECT auth.uid())
  )
);

-- This join chain executes for every row, O(n * m * k) complexity
```

**Correct (denormalized column):**

```sql
-- Add organization_id directly to documents table
ALTER TABLE documents ADD COLUMN organization_id uuid;

-- Create index for the policy
CREATE INDEX idx_documents_org_id ON documents(organization_id);

-- Simple, fast policy
CREATE POLICY "org_documents_access"
ON documents
FOR SELECT
TO authenticated
USING (
  organization_id IN (
    SELECT organization_id
    FROM organization_members
    WHERE user_id = (SELECT auth.uid())
  )
);

-- Or use SECURITY DEFINER function for the lookup
CREATE OR REPLACE FUNCTION get_user_org_ids()
RETURNS uuid[]
LANGUAGE sql
SECURITY DEFINER
STABLE
SET search_path = public
AS $$
  SELECT array_agg(organization_id)
  FROM organization_members
  WHERE user_id = auth.uid();
$$;

CREATE POLICY "org_documents_access"
ON documents
FOR SELECT
TO authenticated
USING (organization_id = ANY(get_user_org_ids()));
```

**Alternative: Use triggers for denormalization:**

```sql
-- Automatically populate organization_id from project
CREATE OR REPLACE FUNCTION set_document_org_id()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  NEW.organization_id := (
    SELECT organization_id FROM projects WHERE id = NEW.project_id
  );
  RETURN NEW;
END;
$$;

CREATE TRIGGER document_set_org_id
  BEFORE INSERT OR UPDATE ON documents
  FOR EACH ROW
  EXECUTE FUNCTION set_document_org_id();
```

**When NOT to use this pattern:**
- When data integrity requires real-time consistency (denormalization can drift)
- Very small tables where join overhead is negligible
- When the join is unavoidable for security reasons

Reference: [RLS Performance Best Practices](https://github.com/orgs/supabase/discussions/14576)
