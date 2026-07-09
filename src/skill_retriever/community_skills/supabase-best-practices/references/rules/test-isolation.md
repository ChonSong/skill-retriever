---
title: Use Transaction Isolation for Database Tests
impact: MEDIUM
impactDescription: Ensures reliable, repeatable test execution
tags: testing, isolation, transactions, pgtap
---

## Use Transaction Isolation for Database Tests

**Impact: MEDIUM (Ensures reliable, repeatable test execution)**

Wrap all pgTAP tests in transactions with `begin` and `rollback` to ensure test isolation. This prevents test data from persisting and allows tests to run independently without affecting each other.

**Incorrect (No transaction isolation):**

```sql
-- supabase/tests/database/bad_test.sql

-- No begin statement!
create extension if not exists pgtap with schema extensions;
select plan(1);

-- This data persists after the test!
insert into auth.users (id, email) values
  ('test-id', 'test@example.com');

select ok(true, 'Test passes but leaves garbage data');

select * from finish();
-- No rollback! Data persists and pollutes other tests
```

**Correct (Transaction-isolated tests):**

```sql
-- supabase/tests/database/good_test.sql
begin;  -- Start transaction

create extension if not exists pgtap with schema extensions;
select plan(3);

-- Test data is created within transaction
insert into auth.users (id, email) values
  ('test-user-1', 'user1@test.com'),
  ('test-user-2', 'user2@test.com');

insert into public.profiles (id, display_name) values
  ('test-user-1', 'Test User 1'),
  ('test-user-2', 'Test User 2');

-- Run your tests
select ok(
  (select count(*) from profiles) = 2,
  'Two profiles exist'
);

-- Simulate user context
set local role authenticated;
set local request.jwt.claim.sub = 'test-user-1';

select results_eq(
  'select display_name from profiles where id = auth.uid()',
  ARRAY['Test User 1'],
  'User can read own profile'
);

select is_empty(
  $$update profiles set display_name = 'Hacked'
    where id != auth.uid() returning id$$,
  'User cannot update other profiles'
);

select * from finish();
rollback;  -- All test data is cleaned up automatically
```

**For application-level tests, use unique identifiers:**

```typescript
// Application tests cannot use transactions
// Instead, generate unique IDs to avoid conflicts

import { describe, it, beforeAll, afterAll } from 'vitest'
import { createClient } from '@supabase/supabase-js'
import crypto from 'crypto'

describe('Profile RLS', () => {
  // Unique IDs prevent conflicts with other test runs
  const TEST_USER_ID = crypto.randomUUID()
  const TEST_EMAIL = `test-${TEST_USER_ID}@example.com`

  const adminClient = createClient(
    process.env.SUPABASE_URL!,
    process.env.SERVICE_ROLE_KEY!
  )

  beforeAll(async () => {
    // Create test user with unique ID
    await adminClient.auth.admin.createUser({
      id: TEST_USER_ID,
      email: TEST_EMAIL,
      password: 'testpassword123',
      email_confirm: true,
    })

    await adminClient.from('profiles').insert({
      id: TEST_USER_ID,
      display_name: 'Test User',
    })
  })

  afterAll(async () => {
    // Clean up test data
    await adminClient.from('profiles').delete().eq('id', TEST_USER_ID)
    await adminClient.auth.admin.deleteUser(TEST_USER_ID)
  })

  it('user can read own profile', async () => {
    const userClient = createClient(
      process.env.SUPABASE_URL!,
      process.env.SUPABASE_ANON_KEY!
    )

    await userClient.auth.signInWithPassword({
      email: TEST_EMAIL,
      password: 'testpassword123',
    })

    const { data } = await userClient
      .from('profiles')
      .select('*')
      .single()

    expect(data?.id).toBe(TEST_USER_ID)
  })
})
```

**Test isolation strategies comparison:**

| Strategy | Database Tests (pgTAP) | Application Tests |
|----------|------------------------|-------------------|
| Transaction wrap | ✅ Use `begin/rollback` | ❌ Not possible |
| Unique IDs | Optional | ✅ Required |
| Cleanup hooks | Not needed | ✅ Use `afterAll` |
| Parallel safe | ✅ Yes | ✅ With unique IDs |
| Speed | ✅ Fast | Slower |

**When NOT to use this pattern:**
- Never skip transaction isolation in pgTAP tests
- For integration tests that specifically need to test commit behavior

Reference: [Supabase Testing Overview](https://supabase.com/docs/guides/local-development/testing/overview)
