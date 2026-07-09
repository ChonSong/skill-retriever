---
title: Request Only Required Fields
impact: HIGH
impactDescription: 50-80% memory reduction for ID-only queries
tags: database, wp_query, memory, optimization
---

## Request Only Required Fields

When you only need post IDs or specific fields, use the `fields` parameter to avoid fetching complete post objects. This significantly reduces memory usage and query time, especially when processing large numbers of posts.

**Incorrect (fetching full objects when not needed):**

```php
// Fetches all post data when only IDs are needed
$query = new WP_Query([
    'post_type'      => 'post',
    'posts_per_page' => 1000,
]);

$post_ids = wp_list_pluck( $query->posts, 'ID' );

// Fetches full objects just to count
$all_posts = get_posts([
    'post_type'   => 'product',
    'numberposts' => -1,
]);
$count = count( $all_posts );

// Unnecessary object hydration
foreach ( get_posts(['numberposts' => 100]) as $post ) {
    update_post_meta( $post->ID, 'processed', true );
}
```

**Correct (requesting only needed fields):**

```php
// Use fields => 'ids' when only IDs are needed
$query = new WP_Query([
    'post_type'      => 'post',
    'posts_per_page' => 1000,
    'fields'         => 'ids', // Returns array of IDs
]);

$post_ids = $query->posts; // Already an array of IDs

// Use found_posts for counting
$query = new WP_Query([
    'post_type'      => 'product',
    'posts_per_page' => 1, // Minimal fetch
    'fields'         => 'ids',
]);
$count = $query->found_posts;

// Or use wp_count_posts() for simple counts
$counts = wp_count_posts( 'product' );
$published_count = $counts->publish;

// Use fields => 'ids' for batch operations
$post_ids = get_posts([
    'post_type'   => 'post',
    'numberposts' => 100,
    'fields'      => 'ids',
]);

foreach ( $post_ids as $post_id ) {
    update_post_meta( $post_id, 'processed', true );
}

// Use fields => 'id=>parent' for hierarchy operations
$query = new WP_Query([
    'post_type' => 'page',
    'fields'    => 'id=>parent', // Returns array of stdClass with ID and post_parent
]);
```

Available `fields` values:
- `'ids'` - Returns array of post IDs
- `'id=>parent'` - Returns array of objects with ID and post_parent

Reference: [WP_Query fields parameter](https://developer.wordpress.org/reference/classes/wp_query/#return-fields-parameter)
