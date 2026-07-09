---
title: Use Foreign Keys with Appropriate CASCADE Actions
impact: HIGH
impactDescription: Ensures data integrity and proper cleanup
tags: database, foreign-keys, integrity, relationships
---

## Use Foreign Keys with Appropriate CASCADE Actions

**Impact: HIGH (Ensures data integrity and proper cleanup)**

Always define foreign key constraints to maintain referential integrity. Choose the appropriate `ON DELETE` and `ON UPDATE` actions based on your data relationships to prevent orphaned records and ensure proper data cleanup.

**Incorrect (missing foreign keys):**

```sql
-- DON'T: Tables without foreign key constraints
CREATE TABLE public.posts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid,  -- No FK constraint!
  title text NOT NULL,
  content text
);

CREATE TABLE public.comments (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  post_id uuid,  -- No FK constraint!
  user_id uuid,  -- No FK constraint!
  content text NOT NULL
);

-- Problems:
-- 1. Can insert comments for non-existent posts
-- 2. Deleting a user leaves orphaned posts and comments
-- 3. No database-level data integrity
```

**Correct (foreign keys with appropriate actions):**

```sql
-- User-owned content: CASCADE delete when user is deleted
CREATE TABLE public.posts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  title text NOT NULL,
  content text,
  created_at timestamptz DEFAULT now()
);

-- Comments: CASCADE when post is deleted, but SET NULL if commenter is deleted
CREATE TABLE public.comments (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  post_id uuid NOT NULL REFERENCES public.posts(id) ON DELETE CASCADE,
  user_id uuid REFERENCES auth.users(id) ON DELETE SET NULL,
  content text NOT NULL,
  created_at timestamptz DEFAULT now()
);

-- Order history: RESTRICT deletion to preserve audit trail
CREATE TABLE public.orders (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE RESTRICT,
  total_amount numeric(10,2) NOT NULL,
  status text DEFAULT 'pending',
  created_at timestamptz DEFAULT now()
);

-- Soft-delete pattern for users with orders
ALTER TABLE auth.users ADD COLUMN IF NOT EXISTS deleted_at timestamptz;
```

**CASCADE action guidelines:**

```sql
-- ON DELETE CASCADE: Child records should be deleted with parent
-- Use for: User content, session data, temporary records
CREATE TABLE public.user_preferences (
  user_id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  theme text DEFAULT 'light',
  notifications_enabled boolean DEFAULT true
);

-- ON DELETE SET NULL: Preserve child records but remove reference
-- Use for: Comments, logs where author context is optional
CREATE TABLE public.audit_logs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  actor_id uuid REFERENCES auth.users(id) ON DELETE SET NULL,
  action text NOT NULL,
  details jsonb,
  created_at timestamptz DEFAULT now()
);

-- ON DELETE RESTRICT: Prevent deletion if children exist
-- Use for: Financial records, compliance data
CREATE TABLE public.invoices (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  customer_id uuid NOT NULL REFERENCES public.customers(id) ON DELETE RESTRICT,
  amount numeric(10,2) NOT NULL,
  paid_at timestamptz
);

-- ON DELETE SET DEFAULT: Set to a default value
-- Use for: Reassigning to a system user or default category
CREATE TABLE public.tasks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  assignee_id uuid DEFAULT '00000000-0000-0000-0000-000000000000'
    REFERENCES auth.users(id) ON DELETE SET DEFAULT,
  title text NOT NULL
);
```

**Index foreign key columns:**

```sql
-- Always index foreign key columns for performance
CREATE INDEX idx_posts_user_id ON public.posts(user_id);
CREATE INDEX idx_comments_post_id ON public.comments(post_id);
CREATE INDEX idx_comments_user_id ON public.comments(user_id);
```

**When NOT to use this pattern:**
- Cross-database references (use application-level checks)
- Very high-write tables where FK checks cause performance issues (rare)
- Intentionally denormalized data for analytics

Reference: [PostgreSQL Foreign Keys](https://www.postgresql.org/docs/current/ddl-constraints.html#DDL-CONSTRAINTS-FK)
