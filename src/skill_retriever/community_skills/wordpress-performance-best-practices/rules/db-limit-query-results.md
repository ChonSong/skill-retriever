---
title: Always Limit Query Results
impact: CRITICAL
impactDescription: Prevents memory exhaustion and timeout errors
tags: database, wp_query, memory, performance
---

## Always Limit Query Results

Never use `posts_per_page => -1` or `nopaging => true` in production code. Unlimited queries can return thousands of posts, causing memory exhaustion, slow page loads, and server timeouts. Always set reasonable limits and implement pagination.

**Incorrect (unlimited queries):**

```php
// NEVER do this - can return millions of rows
$all_posts = new WP_Query([
    'post_type'      => 'post',
    'posts_per_page' => -1, // Dangerous!
]);

// Also dangerous
$all_products = get_posts([
    'post_type' => 'product',
    'nopaging'  => true, // Equally dangerous
]);

// Hidden danger - forgetting to set limit
$query = new WP_Query([
    'post_type' => 'attachment',
    // No posts_per_page set - defaults to blog setting but still risky
]);
```

**Correct (always limit results):**

```php
// Set explicit limits
$posts = new WP_Query([
    'post_type'      => 'post',
    'posts_per_page' => 100,
    'paged'          => get_query_var( 'paged' ) ?: 1,
]);

// For batch processing, use pagination
function process_all_posts_in_batches() {
    $paged = 1;
    $per_page = 100;

    do {
        $query = new WP_Query([
            'post_type'      => 'post',
            'posts_per_page' => $per_page,
            'paged'          => $paged,
            'fields'         => 'ids', // Only fetch IDs if that's all you need
        ]);

        foreach ( $query->posts as $post_id ) {
            // Process each post
            process_single_post( $post_id );
        }

        $paged++;

        // Clear memory between batches
        wp_cache_flush();

    } while ( $query->have_posts() );
}

// If you truly need all IDs, use fields => 'ids' to minimize memory
$all_ids = get_posts([
    'post_type'      => 'post',
    'posts_per_page' => 1000, // Still set a reasonable max
    'fields'         => 'ids',
]);
```

For WP-CLI commands or background processing where all items must be processed, use batching with proper memory management.

Reference: [WordPress VIP Documentation](https://docs.wpvip.com/technical-references/code-quality-and-best-practices/)
