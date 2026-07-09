---
title: Avoid post__not_in in WP_Query
impact: CRITICAL
impactDescription: Can cause 10-100x slower queries on large sites
tags: database, wp_query, performance, vip
---

## Avoid post__not_in in WP_Query

The `post__not_in` parameter in WP_Query creates a `NOT IN` SQL clause that cannot use indexes effectively. On sites with large posts tables, this causes full table scans and severely impacts performance. This is explicitly flagged by WordPress VIP coding standards.

**Incorrect (using post__not_in):**

```php
// Avoid - causes performance issues on large sites
$query = new WP_Query([
    'post_type'    => 'post',
    'post__not_in' => get_option( 'sticky_posts' ),
]);

// Also problematic in pre_get_posts
add_action( 'pre_get_posts', function( $query ) {
    if ( $query->is_main_query() && $query->is_home() ) {
        $exclude_ids = get_posts_to_exclude();
        $query->set( 'post__not_in', $exclude_ids );
    }
});
```

**Correct (filter results in PHP or use alternative approaches):**

```php
// Option 1: Filter results in PHP (preferred for small exclusion lists)
$sticky_posts = get_option( 'sticky_posts' );
$query = new WP_Query([
    'post_type'      => 'post',
    'posts_per_page' => 15, // Fetch extra to account for filtering
]);

$filtered_posts = array_filter( $query->posts, function( $post ) use ( $sticky_posts ) {
    return ! in_array( $post->ID, $sticky_posts, true );
});

// Option 2: Use post__in with the IDs you want (if known)
$wanted_ids = array_diff( $all_ids, $excluded_ids );
$query = new WP_Query([
    'post_type' => 'post',
    'post__in'  => $wanted_ids,
    'orderby'   => 'post__in',
]);

// Option 3: Use meta query or taxonomy query for exclusion logic
$query = new WP_Query([
    'post_type'  => 'post',
    'meta_query' => [
        [
            'key'     => '_is_excluded',
            'compare' => 'NOT EXISTS',
        ],
    ],
]);

// Option 4: For sticky posts specifically, use ignore_sticky_posts
$query = new WP_Query([
    'post_type'           => 'post',
    'ignore_sticky_posts' => true,
]);
```

The same applies to `tag__not_in` and `category__not_in` - avoid these parameters on high-traffic sites.

Reference: [WordPress VIP Code Analysis](https://docs.wpvip.com/technical-references/code-quality-and-best-practices/)
