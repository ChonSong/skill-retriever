---
title: Secure Database Triggers with SECURITY DEFINER
impact: HIGH
impactDescription: Prevents privilege escalation and ensures safe execution
tags: database, triggers, security, functions
---

## Secure Database Triggers with SECURITY DEFINER

**Impact: HIGH (Prevents privilege escalation and ensures safe execution)**

Database triggers execute automatically on data changes. When triggers need elevated privileges, use `SECURITY DEFINER` carefully with proper safeguards to prevent security vulnerabilities. Always set `search_path` and place trigger functions in private schemas.

**Incorrect (insecure trigger function):**

```sql
-- DON'T: SECURITY DEFINER without search_path
CREATE FUNCTION public.log_user_changes()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER  -- Runs as creator (superuser), but no search_path!
AS $$
BEGIN
  -- Vulnerable to search_path injection attacks
  INSERT INTO audit_logs (user_id, action, old_data, new_data)
  VALUES (NEW.id, TG_OP, row_to_json(OLD), row_to_json(NEW));
  RETURN NEW;
END;
$$;

-- DON'T: Trigger function in public schema with SECURITY DEFINER
-- Can be called directly via API, bypassing intended use
```

**Correct (secure trigger function):**

```sql
-- Create private schema for internal functions
CREATE SCHEMA IF NOT EXISTS private;
REVOKE ALL ON SCHEMA private FROM anon, authenticated;

-- Secure trigger function in private schema
CREATE FUNCTION private.handle_user_changes()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''  -- Prevent search_path injection
AS $$
BEGIN
  -- Use fully qualified table names
  INSERT INTO private.audit_logs (
    user_id,
    action,
    table_name,
    old_data,
    new_data,
    changed_at
  )
  VALUES (
    COALESCE(NEW.id, OLD.id),
    TG_OP,
    TG_TABLE_NAME,
    CASE WHEN TG_OP != 'INSERT' THEN row_to_json(OLD) END,
    CASE WHEN TG_OP != 'DELETE' THEN row_to_json(NEW) END,
    now()
  );

  RETURN COALESCE(NEW, OLD);
END;
$$;

-- Create trigger
CREATE TRIGGER on_user_change
  AFTER INSERT OR UPDATE OR DELETE ON public.users
  FOR EACH ROW
  EXECUTE FUNCTION private.handle_user_changes();
```

**Common trigger patterns:**

```sql
-- 1. Auto-populate created_at/updated_at timestamps
CREATE FUNCTION private.set_timestamps()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY INVOKER  -- No elevated privileges needed
SET search_path = ''
AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    NEW.created_at = COALESCE(NEW.created_at, now());
  END IF;
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

CREATE TRIGGER set_timestamps
  BEFORE INSERT OR UPDATE ON public.posts
  FOR EACH ROW
  EXECUTE FUNCTION private.set_timestamps();

-- 2. Sync user profile from auth.users (requires SECURITY DEFINER)
CREATE FUNCTION private.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
BEGIN
  INSERT INTO public.profiles (id, email, display_name)
  VALUES (
    NEW.id,
    NEW.email,
    COALESCE(NEW.raw_user_meta_data->>'display_name', split_part(NEW.email, '@', 1))
  );
  RETURN NEW;
END;
$$;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION private.handle_new_user();

-- 3. Prevent deletion of protected records
CREATE FUNCTION private.prevent_protected_delete()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
BEGIN
  IF OLD.is_protected THEN
    RAISE EXCEPTION 'Cannot delete protected record';
  END IF;
  RETURN OLD;
END;
$$;

CREATE TRIGGER protect_records
  BEFORE DELETE ON public.important_data
  FOR EACH ROW
  EXECUTE FUNCTION private.prevent_protected_delete();
```

**Error handling in triggers:**

```sql
CREATE FUNCTION private.safe_audit_trigger()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
BEGIN
  BEGIN
    -- Attempt audit insert
    INSERT INTO private.audit_logs (action, data)
    VALUES (TG_OP, row_to_json(NEW));
  EXCEPTION WHEN OTHERS THEN
    -- Log error but don't block the original operation
    RAISE WARNING 'Audit log failed: %', SQLERRM;
  END;

  RETURN NEW;
END;
$$;
```

**When NOT to use this pattern:**
- Simple operations that don't need elevated privileges (use `SECURITY INVOKER`)
- Functions that should respect the caller's RLS policies
- Performance-critical paths where trigger overhead is unacceptable

Reference: [Supabase Database Functions](https://supabase.com/docs/guides/database/functions)
