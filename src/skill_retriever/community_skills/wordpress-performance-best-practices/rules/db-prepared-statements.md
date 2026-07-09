---
title: Use Prepared Statements for Database Queries
impact: CRITICAL
impactDescription: Prevents SQL injection and improves query plan caching
tags: security, database, wpdb, sql-injection
---

## Use Prepared Statements for Database Queries

Always use `$wpdb->prepare()` when executing database queries with user input or dynamic values. This prevents SQL injection attacks and allows the database to cache query execution plans. Never concatenate variables directly into SQL strings.

**Incorrect (vulnerable to SQL injection):**

```php
// Direct concatenation - NEVER do this
$user_id = $_GET['user_id'];
$results = $wpdb->get_results(
    "SELECT * FROM {$wpdb->posts} WHERE post_author = $user_id"
);

// String interpolation without prepare - still vulnerable
$meta_key = $request->get_param('key');
$wpdb->query(
    "DELETE FROM {$wpdb->postmeta} WHERE meta_key = '$meta_key'"
);
```

**Correct (using prepared statements):**

```php
// Always use $wpdb->prepare() with placeholders
$user_id = absint( $_GET['user_id'] );
$results = $wpdb->get_results(
    $wpdb->prepare(
        "SELECT * FROM {$wpdb->posts} WHERE post_author = %d",
        $user_id
    )
);

// Use appropriate placeholders: %d for integers, %s for strings, %f for floats
$meta_key = sanitize_key( $request->get_param('key') );
$wpdb->query(
    $wpdb->prepare(
        "DELETE FROM {$wpdb->postmeta} WHERE meta_key = %s",
        $meta_key
    )
);

// Multiple placeholders
$wpdb->get_row(
    $wpdb->prepare(
        "SELECT * FROM {$wpdb->posts} WHERE post_type = %s AND post_status = %s AND post_author = %d",
        'post',
        'publish',
        $user_id
    )
);
```

Note: Even when values are sanitized, always use `prepare()` as a defense-in-depth measure.

Reference: [WordPress Database API](https://developer.wordpress.org/reference/classes/wpdb/#protect-queries-against-sql-injection-attacks)
