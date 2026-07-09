---
title: Test RLS Policies with pgTAP
impact: MEDIUM
impactDescription: Prevents security vulnerabilities from reaching production
tags: testing, rls, security, pgtap
---

## Test RLS Policies with pgTAP

**Impact: MEDIUM (Prevents security vulnerabilities from reaching production)**

Write comprehensive pgTAP tests for all Row Level Security policies. pgTAP is a unit testing framework for Postgres that runs tests in transactions, providing fast and isolated test execution.

**Incorrect (No RLS testing):**

```sql
-- No tests written for RLS policies
-- Relying on manual testing or hoping policies work

CREATE POLICY "users_own_data" ON todos
FOR ALL TO authenticated
USING (user_id = auth.uid());

-- No verification that this policy actually works!
```

**Correct (Comprehensive pgTAP tests):**

```sql
-- supabase/tests/database/todos_rls.test.sql
begin;

-- Install pgTAP extension
create extension if not exists pgtap with schema extensions;

-- Declare test count
select plan(6);

-- Setup test data
insert into auth.users (id, email) values
  ('11111111-1111-1111-1111-111111111111', 'user1@test.com'),
  ('22222222-2222-2222-2222-222222222222', 'user2@test.com');

insert into public.todos (task, user_id) values
  ('User 1 Task 1', '11111111-1111-1111-1111-111111111111'),
  ('User 1 Task 2', '11111111-1111-1111-1111-111111111111'),
  ('User 2 Task 1', '22222222-2222-2222-2222-222222222222');

-- Test 1: Anonymous users cannot access todos
set local role anon;
select results_eq(
  'select count(*) from todos',
  ARRAY[0::bigint],
  'Anonymous users should not see any todos'
);

-- Test 2: Authenticated User 1 sees only their todos
set local role authenticated;
set local request.jwt.claim.sub = '11111111-1111-1111-1111-111111111111';

select results_eq(
  'select count(*) from todos',
  ARRAY[2::bigint],
  'User 1 should only see their 2 todos'
);

-- Test 3: User 1 can create their own todo
select lives_ok(
  $$insert into todos (task, user_id)
    values ('New Task', '11111111-1111-1111-1111-111111111111'::uuid)$$,
  'User 1 can create their own todo'
);

-- Test 4: User 1 cannot create todos for other users
select throws_ok(
  $$insert into todos (task, user_id)
    values ('Malicious', '22222222-2222-2222-2222-222222222222'::uuid)$$,
  'User 1 cannot create todos for other users'
);

-- Test 5: User 2 sees only their todos
set local request.jwt.claim.sub = '22222222-2222-2222-2222-222222222222';

select results_eq(
  'select count(*) from todos',
  ARRAY[1::bigint],
  'User 2 should only see their 1 todo'
);

-- Test 6: User 2 cannot modify User 1's todos
select results_ne(
  $$update todos set task = 'Hacked!'
    where user_id = '11111111-1111-1111-1111-111111111111'::uuid
    returning 1$$,
  $$values(1)$$,
  'User 2 cannot modify User 1 todos'
);

select * from finish();
rollback;
```

**Run tests with Supabase CLI:**

```bash
# Create test file
supabase test new todos_rls

# Run all database tests
supabase test db

# Expected output:
# supabase/tests/database/todos_rls.test.sql .. ok
# All tests successful.
# Result: PASS
```

**Test all CRUD operations:**

```sql
-- Test SELECT (covered above)

-- Test INSERT with policy violation
select throws_ok(
  $$insert into todos (task, user_id) values ('Bad', 'other-user-id')$$,
  'INSERT policy prevents creating records for other users'
);

-- Test UPDATE with policy violation
select is_empty(
  $$update todos set task = 'Changed'
    where user_id != auth.uid()
    returning id$$,
  'UPDATE policy prevents modifying other users records'
);

-- Test DELETE with policy violation
select is_empty(
  $$delete from todos
    where user_id != auth.uid()
    returning id$$,
  'DELETE policy prevents removing other users records'
);
```

**When NOT to use this pattern:**
- For trivial tables with no sensitive data (even then, consider basic tests)
- When using application-level testing exclusively (still recommended to complement)

Reference: [Supabase Testing Overview](https://supabase.com/docs/guides/local-development/testing/overview)
