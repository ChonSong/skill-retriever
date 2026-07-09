---
title: Use WP_Query Instead of Direct Database Queries
impact: CRITICAL
impactDescription: Enables caching and maintains data integrity
tags: database, wp_query, caching, best-practice
---

## Use WP_Query Instead of Direct Database Queries

Always use WordPress API functions (WP_Query, get_posts, get_post_meta) instead of direct `$wpdb` queries when fetching WordPress data. WordPress APIs leverage the object cache, handle data sanitization, and maintain plugin compatibility through filters.

**Incorrect (direct database queries for WordPress data):**

```php
// Don't query posts table directly
global $wpdb;
$posts = $wpdb->get_results(
    "SELECT * FROM {$wpdb->posts} WHERE post_type = 'post' AND post_status = 'publish' ORDER BY post_date DESC LIMIT 10"
);

// Don't query postmeta directly
$meta_value = $wpdb->get_var(
    $wpdb->prepare(
        "SELECT meta_value FROM {$wpdb->postmeta} WHERE post_id = %d AND meta_key = %s",
        $post_id,
        'my_meta_key'
    )
);

// Don't query users directly
$users = $wpdb->get_results(
    "SELECT * FROM {$wpdb->users} WHERE user_status = 0"
);
```

**Correct (using WordPress APIs):**

```php
// Use WP_Query for posts - results are cached
$query = new WP_Query([
    'post_type'      => 'post',
    'post_status'    => 'publish',
    'posts_per_page' => 10,
    'orderby'        => 'date',
    'order'          => 'DESC',
]);

// Use get_post_meta - leverages object cache
$meta_value = get_post_meta( $post_id, 'my_meta_key', true );

// Use get_users or WP_User_Query
$users = get_users([
    'role'   => 'subscriber',
    'number' => 100,
]);

// For complex queries, use WP_Query with meta_query
$query = new WP_Query([
    'post_type'   => 'product',
    'meta_query'  => [
        [
            'key'     => 'price',
            'value'   => 100,
            'compare' => '>=',
            'type'    => 'NUMERIC',
        ],
    ],
]);
```

Direct `$wpdb` queries are appropriate only for custom tables or complex queries that cannot be expressed with WordPress APIs.

Reference: [WP_Query Documentation](https://developer.wordpress.org/reference/classes/wp_query/)
