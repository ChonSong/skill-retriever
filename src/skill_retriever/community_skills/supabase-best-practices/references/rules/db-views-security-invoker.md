---
title: Use SECURITY INVOKER for Views in Public Schema
impact: HIGH
impactDescription: Prevents accidental data exposure through views
tags: database, views, security, rls
---

## Use SECURITY INVOKER for Views in Public Schema

**Impact: HIGH (Prevents accidental data exposure through views)**

PostgreSQL views default to `SECURITY DEFINER`, which bypasses Row Level Security and runs with the view creator's permissions. Always use `SECURITY INVOKER` for views in the public schema to ensure RLS policies are respected.

**Incorrect (default SECURITY DEFINER view):**

```sql
-- DON'T: Create views without security_invoker
-- This view bypasses RLS and exposes ALL data to API users!
CREATE VIEW public.user_orders AS
SELECT
  o.id,
  o.user_id,
  o.total_amount,
  o.status,
  u.email  -- Exposes all users' emails!
FROM public.orders o
JOIN auth.users u ON u.id = o.user_id;

-- Any authenticated user can now see ALL orders and emails
-- SELECT * FROM public.user_orders; -- Returns everything!
```

**Correct (SECURITY INVOKER view):**

```sql
-- DO: Always use security_invoker for public views
CREATE VIEW public.user_orders
WITH (security_invoker = on)
AS
SELECT
  o.id,
  o.user_id,
  o.total_amount,
  o.status,
  o.created_at
FROM public.orders o;

-- Ensure the underlying table has RLS
ALTER TABLE public.orders ENABLE ROW LEVEL SECURITY;

CREATE POLICY "users_see_own_orders"
ON public.orders
FOR SELECT
TO authenticated
USING ((SELECT auth.uid()) = user_id);

-- Now the view respects RLS - users only see their own orders
```

**Complex view with multiple tables:**

```sql
-- View joining multiple RLS-protected tables
CREATE VIEW public.order_details
WITH (security_invoker = on)
AS
SELECT
  o.id AS order_id,
  o.user_id,
  o.total_amount,
  o.status,
  oi.product_id,
  oi.quantity,
  oi.unit_price,
  p.name AS product_name
FROM public.orders o
JOIN public.order_items oi ON oi.order_id = o.id
JOIN public.products p ON p.id = oi.product_id;

-- Each underlying table needs its own RLS policies
-- The view will only show rows the user can access in ALL joined tables
```

**Migrating existing views:**

```sql
-- Check for existing SECURITY DEFINER views
SELECT
  schemaname,
  viewname,
  definition
FROM pg_views
WHERE schemaname = 'public';

-- Recreate view with SECURITY INVOKER
DROP VIEW IF EXISTS public.user_orders;

CREATE VIEW public.user_orders
WITH (security_invoker = on)
AS
SELECT
  id,
  user_id,
  total_amount,
  status,
  created_at
FROM public.orders;
```

**Materialized views (special handling):**

```sql
-- Materialized views don't support security_invoker
-- Option 1: Use a regular view on top of materialized view
CREATE MATERIALIZED VIEW private.orders_summary_mv AS
SELECT
  user_id,
  COUNT(*) as order_count,
  SUM(total_amount) as total_spent
FROM public.orders
GROUP BY user_id;

-- Create security invoker view for API access
CREATE VIEW public.my_order_summary
WITH (security_invoker = on)
AS
SELECT * FROM private.orders_summary_mv
WHERE user_id = (SELECT auth.uid());

-- Option 2: Keep materialized view in private schema
-- and create an RPC function for access
CREATE FUNCTION public.get_my_order_summary()
RETURNS TABLE(order_count bigint, total_spent numeric)
LANGUAGE sql
SECURITY INVOKER
SET search_path = ''
AS $$
  SELECT order_count, total_spent
  FROM private.orders_summary_mv
  WHERE user_id = (SELECT auth.uid());
$$;
```

**Database advisor check:**

```sql
-- Supabase Database Advisor flags SECURITY DEFINER views
-- Run this to find problematic views
SELECT
  n.nspname AS schema,
  c.relname AS view_name,
  CASE
    WHEN c.relrowsecurity THEN 'RLS Enabled'
    ELSE 'RLS Disabled - CHECK THIS!'
  END AS rls_status
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE c.relkind = 'v'
  AND n.nspname = 'public';
```

**When NOT to use this pattern:**
- Views in private schemas not exposed via API
- Views that intentionally aggregate data across users (use RPC functions instead)
- System views for admin dashboards (restrict via role-based access)

Reference: [Supabase Database Advisor - Security Definer View](https://supabase.com/docs/guides/database/database-advisors?lint=0010_security_definer_view)
