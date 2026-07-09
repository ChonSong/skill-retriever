---
title: Validate All Inputs Before Processing
impact: HIGH
impactDescription: Prevents SQL injection and data corruption
tags: security, validation, inputs, sql-injection
---

## Validate All Inputs Before Processing

**Impact: HIGH (Prevents SQL injection and data corruption)**

Always validate and sanitize user inputs before using them in database queries, even when using parameterized queries. RLS protects row-level access, but input validation prevents malformed data, injection attacks through dynamic SQL, and business logic errors.

**Incorrect (trusting user input without validation):**

```typescript
// DON'T DO THIS - no input validation
async function searchProducts(req: Request) {
  const { query, limit, category } = await req.json()

  // Directly using unvalidated input
  const { data } = await supabase
    .from('products')
    .select('*')
    .ilike('name', `%${query}%`)  // Could contain SQL wildcards abuse
    .eq('category', category)      // Could be invalid category
    .limit(limit)                  // Could be negative or huge number

  return data
}

// DON'T DO THIS - dynamic SQL without validation
async function getDynamicReport(tableName: string, columns: string[]) {
  // SQL injection vulnerability with dynamic table/column names
  const query = `SELECT ${columns.join(', ')} FROM ${tableName}`
  const { data } = await supabase.rpc('run_sql', { query })
  return data
}
```

**Correct (validate all inputs):**

```typescript
import { z } from 'zod'

// Define strict schemas for all inputs
const searchSchema = z.object({
  query: z.string()
    .min(1)
    .max(100)
    .regex(/^[\w\s-]+$/, 'Only alphanumeric characters allowed'),
  limit: z.number()
    .int()
    .min(1)
    .max(100)
    .default(20),
  category: z.enum(['electronics', 'clothing', 'food', 'other']),
})

async function searchProducts(req: Request) {
  const body = await req.json()

  // Validate input - throws if invalid
  const { query, limit, category } = searchSchema.parse(body)

  // Now safe to use validated input
  const { data, error } = await supabase
    .from('products')
    .select('id, name, price, category')  // Explicit columns
    .ilike('name', `%${query}%`)
    .eq('category', category)
    .limit(limit)

  if (error) throw new Error('Search failed')
  return data
}
```

```typescript
// Safe dynamic queries with allowlists
const ALLOWED_TABLES = ['products', 'orders', 'customers'] as const
const ALLOWED_COLUMNS: Record<string, string[]> = {
  products: ['id', 'name', 'price', 'category'],
  orders: ['id', 'total', 'status', 'created_at'],
  customers: ['id', 'name', 'email'],
}

const reportSchema = z.object({
  table: z.enum(ALLOWED_TABLES),
  columns: z.array(z.string()),
})

async function getDynamicReport(input: unknown) {
  const { table, columns } = reportSchema.parse(input)

  // Validate columns against allowlist
  const allowedCols = ALLOWED_COLUMNS[table]
  const validColumns = columns.filter(col => allowedCols.includes(col))

  if (validColumns.length === 0) {
    throw new Error('No valid columns specified')
  }

  // Safe to use - table and columns are from allowlists
  const { data, error } = await supabase
    .from(table)
    .select(validColumns.join(', '))

  if (error) throw error
  return data
}
```

**Server-side validation with Edge Functions:**

```typescript
// supabase/functions/create-order/index.ts
import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { z } from 'https://deno.land/x/zod@v3.22.4/mod.ts'

const orderItemSchema = z.object({
  product_id: z.string().uuid(),
  quantity: z.number().int().min(1).max(100),
})

const orderSchema = z.object({
  items: z.array(orderItemSchema).min(1).max(50),
  shipping_address: z.object({
    street: z.string().min(5).max(200),
    city: z.string().min(2).max(100),
    postal_code: z.string().regex(/^\d{5}(-\d{4})?$/),
  }),
  notes: z.string().max(500).optional(),
})

serve(async (req) => {
  try {
    const body = await req.json()

    // Validate entire request
    const validatedOrder = orderSchema.parse(body)

    // Additional business logic validation
    const totalItems = validatedOrder.items.reduce(
      (sum, item) => sum + item.quantity,
      0
    )
    if (totalItems > 100) {
      return new Response(
        JSON.stringify({ error: 'Maximum 100 items per order' }),
        { status: 400 }
      )
    }

    // Process validated order...

  } catch (error) {
    if (error instanceof z.ZodError) {
      return new Response(
        JSON.stringify({
          error: 'Validation failed',
          details: error.errors
        }),
        { status: 400 }
      )
    }
    throw error
  }
})
```

**Database-level validation with constraints:**

```sql
-- Add database-level constraints as defense in depth
CREATE TABLE orders (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id),
  total_amount numeric(10,2) NOT NULL CHECK (total_amount >= 0),
  quantity integer NOT NULL CHECK (quantity BETWEEN 1 AND 100),
  status text NOT NULL CHECK (status IN ('pending', 'processing', 'shipped', 'delivered')),
  email text CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'),
  created_at timestamptz DEFAULT now()
);

-- Use domains for reusable validation
CREATE DOMAIN positive_amount AS numeric(10,2)
  CHECK (VALUE >= 0);

CREATE DOMAIN email_address AS text
  CHECK (VALUE ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$');

-- Apply domains to tables
ALTER TABLE customers
  ALTER COLUMN email TYPE email_address;
```

**Validation checklist:**

- **Type validation**: Ensure correct data types (string, number, boolean)
- **Range validation**: Check min/max values for numbers and string lengths
- **Format validation**: Use regex for emails, URLs, phone numbers
- **Allowlist validation**: For enums, use explicit lists of allowed values
- **Business logic**: Validate quantities, totals, dates make sense
- **SQL safety**: Never build SQL strings from user input without allowlists

**When NOT to use this pattern:**

- Internal system-to-system calls with trusted data (still recommended)
- Static configuration values not from user input (use allowlists anyway)

Reference: [OWASP Input Validation](https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html)
