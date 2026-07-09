---
title: Regularly Run Security Advisor Checks
impact: HIGH
impactDescription: Catches security misconfigurations before exploitation
tags: security, audit, advisors, linting, monitoring
---

## Regularly Run Security Advisor Checks

**Impact: HIGH (Catches security misconfigurations before exploitation)**

Supabase provides built-in Security Advisors that detect common security misconfigurations like missing RLS policies, overly permissive policies, and exposed tables. Run these checks regularly (especially after schema changes) and address all findings to maintain a secure posture.

**Incorrect (ignoring security advisors):**

```typescript
// DON'T DO THIS - deploying without security checks
async function deployMigration() {
  await supabase.rpc('run_migration', { sql: migrationSql })
  // No security validation after schema changes!
  console.log('Migration deployed')
}

// DON'T DO THIS - creating tables without checking advisors
// New table created, but never validated for security
```

**Correct (integrate security checks into workflow):**

```typescript
// Run security advisors after deployments
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  process.env.SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
)

async function runSecurityAudit() {
  // Check security advisors via Management API
  const response = await fetch(
    `https://api.supabase.com/v1/projects/${projectRef}/advisors/security`,
    {
      headers: {
        'Authorization': `Bearer ${process.env.SUPABASE_ACCESS_TOKEN}`,
        'Content-Type': 'application/json'
      }
    }
  )

  const advisors = await response.json()

  // Categorize findings by severity
  const errors = advisors.filter((a: any) => a.level === 'ERROR')
  const warnings = advisors.filter((a: any) => a.level === 'WARN')
  const info = advisors.filter((a: any) => a.level === 'INFO')

  console.log(`Security Audit Results:`)
  console.log(`  Errors: ${errors.length}`)
  console.log(`  Warnings: ${warnings.length}`)
  console.log(`  Info: ${info.length}`)

  // Fail CI/CD if critical issues found
  if (errors.length > 0) {
    console.error('\nCritical security issues found:')
    for (const error of errors) {
      console.error(`  - ${error.title}: ${error.detail}`)
      console.error(`    Remediation: ${error.remediation}`)
    }
    process.exit(1)
  }

  // Warn about non-critical issues
  if (warnings.length > 0) {
    console.warn('\nSecurity warnings:')
    for (const warning of warnings) {
      console.warn(`  - ${warning.title}: ${warning.detail}`)
    }
  }

  return advisors
}
```

**Common Security Advisor findings and fixes:**

```sql
-- FINDING: "RLS Disabled in Public" (ERROR)
-- Table is exposed via API without RLS protection

-- FIX: Enable RLS and add policies
ALTER TABLE public.user_data ENABLE ROW LEVEL SECURITY;

CREATE POLICY "users_own_data"
ON public.user_data
FOR ALL
TO authenticated
USING ((SELECT auth.uid()) = user_id)
WITH CHECK ((SELECT auth.uid()) = user_id);


-- FINDING: "Policy Exists RLS Disabled" (ERROR)
-- Policies exist but RLS isn't enabled (policies have no effect!)

-- FIX: Enable RLS to activate the policies
ALTER TABLE public.orders ENABLE ROW LEVEL SECURITY;


-- FINDING: "RLS Enabled No Policy" (INFO)
-- RLS is on but no policies exist (blocks all access)

-- FIX: Add appropriate policies
CREATE POLICY "authenticated_select"
ON public.products
FOR SELECT
TO authenticated
USING (true);  -- Public read is intentional for this table


-- FINDING: "RLS Policy Always True" (WARN)
-- Policy uses USING(true) for INSERT/UPDATE/DELETE

-- FIX: Add proper authorization check
-- BEFORE (insecure):
CREATE POLICY "insecure_insert"
ON public.comments FOR INSERT
WITH CHECK (true);  -- Anyone can insert!

-- AFTER (secure):
DROP POLICY "insecure_insert" ON public.comments;
CREATE POLICY "secure_insert"
ON public.comments FOR INSERT
TO authenticated
WITH CHECK ((SELECT auth.uid()) = user_id);


-- FINDING: "Function Search Path Mutable" (WARN)
-- Function doesn't set search_path, vulnerable to hijacking

-- FIX: Set explicit search_path
CREATE OR REPLACE FUNCTION my_function()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp  -- Explicit search path
AS $$
BEGIN
  -- Function body
END;
$$;
```

**Automated security checks in CI/CD:**

```yaml
# .github/workflows/security-check.yml
name: Security Audit

on:
  push:
    paths:
      - 'supabase/migrations/**'
  pull_request:
    paths:
      - 'supabase/migrations/**'

jobs:
  security-audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run Security Advisors
        env:
          SUPABASE_ACCESS_TOKEN: ${{ secrets.SUPABASE_ACCESS_TOKEN }}
          PROJECT_REF: ${{ secrets.SUPABASE_PROJECT_REF }}
        run: |
          # Fetch security advisors
          RESPONSE=$(curl -s \
            -H "Authorization: Bearer $SUPABASE_ACCESS_TOKEN" \
            "https://api.supabase.com/v1/projects/$PROJECT_REF/advisors/security")

          # Check for errors
          ERRORS=$(echo $RESPONSE | jq '[.[] | select(.level == "ERROR")] | length')

          if [ "$ERRORS" -gt 0 ]; then
            echo "::error::Found $ERRORS critical security issues"
            echo $RESPONSE | jq '.[] | select(.level == "ERROR")'
            exit 1
          fi

          # Report warnings
          WARNINGS=$(echo $RESPONSE | jq '[.[] | select(.level == "WARN")] | length')
          if [ "$WARNINGS" -gt 0 ]; then
            echo "::warning::Found $WARNINGS security warnings"
            echo $RESPONSE | jq '.[] | select(.level == "WARN")'
          fi

          echo "Security audit passed"
```

**Security Advisor categories:**

| Level | Meaning | Action Required |
|-------|---------|-----------------|
| ERROR | Critical vulnerability | Fix immediately before deployment |
| WARN | Potential security issue | Review and fix in current sprint |
| INFO | Informational finding | Review for best practices |

**Key advisors to watch for:**

1. **rls_disabled_in_public** (ERROR): Tables exposed without RLS
2. **policy_exists_rls_disabled** (ERROR): Policies exist but RLS not enabled
3. **rls_enabled_no_policy** (INFO): RLS enabled but no policies (blocks all access)
4. **rls_policy_always_true** (WARN): Overly permissive policies
5. **function_search_path_mutable** (WARN): Functions vulnerable to path hijacking
6. **leaked_service_role_key** (ERROR): Service role key exposed in client code

**Dashboard access:**

Access Security Advisors in Supabase Dashboard:
1. Go to **Database** > **Linting**
2. Or use **Advisors** > **Security**
3. Filter by severity level
4. Click remediation links for detailed guidance

**When NOT to use this pattern:**

- There are no exceptions - always run security checks
- Even "internal" projects should maintain security hygiene

Reference: [Supabase Database Linter](https://supabase.com/docs/guides/database/database-linter)
