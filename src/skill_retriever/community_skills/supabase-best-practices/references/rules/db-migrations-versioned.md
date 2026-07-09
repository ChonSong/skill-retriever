---
title: Use Versioned Migrations for Schema Changes
impact: HIGH
impactDescription: Ensures reproducible and auditable database changes
tags: database, migrations, schema, versioning
---

## Use Versioned Migrations for Schema Changes

**Impact: HIGH (Ensures reproducible and auditable database changes)**

All database schema changes should be managed through versioned migration files, never through direct SQL execution in production. This ensures changes are tracked, reversible, and consistent across environments.

**Incorrect (direct schema changes):**

```sql
-- DON'T: Run ad-hoc SQL directly in production
-- This change is not tracked or reproducible
ALTER TABLE users ADD COLUMN phone text;
CREATE INDEX idx_users_phone ON users(phone);
```

```typescript
// DON'T: Embed schema changes in application code
const setupDatabase = async () => {
  await supabase.rpc('exec_sql', {
    sql: 'ALTER TABLE users ADD COLUMN phone text'
  })
}
```

**Correct (versioned migrations):**

```sql
-- supabase/migrations/20260118000000_add_user_phone.sql
-- Migration: Add phone column to users table

-- Add the phone column
ALTER TABLE public.users ADD COLUMN phone text;

-- Add index for phone lookups
CREATE INDEX idx_users_phone ON public.users(phone);

-- Add RLS policy for phone column access
CREATE POLICY "users_can_view_own_phone"
ON public.users
FOR SELECT
TO authenticated
USING ((SELECT auth.uid()) = id);
```

```bash
# Apply migrations using Supabase CLI
supabase db push

# Or apply specific migration
supabase migration up

# Check migration status
supabase migration list
```

**Migration file naming convention:**

```
supabase/migrations/
├── 20260101000000_create_users_table.sql
├── 20260102000000_add_user_profiles.sql
├── 20260103000000_create_rls_policies.sql
└── 20260118000000_add_user_phone.sql
```

**Best practices for migrations:**

```sql
-- 1. Always include both schema changes AND RLS policies
-- 2. Use transactions for multi-statement migrations
BEGIN;

CREATE TABLE public.orders (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE,
  total_amount numeric(10,2) NOT NULL,
  created_at timestamptz DEFAULT now()
);

ALTER TABLE public.orders ENABLE ROW LEVEL SECURITY;

CREATE POLICY "users_own_orders"
ON public.orders
FOR ALL
TO authenticated
USING ((SELECT auth.uid()) = user_id)
WITH CHECK ((SELECT auth.uid()) = user_id);

COMMIT;
```

**When NOT to use this pattern:**
- Local development experimentation (but always create migration before committing)
- One-time data fixes that don't change schema (use separate data scripts)

Reference: [Supabase Migrations Guide](https://supabase.com/docs/guides/cli/managing-environments)
