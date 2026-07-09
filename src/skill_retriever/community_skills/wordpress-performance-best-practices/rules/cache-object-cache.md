---
title: Leverage Object Cache with Cache Groups
impact: CRITICAL
impactDescription: Enables efficient cache invalidation and organization
tags: caching, object-cache, redis, memcached
---

## Leverage Object Cache with Cache Groups

Use `wp_cache_*` functions with cache groups for better organization and selective invalidation. Cache groups allow you to clear related cached items without flushing the entire cache. This is especially important on sites with persistent object caching (Redis, Memcached).

**Incorrect (no cache groups or poor invalidation):**

```php
// No cache group - hard to invalidate selectively
wp_cache_set( 'my_data_' . $user_id, $data );

// Deleting requires knowing exact keys
wp_cache_delete( 'my_data_123' );
wp_cache_delete( 'my_data_124' );
// ... impossible to clear all user data

// Using transients for frequently accessed data
set_transient( 'user_stats_' . $user_id, $stats, HOUR_IN_SECONDS );
```

**Correct (using cache groups):**

```php
// Use cache groups for logical organization
function get_user_stats( $user_id ) {
    $cache_key = 'stats_' . $user_id;
    $cache_group = 'user_stats';

    $stats = wp_cache_get( $cache_key, $cache_group );

    if ( false === $stats ) {
        $stats = calculate_user_stats( $user_id );
        wp_cache_set( $cache_key, $stats, $cache_group, HOUR_IN_SECONDS );
    }

    return $stats;
}

// Easy invalidation when user data changes
function invalidate_user_stats( $user_id ) {
    wp_cache_delete( 'stats_' . $user_id, 'user_stats' );
}

// Invalidate entire group by incrementing group version
function invalidate_all_user_stats() {
    // Instead of flushing, use versioned cache keys
    $version = wp_cache_get( 'version', 'user_stats' ) ?: 1;
    wp_cache_set( 'version', $version + 1, 'user_stats' );
}

// Versioned cache key pattern
function get_user_stats_versioned( $user_id ) {
    $version = wp_cache_get( 'version', 'user_stats' ) ?: 1;
    $cache_key = "stats_{$user_id}_v{$version}";

    $stats = wp_cache_get( $cache_key, 'user_stats' );

    if ( false === $stats ) {
        $stats = calculate_user_stats( $user_id );
        wp_cache_set( $cache_key, $stats, 'user_stats', HOUR_IN_SECONDS );
    }

    return $stats;
}

// Use wp_cache_add to prevent race conditions
function increment_page_views( $post_id ) {
    $cache_key = 'views_' . $post_id;
    $cache_group = 'page_views';

    // Only set if not exists
    $added = wp_cache_add( $cache_key, 1, $cache_group );

    if ( ! $added ) {
        // Key exists, increment it
        wp_cache_incr( $cache_key, 1, $cache_group );
    }
}

// Non-persistent cache for request-scoped data
function get_expensive_calculation() {
    static $result = null;

    if ( null === $result ) {
        // Use non-persistent group for single-request caching
        $result = wp_cache_get( 'calculation', 'non-persistent' );

        if ( false === $result ) {
            $result = perform_expensive_calculation();
            wp_cache_set( 'calculation', $result, 'non-persistent' );
        }
    }

    return $result;
}
```

Reference: [WordPress Object Cache](https://developer.wordpress.org/reference/classes/wp_object_cache/)
