---
title: Organization-Based RLS Policies with Clerk
impact: HIGH
impactDescription: Secure multi-tenant data isolation
tags: clerk, security, rls, organizations, multi-tenant
---

## Organization-Based RLS Policies with Clerk

**Impact: HIGH (Secure multi-tenant data isolation)**

Use Clerk's organization claims for multi-tenant RLS policies. Clerk provides organization information in JWT tokens that can be used to isolate data between organizations.

**Incorrect (no organization isolation):**

```sql
-- DON'T DO THIS - no organization context
CREATE POLICY "Users can read data"
ON team_data
FOR SELECT
TO authenticated
USING (true);  -- All authenticated users see all data!
```

**Correct (organization-scoped policies):**

**Step 1: Configure organization claims in Clerk**

Add to your Clerk session token customization:

```json
{
  "role": "authenticated",
  "org_id": "{{org.id}}",
  "org_role": "{{org.role}}",
  "org_slug": "{{org.slug}}"
}
```

**Step 2: Create organization-scoped table**

```sql
-- Table with organization isolation
CREATE TABLE team_documents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id text NOT NULL,
  title text NOT NULL,
  content text,
  created_by text NOT NULL,
  created_at timestamptz DEFAULT now()
);

-- Index for RLS performance
CREATE INDEX idx_team_documents_org_id
ON team_documents(organization_id);

-- Enable RLS
ALTER TABLE team_documents ENABLE ROW LEVEL SECURITY;
```

**Step 3: Create organization-scoped RLS policies**

```sql
-- Members can read their organization's documents
CREATE POLICY "Org members can read documents"
ON team_documents
FOR SELECT
TO authenticated
USING (
  organization_id = (SELECT auth.jwt()->>'org_id')
);

-- Members can create documents in their organization
CREATE POLICY "Org members can create documents"
ON team_documents
FOR INSERT
TO authenticated
WITH CHECK (
  organization_id = (SELECT auth.jwt()->>'org_id')
  AND created_by = (SELECT auth.uid()::text)
);
```

**Step 4: Role-based organization policies**

```sql
-- Only org admins can delete documents
CREATE POLICY "Org admins can delete documents"
ON team_documents
FOR DELETE
TO authenticated
USING (
  organization_id = (SELECT auth.jwt()->>'org_id')
  AND (
    -- Support both full and abbreviated claim formats
    (SELECT auth.jwt()->>'org_role') = 'org:admin'
    OR (SELECT auth.jwt()->'o'->>'rol') = 'admin'
  )
);

-- Only org admins can update documents
CREATE POLICY "Org admins can update documents"
ON team_documents
FOR UPDATE
TO authenticated
USING (
  organization_id = (SELECT auth.jwt()->>'org_id')
  AND (
    (SELECT auth.jwt()->>'org_role') = 'org:admin'
    OR (SELECT auth.jwt()->'o'->>'rol') = 'admin'
  )
)
WITH CHECK (
  organization_id = (SELECT auth.jwt()->>'org_id')
);
```

**Helper function for organization checks:**

```sql
-- Create a helper function for cleaner policies
CREATE OR REPLACE FUNCTION auth.org_id()
RETURNS text
LANGUAGE sql
STABLE
AS $$
  SELECT COALESCE(
    auth.jwt()->>'org_id',
    auth.jwt()->'o'->>'id'
  )
$$;

CREATE OR REPLACE FUNCTION auth.org_role()
RETURNS text
LANGUAGE sql
STABLE
AS $$
  SELECT COALESCE(
    auth.jwt()->>'org_role',
    'org:' || (auth.jwt()->'o'->>'rol')
  )
$$;

-- Use in policies
CREATE POLICY "Org members can read"
ON team_documents
FOR SELECT
TO authenticated
USING (
  organization_id = (SELECT auth.org_id())
);
```

**Clerk organization roles:**

| Role | Claim Value | Description |
|------|-------------|-------------|
| Admin | `org:admin` | Full organization access |
| Member | `org:member` | Standard member access |
| Custom | `org:custom_role` | Custom roles you define |

**Why this matters:**

1. **Data isolation**: Each organization only sees their own data.

2. **Role-based access**: Different permissions for admins vs members.

3. **Automatic context**: Clerk handles organization switching in the UI.

4. **Scalable multi-tenancy**: No application-level filtering needed.

**When NOT to use this pattern:**

- Single-tenant applications
- User-level data that isn't shared within organizations
- Public data that should be visible to all users

Reference: [Clerk Organizations](https://clerk.com/docs/organizations/overview)
