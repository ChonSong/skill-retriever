---
title: Implement Proper Cache Invalidation
impact: HIGH
impactDescription: Prevents stale data without excessive cache clearing
tags: caching, invalidation, hooks, data-integrity
---

## Implement Proper Cache Invalidation

Cache invalidation should be precise and event-driven. Clear only the specific cached data that changed, not entire caches. Hook into WordPress actions to automatically invalidate caches when underlying data changes.

**Incorrect (over-aggressive or missing invalidation):**

```php
// Nuclear option - clears everything
function on_post_save( $post_id ) {
    wp_cache_flush(); // Don't do this!
}
add_action( 'save_post', 'on_post_save' );

// Clearing too much
function clear_post_caches( $post_id ) {
    delete_transient( 'all_posts_cache' );
    delete_transient( 'featured_posts' );
    delete_transient( 'sidebar_posts' );
    delete_transient( 'homepage_posts' );
    // ... 20 more transients
}

// No invalidation at all - stale data forever
function get_post_stats( $post_id ) {
    $stats = get_transient( 'post_stats_' . $post_id );
    if ( ! $stats ) {
        $stats = calculate_post_stats( $post_id );
        set_transient( 'post_stats_' . $post_id, $stats, WEEK_IN_SECONDS );
    }
    return $stats;
}
```

**Correct (precise, event-driven invalidation):**

```php
// Invalidate only affected caches
function invalidate_post_cache( $post_id, $post, $update ) {
    // Clear this specific post's cache
    wp_cache_delete( 'post_stats_' . $post_id, 'post_stats' );
    delete_transient( 'post_views_' . $post_id );

    // Clear caches that include this post
    $post_type = get_post_type( $post_id );
    wp_cache_delete( "latest_{$post_type}", 'archive_queries' );

    // Clear term-related caches
    $terms = wp_get_post_terms( $post_id, 'category', ['fields' => 'ids'] );
    foreach ( $terms as $term_id ) {
        wp_cache_delete( 'category_posts_' . $term_id, 'category_queries' );
    }
}
add_action( 'save_post', 'invalidate_post_cache', 10, 3 );

// Use versioned cache keys for bulk invalidation
class Post_Cache {
    private static function get_version() {
        $version = wp_cache_get( 'posts_cache_version', 'versions' );
        if ( false === $version ) {
            $version = 1;
            wp_cache_set( 'posts_cache_version', $version, 'versions' );
        }
        return $version;
    }

    public static function get( $key ) {
        $versioned_key = $key . '_v' . self::get_version();
        return wp_cache_get( $versioned_key, 'posts' );
    }

    public static function set( $key, $data, $expiration = 3600 ) {
        $versioned_key = $key . '_v' . self::get_version();
        return wp_cache_set( $versioned_key, $data, 'posts', $expiration );
    }

    public static function invalidate_all() {
        // Increment version instead of deleting all keys
        $version = self::get_version();
        wp_cache_set( 'posts_cache_version', $version + 1, 'versions' );
    }
}

// Invalidate on relevant hooks
add_action( 'save_post', function( $post_id ) {
    wp_cache_delete( 'single_post_' . $post_id, 'posts' );
});

add_action( 'deleted_post', function( $post_id ) {
    wp_cache_delete( 'single_post_' . $post_id, 'posts' );
    Post_Cache::invalidate_all(); // Bulk queries might be affected
});

add_action( 'transition_post_status', function( $new, $old, $post ) {
    if ( $new !== $old ) {
        // Status changed, invalidate archive caches
        wp_cache_delete( 'archive_' . $post->post_type, 'archives' );
    }
}, 10, 3 );

// Clean up expired transients periodically
add_action( 'wp_scheduled_delete', function() {
    global $wpdb;
    $wpdb->query(
        "DELETE a, b FROM {$wpdb->options} a
        INNER JOIN {$wpdb->options} b ON b.option_name = CONCAT('_transient_timeout_', SUBSTRING(a.option_name, 12))
        WHERE a.option_name LIKE '_transient_%'
        AND b.option_value < UNIX_TIMESTAMP()"
    );
});
```

Reference: [WordPress Cache API](https://developer.wordpress.org/reference/functions/wp_cache_delete/)
