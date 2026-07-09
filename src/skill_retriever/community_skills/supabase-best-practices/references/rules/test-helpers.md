---
title: Use Test Helper Functions for Supabase Testing
impact: MEDIUM
impactDescription: Reduces test boilerplate and improves maintainability
tags: testing, helpers, pgtap, utilities
---

## Use Test Helper Functions for Supabase Testing

**Impact: MEDIUM (Reduces test boilerplate and improves maintainability)**

Create reusable helper functions for common test operations like user authentication simulation, role switching, and test data creation. This reduces duplication and makes tests more readable.

**Incorrect (Repeated boilerplate in every test):**

```sql
-- Test 1
begin;
create extension if not exists pgtap with schema extensions;
select plan(1);

-- Manually setting up auth every time
insert into auth.users (id, email) values ('user-1', 'test@test.com');
set local role authenticated;
set local request.jwt.claim.sub = 'user-1';
set local request.jwt.claims = '{"sub": "user-1", "role": "authenticated"}';

-- Test logic...
select * from finish();
rollback;

-- Test 2 - Same boilerplate repeated!
begin;
create extension if not exists pgtap with schema extensions;
select plan(1);
insert into auth.users (id, email) values ('user-2', 'test2@test.com');
set local role authenticated;
set local request.jwt.claim.sub = 'user-2';
-- ...
```

**Correct (Use test helper functions):**

```sql
-- supabase/tests/database/helpers.sql
-- Create helper functions in a separate file or at the start of tests

-- Helper: Create a test user and return their ID
create or replace function tests.create_test_user(
  p_email text default 'test@example.com',
  p_id uuid default gen_random_uuid()
)
returns uuid
language plpgsql
security definer
as $$
begin
  insert into auth.users (id, email, encrypted_password, email_confirmed_at)
  values (p_id, p_email, crypt('password123', gen_salt('bf')), now());
  return p_id;
end;
$$;

-- Helper: Authenticate as a specific user
create or replace function tests.authenticate_as(p_user_id uuid)
returns void
language plpgsql
as $$
begin
  set local role authenticated;
  execute format('set local request.jwt.claim.sub = %L', p_user_id);
  execute format(
    'set local request.jwt.claims = %L',
    json_build_object(
      'sub', p_user_id,
      'role', 'authenticated',
      'aal', 'aal1'
    )::text
  );
end;
$$;

-- Helper: Authenticate as anonymous
create or replace function tests.authenticate_anon()
returns void
language plpgsql
as $$
begin
  set local role anon;
  set local request.jwt.claims = '{}';
end;
$$;

-- Helper: Authenticate with organization context (Clerk)
create or replace function tests.authenticate_with_org(
  p_user_id uuid,
  p_org_id text,
  p_org_role text default 'org:member'
)
returns void
language plpgsql
as $$
begin
  set local role authenticated;
  execute format('set local request.jwt.claim.sub = %L', p_user_id);
  execute format(
    'set local request.jwt.claims = %L',
    json_build_object(
      'sub', p_user_id,
      'role', 'authenticated',
      'org_id', p_org_id,
      'org_role', p_org_role
    )::text
  );
end;
$$;
```

**Using helpers in tests:**

```sql
-- supabase/tests/database/profiles_rls.test.sql
begin;
create extension if not exists pgtap with schema extensions;

-- Load helpers (or include them in the test file)
\i tests/database/helpers.sql

select plan(5);

-- Create test users with helper
select tests.create_test_user('alice@test.com', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa');
select tests.create_test_user('bob@test.com', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb');

-- Create test data
insert into public.profiles (id, display_name, is_public) values
  ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'Alice', true),
  ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'Bob', false);

-- Test 1: Anonymous can see public profiles
select tests.authenticate_anon();
select results_eq(
  'select display_name from profiles where is_public = true',
  ARRAY['Alice'],
  'Anonymous users can see public profiles'
);

-- Test 2: Alice can see her own profile
select tests.authenticate_as('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid);
select results_eq(
  'select display_name from profiles where id = auth.uid()',
  ARRAY['Alice'],
  'Alice can see her own profile'
);

-- Test 3: Alice can update her own profile
select lives_ok(
  $$update profiles set display_name = 'Alice Updated' where id = auth.uid()$$,
  'Alice can update her own profile'
);

-- Test 4: Alice cannot update Bob's profile
select is_empty(
  $$update profiles set display_name = 'Hacked'
    where id = 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb' returning id$$,
  'Alice cannot update Bob profile'
);

-- Test 5: Org admin can manage team profiles
select tests.authenticate_with_org(
  'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid,
  'org_123',
  'org:admin'
);
select ok(
  ((select current_setting('request.jwt.claims', true))::json->>'org_role') = 'org:admin',
  'Org admin context is set correctly'
);

select * from finish();
rollback;
```

**Community test helpers (basejump):**

```sql
-- Install community test helpers from database.dev
-- https://database.dev/basejump/supabase_test_helpers

-- These provide additional utilities:
-- - create_supabase_user()
-- - authenticate_as()
-- - switch_to_anon()
-- - tests.rls_enabled()
-- - tests.policy_exists()
```

**CI/CD integration:**

```yaml
# .github/workflows/db-tests.yml
name: Database Tests

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Supabase CLI
        uses: supabase/setup-cli@v1

      - name: Start Supabase
        run: supabase start

      - name: Run Database Tests
        run: supabase test db
```

**When NOT to use this pattern:**
- For single, simple tests that don't benefit from abstraction
- When helpers would obscure what the test is actually testing

Reference: [Supabase Test Helpers](https://database.dev/basejump/supabase_test_helpers)
