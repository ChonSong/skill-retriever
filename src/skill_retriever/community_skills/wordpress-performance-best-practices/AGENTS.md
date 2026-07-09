# WordPress Performance Best Practices

**Version 1.0.0**
WordPress Performance Community
January 2026

> **Note:** This document is designed for AI agents and LLMs assisting with WordPress development. It provides structured performance guidelines with clear examples of incorrect and correct implementations.

## Abstract

Comprehensive performance optimization guide for WordPress development, designed for AI agents and LLMs assisting developers. This document covers database optimization, caching strategies, asset management, theme development, plugin architecture, media handling, API optimization, and advanced performance patterns. Rules are based on WordPress VIP coding standards, 10up engineering best practices, and official WordPress developer documentation. Each rule includes impact assessment, clear explanations, and practical code examples demonstrating both anti-patterns and recommended implementations.

## Table of Contents

### 1. Database Optimization (CRITICAL)

- [1.1 Avoid post__not_in in WP_Query](#11-avoid-post-not-in-in-wp-query)
- [1.2 Request Only Required Fields](#12-request-only-required-fields)
- [1.3 Always Limit Query Results](#13-always-limit-query-results)
- [1.4 Optimize Meta Queries with Proper Indexing](#14-optimize-meta-queries-with-proper-indexing)
- [1.5 Use Prepared Statements for Database Queries](#15-use-prepared-statements-for-database-queries)
- [1.6 Use WP_Query Instead of Direct Database Queries](#16-use-wp-query-instead-of-direct-database-queries)

### 2. Caching Strategies (CRITICAL)

- [2.1 Use Fragment Caching for Expensive Template Parts](#21-use-fragment-caching-for-expensive-template-parts)
- [2.2 Implement Proper Cache Invalidation](#22-implement-proper-cache-invalidation)
- [2.3 Leverage Object Cache with Cache Groups](#23-leverage-object-cache-with-cache-groups)
- [2.4 Cache Remote HTTP Requests](#24-cache-remote-http-requests)
- [2.5 Use Transients for Expensive External Operations](#25-use-transients-for-expensive-external-operations)

### 3. Asset Management (HIGH)

- [3.1 Load Assets Conditionally](#31-load-assets-conditionally)
- [3.2 Use Defer and Async for Non-Critical Scripts](#32-use-defer-and-async-for-non-critical-scripts)
- [3.3 Dequeue Unused Plugin Assets](#33-dequeue-unused-plugin-assets)
- [3.4 Minify and Combine Assets Appropriately](#34-minify-and-combine-assets-appropriately)
- [3.5 Use Proper Script and Style Enqueueing](#35-use-proper-script-and-style-enqueueing)

### 4. Theme Performance (HIGH)

- [4.1 Avoid Database Queries in Templates](#41-avoid-database-queries-in-templates)
- [4.2 Place Hooks at Appropriate Priority Levels](#42-place-hooks-at-appropriate-priority-levels)
- [4.3 Optimize WordPress Loops](#43-optimize-wordpress-loops)
- [4.4 Use Template Parts Efficiently](#44-use-template-parts-efficiently)

### 5. Plugin Architecture (MEDIUM-HIGH)

- [5.1 Use Activation and Deactivation Hooks Properly](#51-use-activation-and-deactivation-hooks-properly)
- [5.2 Use Autoloading for Plugin Classes](#52-use-autoloading-for-plugin-classes)
- [5.3 Load Plugin Code Conditionally](#53-load-plugin-code-conditionally)
- [5.4 Remove Hooks Properly When Needed](#54-remove-hooks-properly-when-needed)

### 6. Media Optimization (MEDIUM)

- [6.1 Define and Use Appropriate Image Sizes](#61-define-and-use-appropriate-image-sizes)
- [6.2 Implement Proper Lazy Loading](#62-implement-proper-lazy-loading)
- [6.3 Use Responsive Images Properly](#63-use-responsive-images-properly)

### 7. API and AJAX (MEDIUM)

- [7.1 Avoid Admin-Ajax Bottleneck](#71-avoid-admin-ajax-bottleneck)
- [7.2 Implement Proper Nonce Validation](#72-implement-proper-nonce-validation)
- [7.3 Optimize REST API Endpoints](#73-optimize-rest-api-endpoints)

### 8. Advanced Patterns (LOW-MEDIUM)

- [8.1 Optimize Options Autoloading](#81-optimize-options-autoloading)
- [8.2 Optimize WP-Cron Usage](#82-optimize-wp-cron-usage)
- [8.3 Manage Memory Usage Effectively](#83-manage-memory-usage-effectively)
- [8.4 Profile and Monitor Performance](#84-profile-and-monitor-performance)

---

## 1. Database Optimization

**Impact Level:** CRITICAL

Database queries are the primary bottleneck in WordPress performance. Unoptimized queries, missing indexes, direct database access, and improper use of WP_Query can cause severe slowdowns, especially on high-traffic sites. Following WordPress VIP standards for database operations is essential for scalable applications.

### 1.1 Avoid post__not_in in WP_Query

**Impact: CRITICAL (Can cause 10-100x slower queries on large sites)**

*Tags: database, wp_query, performance, vip*

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

### 1.2 Request Only Required Fields

**Impact: HIGH (50-80% memory reduction for ID-only queries)**

*Tags: database, wp_query, memory, optimization*

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

### 1.3 Always Limit Query Results

**Impact: CRITICAL (Prevents memory exhaustion and timeout errors)**

*Tags: database, wp_query, memory, performance*

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

### 1.4 Optimize Meta Queries with Proper Indexing

**Impact: HIGH (5-50x improvement for meta-heavy queries)**

*Tags: database, meta_query, indexing, performance*

Meta queries (`meta_query` in WP_Query) can be slow because the postmeta table's default indexes don't cover all query patterns. For frequently queried meta keys, consider adding custom indexes or using alternative data structures like taxonomies.

**Incorrect (unoptimized meta queries):**

```php
// Slow - multiple meta conditions without index optimization
$query = new WP_Query([
    'post_type'  => 'product',
    'meta_query' => [
        'relation' => 'AND',
        [
            'key'     => 'price',
            'value'   => [10, 100],
            'compare' => 'BETWEEN',
            'type'    => 'NUMERIC',
        ],
        [
            'key'     => 'stock_status',
            'value'   => 'instock',
        ],
        [
            'key'     => 'featured',
            'value'   => '1',
        ],
    ],
]);

// Slow - LIKE queries on meta_value
$query = new WP_Query([
    'meta_query' => [
        [
            'key'     => 'description',
            'value'   => 'keyword',
            'compare' => 'LIKE', // Cannot use index
        ],
    ],
]);
```

**Correct (optimized approaches):**

```php
// Option 1: Use taxonomies for filterable attributes (preferred)
// Register a custom taxonomy instead of meta for frequently filtered values
register_taxonomy( 'stock_status', 'product', [
    'hierarchical' => false,
    'public'       => false,
    'rewrite'      => false,
] );

// Query using taxonomy - much faster
$query = new WP_Query([
    'post_type' => 'product',
    'tax_query' => [
        [
            'taxonomy' => 'stock_status',
            'field'    => 'slug',
            'terms'    => 'instock',
        ],
    ],
]);

// Option 2: Add custom index for frequently queried meta keys
// Run once during plugin activation
function add_custom_meta_index() {
    global $wpdb;

    // Check if index exists first
    $index_exists = $wpdb->get_var(
        "SHOW INDEX FROM {$wpdb->postmeta} WHERE Key_name = 'meta_key_value'"
    );

    if ( ! $index_exists ) {
        $wpdb->query(
            "ALTER TABLE {$wpdb->postmeta} ADD INDEX meta_key_value (meta_key(191), meta_value(100))"
        );
    }
}

// Option 3: Minimize meta conditions and use post__in for complex filters
$product_ids = get_products_by_price_range( 10, 100 ); // Custom cached function
$query = new WP_Query([
    'post_type' => 'product',
    'post__in'  => $product_ids,
    'orderby'   => 'post__in',
]);

// Option 4: Use EXISTS instead of value comparison when possible
$query = new WP_Query([
    'post_type'  => 'product',
    'meta_query' => [
        [
            'key'     => 'featured',
            'compare' => 'EXISTS', // Faster than checking value
        ],
    ],
]);
```

Consider using a dedicated search solution (Elasticsearch, Algolia) for complex filtering requirements.

Reference: [10up Engineering Best Practices](https://10up.github.io/Engineering-Best-Practices/php/#performance)

### 1.5 Use Prepared Statements for Database Queries

**Impact: CRITICAL (Prevents SQL injection and improves query plan caching)**

*Tags: security, database, wpdb, sql-injection*

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

### 1.6 Use WP_Query Instead of Direct Database Queries

**Impact: CRITICAL (Enables caching and maintains data integrity)**

*Tags: database, wp_query, caching, best-practice*

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

---

## 2. Caching Strategies

**Impact Level:** CRITICAL

Effective caching reduces server load by avoiding redundant computations and database queries. Understanding when to use transients vs object cache, implementing proper cache invalidation, and leveraging page caching are fundamental to WordPress performance optimization.

### 2.1 Use Fragment Caching for Expensive Template Parts

**Impact: HIGH (Reduces template rendering time by 50-90%)**

*Tags: caching, templates, fragments, performance*

Cache expensive template fragments (widgets, complex loops, sidebars) separately from full-page caching. This allows dynamic pages to still benefit from caching static portions. Fragment caching is especially useful for logged-in users where page caching isn't possible.

**Incorrect (regenerating expensive content on every request):**

```php
// Sidebar regenerated on every page load
function render_popular_posts_widget() {
    $posts = new WP_Query([
        'post_type'      => 'post',
        'posts_per_page' => 5,
        'meta_key'       => 'views',
        'orderby'        => 'meta_value_num',
        'order'          => 'DESC',
    ]);

    ob_start();
    while ( $posts->have_posts() ) {
        $posts->the_post();
        // Complex template rendering
        get_template_part( 'partials/popular-post' );
    }
    wp_reset_postdata();
    return ob_get_clean();
}

// Navigation menu regenerated on every page
wp_nav_menu(['theme_location' => 'primary']);
```

**Correct (fragment caching):**

```php
// Cache expensive widget output
function render_popular_posts_widget() {
    $cache_key = 'popular_posts_widget';
    $output = wp_cache_get( $cache_key, 'widget_fragments' );

    if ( false === $output ) {
        $posts = new WP_Query([
            'post_type'      => 'post',
            'posts_per_page' => 5,
            'meta_key'       => 'views',
            'orderby'        => 'meta_value_num',
            'order'          => 'DESC',
        ]);

        ob_start();
        while ( $posts->have_posts() ) {
            $posts->the_post();
            get_template_part( 'partials/popular-post' );
        }
        wp_reset_postdata();
        $output = ob_get_clean();

        wp_cache_set( $cache_key, $output, 'widget_fragments', HOUR_IN_SECONDS );
    }

    return $output;
}

// Invalidate when posts are updated
add_action( 'save_post', function() {
    wp_cache_delete( 'popular_posts_widget', 'widget_fragments' );
});

// Reusable fragment caching helper
function cached_fragment( $key, $callback, $expiration = 3600, $group = 'fragments' ) {
    $output = wp_cache_get( $key, $group );

    if ( false === $output ) {
        ob_start();
        $callback();
        $output = ob_get_clean();
        wp_cache_set( $key, $output, $group, $expiration );
    }

    return $output;
}

// Usage in templates
echo cached_fragment( 'sidebar_popular', function() {
    get_template_part( 'partials/popular-posts' );
}, HOUR_IN_SECONDS );

// Cache navigation menus
function get_cached_nav_menu( $location, $args = [] ) {
    $cache_key = 'nav_menu_' . $location;
    $menu = wp_cache_get( $cache_key, 'nav_fragments' );

    if ( false === $menu ) {
        $menu = wp_nav_menu( array_merge( $args, [
            'theme_location' => $location,
            'echo'           => false,
        ]));
        wp_cache_set( $cache_key, $menu, 'nav_fragments', DAY_IN_SECONDS );
    }

    return $menu;
}

// Invalidate menu cache when menus change
add_action( 'wp_update_nav_menu', function() {
    wp_cache_delete( 'nav_menu_primary', 'nav_fragments' );
    wp_cache_delete( 'nav_menu_footer', 'nav_fragments' );
});

// User-specific fragment caching
function get_user_dashboard_fragment( $user_id ) {
    $cache_key = 'dashboard_' . $user_id;
    $fragment = wp_cache_get( $cache_key, 'user_fragments' );

    if ( false === $fragment ) {
        ob_start();
        // Render user-specific dashboard
        include 'partials/user-dashboard.php';
        $fragment = ob_get_clean();
        wp_cache_set( $cache_key, $fragment, 'user_fragments', 15 * MINUTE_IN_SECONDS );
    }

    return $fragment;
}
```

Reference: [10up Fragment Caching](https://10up.github.io/Engineering-Best-Practices/php/#caching)

### 2.2 Implement Proper Cache Invalidation

**Impact: HIGH (Prevents stale data without excessive cache clearing)**

*Tags: caching, invalidation, hooks, data-integrity*

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

### 2.3 Leverage Object Cache with Cache Groups

**Impact: CRITICAL (Enables efficient cache invalidation and organization)**

*Tags: caching, object-cache, redis, memcached*

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

### 2.4 Cache Remote HTTP Requests

**Impact: CRITICAL (Eliminates network latency on repeated requests)**

*Tags: caching, http, api, wp_remote_get*

Always cache responses from `wp_remote_get()`, `wp_remote_post()`, and other HTTP API functions. Remote requests add significant latency (100ms-2s+) and can fail, causing page load delays. Cache successful responses and handle failures gracefully.

**Incorrect (uncached remote requests):**

```php
// Every page load makes HTTP request
function display_github_stars() {
    $response = wp_remote_get( 'https://api.github.com/repos/wordpress/wordpress' );
    $data = json_decode( wp_remote_retrieve_body( $response ) );
    return $data->stargazers_count ?? 0;
}

// No timeout set - can hang for 30+ seconds
$response = wp_remote_get( 'https://slow-api.example.com/data' );

// No error handling
function get_remote_data() {
    $response = wp_remote_get( 'https://api.example.com/data' );
    return json_decode( wp_remote_retrieve_body( $response ) );
}
```

**Correct (properly cached with error handling):**

```php
// Cache remote requests with transients
function get_github_stars( $repo ) {
    $cache_key = 'github_stars_' . sanitize_key( $repo );
    $stars = get_transient( $cache_key );

    if ( false !== $stars ) {
        return $stars;
    }

    $response = wp_remote_get(
        "https://api.github.com/repos/{$repo}",
        [
            'timeout' => 10,
            'headers' => [
                'Accept' => 'application/vnd.github.v3+json',
            ],
        ]
    );

    if ( is_wp_error( $response ) ) {
        // Log error and return cached/default value
        error_log( 'GitHub API error: ' . $response->get_error_message() );
        return get_option( "github_stars_{$repo}_fallback", 0 );
    }

    $code = wp_remote_retrieve_response_code( $response );
    if ( 200 !== $code ) {
        error_log( "GitHub API returned status {$code}" );
        return get_option( "github_stars_{$repo}_fallback", 0 );
    }

    $data = json_decode( wp_remote_retrieve_body( $response ) );
    $stars = $data->stargazers_count ?? 0;

    // Cache for 1 hour, store fallback for longer
    set_transient( $cache_key, $stars, HOUR_IN_SECONDS );
    update_option( "github_stars_{$repo}_fallback", $stars );

    return $stars;
}

// Background refresh pattern for critical data
function get_critical_api_data() {
    $cache_key = 'critical_api_data';
    $data = get_transient( $cache_key );

    if ( false !== $data ) {
        // Schedule background refresh if cache is getting stale
        $age = get_transient( $cache_key . '_time' );
        if ( $age && ( time() - $age ) > ( HOUR_IN_SECONDS / 2 ) ) {
            wp_schedule_single_event( time(), 'refresh_critical_api_data' );
        }
        return $data;
    }

    // Synchronous fetch if no cache
    return fetch_and_cache_api_data();
}

add_action( 'refresh_critical_api_data', 'fetch_and_cache_api_data' );

function fetch_and_cache_api_data() {
    $response = wp_remote_get( 'https://api.example.com/critical', ['timeout' => 15] );

    if ( ! is_wp_error( $response ) && 200 === wp_remote_retrieve_response_code( $response ) ) {
        $data = json_decode( wp_remote_retrieve_body( $response ), true );
        set_transient( 'critical_api_data', $data, 2 * HOUR_IN_SECONDS );
        set_transient( 'critical_api_data_time', time(), 2 * HOUR_IN_SECONDS );
        return $data;
    }

    return get_transient( 'critical_api_data' ) ?: [];
}
```

Reference: [WordPress HTTP API](https://developer.wordpress.org/plugins/http-api/)

### 2.5 Use Transients for Expensive External Operations

**Impact: CRITICAL (10-100x reduction in external API calls)**

*Tags: caching, transients, api, performance*

Transients are ideal for caching expensive external operations like API calls, remote requests, and complex computations. They persist across page loads and work with or without a persistent object cache. Never use transients for data that originates from the WordPress database.

**Incorrect (no caching of external calls):**

```php
// Every page load makes an API call
function get_weather_data( $city ) {
    $response = wp_remote_get( "https://api.weather.com/v1/current?city={$city}" );
    return json_decode( wp_remote_retrieve_body( $response ) );
}

// Caching database data in transients is wasteful
function get_recent_posts_cached() {
    $cached = get_transient( 'recent_posts' );
    if ( $cached ) {
        return $cached;
    }
    // This already uses object cache via WP_Query
    $posts = get_posts(['numberposts' => 10]);
    set_transient( 'recent_posts', $posts, HOUR_IN_SECONDS );
    return $posts;
}

// Missing error handling
function get_api_data() {
    $data = get_transient( 'api_data' );
    if ( ! $data ) {
        $response = wp_remote_get( 'https://api.example.com/data' );
        $data = json_decode( wp_remote_retrieve_body( $response ) );
        set_transient( 'api_data', $data, DAY_IN_SECONDS );
    }
    return $data;
}
```

**Correct (proper transient usage):**

```php
// Cache external API calls with appropriate expiration
function get_weather_data( $city ) {
    $cache_key = 'weather_' . sanitize_key( $city );
    $data = get_transient( $cache_key );

    if ( false !== $data ) {
        return $data;
    }

    $response = wp_remote_get(
        "https://api.weather.com/v1/current?city=" . urlencode( $city ),
        ['timeout' => 10]
    );

    if ( is_wp_error( $response ) ) {
        // Return stale data if available, or false
        return false;
    }

    $data = json_decode( wp_remote_retrieve_body( $response ) );

    if ( $data ) {
        set_transient( $cache_key, $data, HOUR_IN_SECONDS );
    }

    return $data;
}

// Use object cache for database-originated data instead
function get_recent_posts_cached() {
    $cache_key = 'recent_posts_query';
    $posts = wp_cache_get( $cache_key, 'my_plugin' );

    if ( false === $posts ) {
        $posts = get_posts(['numberposts' => 10]);
        wp_cache_set( $cache_key, $posts, 'my_plugin', HOUR_IN_SECONDS );
    }

    return $posts;
}

// Handle API errors gracefully with stale-while-revalidate pattern
function get_api_data_robust() {
    $data = get_transient( 'api_data' );
    $last_fetch = get_transient( 'api_data_timestamp' );

    // Return cached data if fresh enough
    if ( false !== $data && $last_fetch && ( time() - $last_fetch ) < HOUR_IN_SECONDS ) {
        return $data;
    }

    // Attempt to refresh
    $response = wp_remote_get( 'https://api.example.com/data', ['timeout' => 5] );

    if ( ! is_wp_error( $response ) && 200 === wp_remote_retrieve_response_code( $response ) ) {
        $new_data = json_decode( wp_remote_retrieve_body( $response ), true );
        if ( $new_data ) {
            set_transient( 'api_data', $new_data, DAY_IN_SECONDS );
            set_transient( 'api_data_timestamp', time(), DAY_IN_SECONDS );
            return $new_data;
        }
    }

    // Return stale data on failure
    return $data ?: [];
}
```

Reference: [WordPress Transients API](https://developer.wordpress.org/apis/transients/)

---

## 3. Asset Management

**Impact Level:** HIGH

How scripts and styles are loaded directly affects page load time and Core Web Vitals. Proper enqueueing, conditional loading, defer/async attributes, and avoiding render-blocking resources are key to frontend performance.

### 3.1 Load Assets Conditionally

**Impact: HIGH (30-50% reduction in unnecessary asset loading)**

*Tags: assets, conditional, performance, optimization*

Only load scripts and styles on pages where they're actually needed. Loading all assets on every page wastes bandwidth and slows down pages. Use WordPress conditional tags to selectively enqueue assets.

**Incorrect (loading everything everywhere):**

```php
// Loads contact form scripts on every page
function enqueue_all_scripts() {
    wp_enqueue_script( 'contact-form', get_template_directory_uri() . '/js/contact.js', [], '1.0', true );
    wp_enqueue_script( 'slider', get_template_directory_uri() . '/js/slider.js', [], '1.0', true );
    wp_enqueue_script( 'gallery', get_template_directory_uri() . '/js/gallery.js', [], '1.0', true );
    wp_enqueue_style( 'gallery-styles', get_template_directory_uri() . '/css/gallery.css' );
}
add_action( 'wp_enqueue_scripts', 'enqueue_all_scripts' );

// Plugin loads admin scripts on all admin pages
function plugin_admin_scripts() {
    wp_enqueue_script( 'my-plugin-admin', plugins_url( 'js/admin.js', __FILE__ ) );
}
add_action( 'admin_enqueue_scripts', 'plugin_admin_scripts' );
```

**Correct (conditional loading):**

```php
function enqueue_conditional_assets() {
    // Contact form only on contact page
    if ( is_page( 'contact' ) || is_page_template( 'contact-template.php' ) ) {
        wp_enqueue_script( 'contact-form', get_template_directory_uri() . '/js/contact.js', [], '1.0', true );
    }

    // Slider only on homepage
    if ( is_front_page() ) {
        wp_enqueue_script( 'slider', get_template_directory_uri() . '/js/slider.js', [], '1.0', true );
    }

    // Gallery only on posts with gallery shortcode or block
    if ( is_singular() ) {
        $post = get_post();
        if ( has_shortcode( $post->post_content, 'gallery' ) || has_block( 'gallery', $post ) ) {
            wp_enqueue_script( 'gallery', get_template_directory_uri() . '/js/gallery.js', [], '1.0', true );
            wp_enqueue_style( 'gallery-styles', get_template_directory_uri() . '/css/gallery.css' );
        }
    }

    // Comments script only when needed
    if ( is_singular() && comments_open() && get_option( 'thread_comments' ) ) {
        wp_enqueue_script( 'comment-reply' );
    }

    // WooCommerce scripts only on shop pages
    if ( function_exists( 'is_woocommerce' ) && is_woocommerce() ) {
        wp_enqueue_script( 'shop-custom', get_template_directory_uri() . '/js/shop.js', [], '1.0', true );
    }
}
add_action( 'wp_enqueue_scripts', 'enqueue_conditional_assets' );

// Admin scripts only on relevant pages
function plugin_admin_scripts( $hook ) {
    // Only on our plugin's settings page
    if ( 'settings_page_my-plugin' !== $hook ) {
        return;
    }

    wp_enqueue_script( 'my-plugin-admin', plugins_url( 'js/admin.js', __FILE__ ), ['jquery'], '1.0', true );
    wp_enqueue_style( 'my-plugin-admin', plugins_url( 'css/admin.css', __FILE__ ), [], '1.0' );
}
add_action( 'admin_enqueue_scripts', 'plugin_admin_scripts' );

// Use post type checks
function cpt_specific_scripts() {
    if ( is_singular( 'product' ) ) {
        wp_enqueue_script( 'product-viewer' );
    }

    if ( is_post_type_archive( 'event' ) || is_singular( 'event' ) ) {
        wp_enqueue_script( 'calendar' );
        wp_enqueue_style( 'calendar-styles' );
    }
}
add_action( 'wp_enqueue_scripts', 'cpt_specific_scripts' );
```

Reference: [WordPress Conditional Tags](https://developer.wordpress.org/themes/basics/conditional-tags/)

### 3.2 Use Defer and Async for Non-Critical Scripts

**Impact: HIGH (Improves LCP and reduces render-blocking time)**

*Tags: assets, defer, async, core-web-vitals*

Add `defer` or `async` attributes to non-critical scripts to prevent them from blocking page rendering. Since WordPress 6.3, use the `strategy` parameter in `wp_register_script()` and `wp_enqueue_script()` for clean defer/async support.

**Incorrect (render-blocking scripts):**

```php
// All scripts block rendering by default
wp_enqueue_script( 'analytics', 'https://example.com/analytics.js', [], '1.0', false );
wp_enqueue_script( 'chat-widget', 'https://example.com/chat.js', [], '1.0', false );

// Old hack using script_loader_tag filter (fragile)
add_filter( 'script_loader_tag', function( $tag, $handle ) {
    if ( 'my-script' === $handle ) {
        return str_replace( ' src', ' defer src', $tag );
    }
    return $tag;
}, 10, 2 );
```

**Correct (using defer/async strategies):**

```php
// WordPress 6.3+ native defer/async support
function enqueue_optimized_scripts() {
    // Defer non-critical scripts (executes after HTML parsing, maintains order)
    wp_enqueue_script(
        'analytics',
        'https://example.com/analytics.js',
        [],
        '1.0',
        [
            'strategy'  => 'defer',
            'in_footer' => true,
        ]
    );

    // Async for independent scripts (executes as soon as loaded)
    wp_enqueue_script(
        'chat-widget',
        'https://example.com/chat.js',
        [],
        '1.0',
        [
            'strategy'  => 'async',
            'in_footer' => true,
        ]
    );

    // Regular script that needs to run immediately
    wp_enqueue_script(
        'critical-above-fold',
        get_template_directory_uri() . '/js/critical.js',
        [],
        '1.0',
        false // Load in head, no defer
    );

    // Deferred script with dependencies
    wp_enqueue_script(
        'theme-main',
        get_template_directory_uri() . '/js/main.js',
        ['jquery'],
        '1.0',
        [
            'strategy'  => 'defer',
            'in_footer' => true,
        ]
    );
}
add_action( 'wp_enqueue_scripts', 'enqueue_optimized_scripts' );

// For WordPress < 6.3, use filter approach
function add_defer_attribute( $tag, $handle, $src ) {
    $defer_scripts = ['analytics', 'chat-widget', 'social-share'];

    if ( in_array( $handle, $defer_scripts, true ) ) {
        return '<script src="' . esc_url( $src ) . '" defer></script>' . "\n";
    }

    $async_scripts = ['beacon', 'pixel'];

    if ( in_array( $handle, $async_scripts, true ) ) {
        return '<script src="' . esc_url( $src ) . '" async></script>' . "\n";
    }

    return $tag;
}
add_filter( 'script_loader_tag', 'add_defer_attribute', 10, 3 );

// Defer third-party scripts
function defer_third_party_scripts( $tag, $handle, $src ) {
    // Defer all external scripts by default
    if ( strpos( $src, home_url() ) === false && strpos( $tag, 'defer' ) === false ) {
        return str_replace( '<script ', '<script defer ', $tag );
    }
    return $tag;
}
add_filter( 'script_loader_tag', 'defer_third_party_scripts', 10, 3 );
```

Use `defer` for scripts that depend on DOM or other scripts. Use `async` only for independent scripts like analytics that don't depend on anything.

Reference: [WordPress Script Loading Strategies](https://developer.wordpress.org/reference/functions/wp_enqueue_script/#script-loading-strategies)

### 3.3 Dequeue Unused Plugin Assets

**Impact: MEDIUM-HIGH (Removes unnecessary HTTP requests and reduces page weight)**

*Tags: assets, plugins, optimization, dequeue*

Many plugins load their assets on every page, even when not needed. Identify and dequeue unused plugin scripts and styles on pages where they're not required. This reduces HTTP requests and page weight.

**Incorrect (allowing all plugin assets to load everywhere):**

```php
// Not managing plugin assets at all - they load on every page

// Or using a blanket approach that breaks functionality
function remove_all_plugin_styles() {
    global $wp_styles;
    foreach ( $wp_styles->registered as $handle => $style ) {
        if ( strpos( $style->src, 'plugins/' ) !== false ) {
            wp_dequeue_style( $handle ); // Dangerous - may break things
        }
    }
}
```

**Correct (selective dequeuing based on page context):**

```php
function optimize_plugin_assets() {
    // Remove Contact Form 7 assets except on contact page
    if ( ! is_page( 'contact' ) && ! is_page_template( 'contact-template.php' ) ) {
        wp_dequeue_style( 'contact-form-7' );
        wp_dequeue_script( 'contact-form-7' );
    }

    // Remove WooCommerce assets on non-shop pages
    if ( function_exists( 'is_woocommerce' ) ) {
        if ( ! is_woocommerce() && ! is_cart() && ! is_checkout() && ! is_account_page() ) {
            wp_dequeue_style( 'woocommerce-general' );
            wp_dequeue_style( 'woocommerce-layout' );
            wp_dequeue_style( 'woocommerce-smallscreen' );
            wp_dequeue_script( 'wc-cart-fragments' );
            wp_dequeue_script( 'woocommerce' );
        }
    }

    // Remove block library CSS if not using blocks
    if ( ! has_blocks() ) {
        wp_dequeue_style( 'wp-block-library' );
        wp_dequeue_style( 'wp-block-library-theme' );
        wp_dequeue_style( 'wc-blocks-style' );
    }

    // Remove Elementor assets on non-Elementor pages
    if ( ! is_singular() || ! \Elementor\Plugin::$instance->documents->get( get_the_ID() )->is_built_with_elementor() ) {
        wp_dequeue_style( 'elementor-frontend' );
        wp_dequeue_style( 'elementor-icons' );
    }

    // Remove dashicons for non-logged-in users
    if ( ! is_user_logged_in() ) {
        wp_dequeue_style( 'dashicons' );
    }

    // Remove emoji scripts if not needed
    remove_action( 'wp_head', 'print_emoji_detection_script', 7 );
    remove_action( 'wp_print_styles', 'print_emoji_styles' );
}
add_action( 'wp_enqueue_scripts', 'optimize_plugin_assets', 100 );

// Identify what's loading - development helper
function debug_enqueued_assets() {
    if ( ! current_user_can( 'manage_options' ) || ! isset( $_GET['debug_assets'] ) ) {
        return;
    }

    global $wp_scripts, $wp_styles;

    echo '<!-- Enqueued Scripts: ';
    foreach ( $wp_scripts->queue as $handle ) {
        echo $handle . ', ';
    }
    echo ' -->';

    echo '<!-- Enqueued Styles: ';
    foreach ( $wp_styles->queue as $handle ) {
        echo $handle . ', ';
    }
    echo ' -->';
}
add_action( 'wp_footer', 'debug_enqueued_assets' );

// Dequeue jQuery migrate if not needed (careful - test thoroughly)
function remove_jquery_migrate( $scripts ) {
    if ( ! is_admin() && isset( $scripts->registered['jquery'] ) ) {
        $script = $scripts->registered['jquery'];
        if ( $script->deps ) {
            $script->deps = array_diff( $script->deps, ['jquery-migrate'] );
        }
    }
}
add_action( 'wp_default_scripts', 'remove_jquery_migrate' );
```

Always test thoroughly after dequeuing plugin assets to ensure functionality isn't broken.

Reference: [wp_dequeue_script](https://developer.wordpress.org/reference/functions/wp_dequeue_script/)

### 3.4 Minify and Combine Assets Appropriately

**Impact: MEDIUM (20-40% reduction in asset file sizes)**

*Tags: assets, minification, optimization, http2*

Minify CSS and JavaScript files to reduce file sizes. With HTTP/2, combining files is less critical than before, but minification remains important. Use build tools for development and consider caching plugins for production.

**Incorrect (unminified production assets):**

```php
// Loading development/unminified versions in production
wp_enqueue_script( 'theme-main', get_template_directory_uri() . '/js/main.js' );
wp_enqueue_style( 'theme-style', get_template_directory_uri() . '/css/style.css' );

// Manually combining scripts incorrectly
function combine_scripts() {
    $combined = '';
    $combined .= file_get_contents( get_template_directory() . '/js/file1.js' );
    $combined .= file_get_contents( get_template_directory() . '/js/file2.js' );
    echo '<script>' . $combined . '</script>'; // Security risk, no caching
}
```

**Correct (environment-aware asset loading):**

```php
// Load minified in production, source in development
function enqueue_theme_assets() {
    $suffix = defined( 'SCRIPT_DEBUG' ) && SCRIPT_DEBUG ? '' : '.min';
    $version = wp_get_theme()->get( 'Version' );

    wp_enqueue_style(
        'theme-style',
        get_template_directory_uri() . "/css/style{$suffix}.css",
        [],
        $version
    );

    wp_enqueue_script(
        'theme-main',
        get_template_directory_uri() . "/js/main{$suffix}.js",
        ['jquery'],
        $version,
        true
    );
}
add_action( 'wp_enqueue_scripts', 'enqueue_theme_assets' );

// Use build tools (example package.json scripts)
/*
{
    "scripts": {
        "build:css": "sass src/scss:dist/css && postcss dist/css/*.css --use autoprefixer cssnano -d dist/css",
        "build:js": "esbuild src/js/main.js --bundle --minify --outfile=dist/js/main.min.js",
        "build": "npm run build:css && npm run build:js",
        "watch": "npm run build -- --watch"
    }
}
*/

// Critical CSS inline for above-the-fold content
function inline_critical_css() {
    $critical_css_file = get_template_directory() . '/css/critical.css';

    if ( file_exists( $critical_css_file ) ) {
        $critical_css = file_get_contents( $critical_css_file );
        echo '<style id="critical-css">' . $critical_css . '</style>';
    }
}
add_action( 'wp_head', 'inline_critical_css', 1 );

// Defer non-critical CSS
function defer_non_critical_css() {
    ?>
    <link rel="preload" href="<?php echo esc_url( get_template_directory_uri() . '/css/style.min.css' ); ?>" as="style" onload="this.onload=null;this.rel='stylesheet'">
    <noscript><link rel="stylesheet" href="<?php echo esc_url( get_template_directory_uri() . '/css/style.min.css' ); ?>"></noscript>
    <?php
}
add_action( 'wp_head', 'defer_non_critical_css', 2 );

// Add resource hints for external resources
function add_resource_hints() {
    // Preconnect to external domains
    echo '<link rel="preconnect" href="https://fonts.googleapis.com">';
    echo '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>';

    // DNS prefetch for analytics
    echo '<link rel="dns-prefetch" href="https://www.google-analytics.com">';
}
add_action( 'wp_head', 'add_resource_hints', 1 );
```

Consider using caching plugins (WP Rocket, W3 Total Cache) for automatic minification and combination in production environments.

Reference: [Resource Hints](https://developer.wordpress.org/reference/functions/wp_resource_hints/)

### 3.5 Use Proper Script and Style Enqueueing

**Impact: HIGH (Enables dependency management and prevents conflicts)**

*Tags: assets, scripts, styles, enqueue*

Always use `wp_enqueue_script()` and `wp_enqueue_style()` to load assets. Never hardcode script or link tags in templates. Proper enqueueing enables dependency management, versioning, conditional loading, and prevents duplicate asset loading.

**Incorrect (hardcoded assets):**

```php
// Don't hardcode in header.php or templates
<script src="<?php echo get_template_directory_uri(); ?>/js/custom.js"></script>
<link rel="stylesheet" href="<?php echo get_template_directory_uri(); ?>/css/custom.css">

// Don't echo script tags in functions
function add_my_scripts() {
    echo '<script src="https://example.com/script.js"></script>';
}
add_action( 'wp_head', 'add_my_scripts' );

// Don't use wp_head for inline scripts that should be enqueued
add_action( 'wp_head', function() {
    ?>
    <script>
        var myConfig = { api: '<?php echo esc_js( $api_url ); ?>' };
    </script>
    <?php
});
```

**Correct (proper enqueueing):**

```php
// Enqueue scripts and styles properly
function theme_enqueue_assets() {
    // Enqueue styles
    wp_enqueue_style(
        'theme-main',
        get_template_directory_uri() . '/css/main.css',
        [], // dependencies
        wp_get_theme()->get( 'Version' )
    );

    // Enqueue scripts with dependencies
    wp_enqueue_script(
        'theme-main',
        get_template_directory_uri() . '/js/main.js',
        ['jquery'], // dependencies
        wp_get_theme()->get( 'Version' ),
        true // in footer
    );

    // Pass data to scripts using wp_localize_script or wp_add_inline_script
    wp_localize_script( 'theme-main', 'themeConfig', [
        'ajaxUrl' => admin_url( 'admin-ajax.php' ),
        'nonce'   => wp_create_nonce( 'theme_nonce' ),
        'apiUrl'  => esc_url( $api_url ),
    ]);

    // Or use wp_add_inline_script for more control
    wp_add_inline_script(
        'theme-main',
        'const THEME_VERSION = ' . wp_json_encode( wp_get_theme()->get( 'Version' ) ) . ';',
        'before'
    );
}
add_action( 'wp_enqueue_scripts', 'theme_enqueue_assets' );

// For admin scripts
function admin_enqueue_assets( $hook ) {
    // Only load on specific admin pages
    if ( 'edit.php' !== $hook ) {
        return;
    }

    wp_enqueue_script(
        'admin-custom',
        get_template_directory_uri() . '/js/admin.js',
        ['jquery'],
        '1.0.0',
        true
    );
}
add_action( 'admin_enqueue_scripts', 'admin_enqueue_assets' );

// For login page
add_action( 'login_enqueue_scripts', function() {
    wp_enqueue_style( 'custom-login', get_template_directory_uri() . '/css/login.css' );
});
```

Reference: [wp_enqueue_script](https://developer.wordpress.org/reference/functions/wp_enqueue_script/)

---

## 4. Theme Performance

**Impact Level:** HIGH

Theme code executes on every page load. Avoiding queries in templates, using proper template hierarchy, optimizing loops, and following WordPress template best practices prevent performance degradation at the presentation layer.

### 4.1 Avoid Database Queries in Templates

**Impact: HIGH (Prevents N+1 queries and template-level bottlenecks)**

*Tags: theme, templates, queries, performance*

Keep database queries out of template files. Templates should only display data, not fetch it. Move queries to functions.php, controllers, or use pre_get_posts to modify the main query. This improves maintainability and prevents accidental performance issues.

**Incorrect (queries scattered in templates):**

```php
// In single.php - additional queries in template
<?php get_header(); ?>

<?php
// Bad: Query in template
$related = new WP_Query([
    'post_type'      => 'post',
    'posts_per_page' => 4,
    'post__not_in'   => [get_the_ID()],
    'category__in'   => wp_get_post_categories( get_the_ID() ),
]);
?>

<article>
    <?php the_content(); ?>

    <?php
    // Bad: Another query in template
    $author_posts = get_posts([
        'author'      => get_the_author_meta( 'ID' ),
        'numberposts' => 5,
        'exclude'     => get_the_ID(),
    ]);
    ?>

    <div class="author-posts">
        <?php foreach ( $author_posts as $post ) : setup_postdata( $post ); ?>
            <!-- render post -->
        <?php endforeach; wp_reset_postdata(); ?>
    </div>
</article>

// In archive.php - querying inside the loop
<?php while ( have_posts() ) : the_post(); ?>
    <article>
        <?php the_title(); ?>
        <?php
        // Bad: Query inside loop = N+1 problem
        $attachments = get_posts([
            'post_type'   => 'attachment',
            'post_parent' => get_the_ID(),
        ]);
        ?>
    </article>
<?php endwhile; ?>
```

**Correct (queries in functions, data passed to templates):**

```php
// In functions.php or a controller class
function get_related_posts( $post_id, $count = 4 ) {
    $cache_key = "related_posts_{$post_id}";
    $related = wp_cache_get( $cache_key, 'theme_queries' );

    if ( false === $related ) {
        $categories = wp_get_post_categories( $post_id, ['fields' => 'ids'] );

        $related = get_posts([
            'post_type'      => 'post',
            'posts_per_page' => $count,
            'exclude'        => $post_id,
            'category__in'   => $categories,
            'fields'         => 'ids',
        ]);

        wp_cache_set( $cache_key, $related, 'theme_queries', HOUR_IN_SECONDS );
    }

    return $related;
}

function get_author_posts( $author_id, $exclude_id = 0 ) {
    return get_posts([
        'author'      => $author_id,
        'numberposts' => 5,
        'exclude'     => $exclude_id,
        'fields'      => 'ids',
    ]);
}

// In single.php - clean template
<?php
get_header();

// Get data at the top of template
$related_ids = get_related_posts( get_the_ID() );
$author_post_ids = get_author_posts( get_the_author_meta( 'ID' ), get_the_ID() );
?>

<article>
    <?php the_content(); ?>

    <?php if ( $related_ids ) : ?>
        <div class="related-posts">
            <?php foreach ( $related_ids as $post_id ) : ?>
                <?php get_template_part( 'partials/post-card', null, ['post_id' => $post_id] ); ?>
            <?php endforeach; ?>
        </div>
    <?php endif; ?>
</article>

// Use pre_get_posts for main query modifications
add_action( 'pre_get_posts', function( $query ) {
    if ( ! is_admin() && $query->is_main_query() ) {
        if ( $query->is_home() ) {
            $query->set( 'posts_per_page', 12 );
            $query->set( 'ignore_sticky_posts', true );
        }
    }
});
```

Reference: [Template Hierarchy](https://developer.wordpress.org/themes/basics/template-hierarchy/)

### 4.2 Place Hooks at Appropriate Priority Levels

**Impact: MEDIUM (Ensures proper execution order and avoids conflicts)**

*Tags: theme, hooks, actions, filters*

Use appropriate priority levels when adding actions and filters. Lower numbers run first. Understanding hook priority prevents conflicts with plugins and ensures your code runs at the right time.

**Incorrect (ignoring priority or using arbitrary values):**

```php
// All at default priority - order is unpredictable
add_action( 'wp_enqueue_scripts', 'theme_styles' );
add_action( 'wp_enqueue_scripts', 'theme_scripts' );
add_action( 'wp_enqueue_scripts', 'override_plugin_styles' );

// Random priority values
add_filter( 'the_content', 'add_social_buttons', 999999 );

// Trying to run before everything with very low number
add_action( 'init', 'my_early_init', -99999 );
```

**Correct (intentional, documented priorities):**

```php
// Standard priority levels:
// 1-9:    Very early, before most things
// 10:     Default, normal execution
// 11-19:  After defaults, modifications
// 20+:    Late execution, overrides
// 100+:   Very late, final modifications

// Load base styles first, then customizations
add_action( 'wp_enqueue_scripts', 'theme_base_styles', 10 );
add_action( 'wp_enqueue_scripts', 'theme_component_styles', 15 );
add_action( 'wp_enqueue_scripts', 'theme_override_plugin_styles', 20 );

// Dequeue plugin assets after they're enqueued
add_action( 'wp_enqueue_scripts', 'dequeue_unnecessary_assets', 100 );

// Filter content modifications in logical order
add_filter( 'the_content', 'process_shortcodes', 10 );     // Default
add_filter( 'the_content', 'add_related_posts', 15 );      // After shortcodes
add_filter( 'the_content', 'add_social_buttons', 20 );     // After related posts
add_filter( 'the_content', 'wrap_content_sections', 25 );  // Final wrapping

// Document why you're using non-default priorities
/**
 * Override plugin's body classes.
 * Priority 20 ensures this runs after the plugin's filter at default priority.
 */
add_filter( 'body_class', 'override_plugin_body_class', 20 );

// Use early priority for setup tasks
add_action( 'init', 'register_custom_post_types', 5 );  // Before anything uses them
add_action( 'init', 'register_taxonomies', 5 );

// Default priority for normal functionality
add_action( 'init', 'setup_theme_features', 10 );

// Late priority for modifications that depend on other init hooks
add_action( 'init', 'modify_registered_post_types', 15 );

// WordPress standard hook priorities
add_action( 'after_setup_theme', 'theme_setup', 10 );  // Standard
add_action( 'widgets_init', 'register_sidebars', 10 ); // Standard

// Remove then re-add with different priority
remove_action( 'woocommerce_before_main_content', 'woocommerce_output_content_wrapper', 10 );
add_action( 'woocommerce_before_main_content', 'theme_content_wrapper', 10 );

// Helper for consistent priority management
class Theme_Hooks {
    const EARLY    = 5;
    const DEFAULT  = 10;
    const LATE     = 15;
    const OVERRIDE = 20;
    const FINAL    = 100;
}

add_action( 'init', 'register_cpts', Theme_Hooks::EARLY );
add_action( 'init', 'setup_features', Theme_Hooks::DEFAULT );
add_filter( 'the_content', 'final_content_filter', Theme_Hooks::FINAL );
```

Reference: [Plugin API - Actions](https://developer.wordpress.org/plugins/hooks/actions/)

### 4.3 Optimize WordPress Loops

**Impact: MEDIUM-HIGH (Prevents memory issues and N+1 query patterns)**

*Tags: theme, loops, wp_query, optimization*

Optimize loops to prevent N+1 queries and memory issues. Use `update_post_meta_cache` and `update_post_term_cache` parameters, reset post data properly, and avoid expensive operations inside loops.

**Incorrect (unoptimized loops):**

```php
// N+1 queries - each iteration queries meta and terms
<?php while ( have_posts() ) : the_post(); ?>
    <article>
        <?php the_title(); ?>
        <?php echo get_post_meta( get_the_ID(), 'custom_field', true ); // Query each iteration ?>
        <?php the_category(); // Query each iteration ?>
        <?php the_tags(); // Query each iteration ?>
    </article>
<?php endwhile; ?>

// Not resetting post data
$custom_query = new WP_Query(['post_type' => 'product']);
while ( $custom_query->have_posts() ) {
    $custom_query->the_post();
    // ...
}
// Missing wp_reset_postdata() - corrupts global $post

// Expensive operations inside loop
while ( have_posts() ) {
    the_post();
    // Bad: complex query inside loop
    $related = new WP_Query([
        'post_type' => 'post',
        'meta_query' => [/* complex meta query */],
    ]);
}
```

**Correct (optimized loops):**

```php
// Enable meta and term caching - single query loads all at once
$query = new WP_Query([
    'post_type'              => 'post',
    'posts_per_page'         => 20,
    'update_post_meta_cache' => true,  // Prime meta cache (default true)
    'update_post_term_cache' => true,  // Prime term cache (default true)
]);

while ( $query->have_posts() ) {
    $query->the_post();
    // Meta and terms are now cached - no additional queries
    the_title();
    echo get_post_meta( get_the_ID(), 'custom_field', true );
    the_category();
}
wp_reset_postdata(); // Always reset!

// Disable caching when not needed (saves memory for large batches)
$ids_only = new WP_Query([
    'post_type'              => 'post',
    'posts_per_page'         => 1000,
    'fields'                 => 'ids',
    'update_post_meta_cache' => false, // Don't need meta
    'update_post_term_cache' => false, // Don't need terms
]);

// Pre-fetch data before loop for complex requirements
$post_ids = wp_list_pluck( $query->posts, 'ID' );

// Batch fetch all custom meta at once
$custom_fields = [];
foreach ( $post_ids as $id ) {
    $custom_fields[ $id ] = get_post_meta( $id, 'custom_field', true );
}

// Batch fetch related data
$related_data = get_related_data_for_posts( $post_ids );

// Now loop with pre-fetched data
foreach ( $query->posts as $post ) {
    setup_postdata( $post );
    ?>
    <article>
        <?php the_title(); ?>
        <?php echo esc_html( $custom_fields[ $post->ID ] ?? '' ); ?>
        <?php
        if ( isset( $related_data[ $post->ID ] ) ) {
            // Use pre-fetched data
        }
        ?>
    </article>
    <?php
}
wp_reset_postdata();

// Use foreach with setup_postdata for cleaner code
foreach ( $query->posts as $post ) {
    setup_postdata( $post );
    get_template_part( 'partials/post-card' );
}
wp_reset_postdata();

// For simple ID operations, skip setup_postdata entirely
$post_ids = get_posts([
    'post_type'   => 'post',
    'numberposts' => 100,
    'fields'      => 'ids',
]);

foreach ( $post_ids as $post_id ) {
    // Direct function calls are fine for IDs
    update_post_meta( $post_id, 'processed', true );
}
```

Reference: [WP_Query](https://developer.wordpress.org/reference/classes/wp_query/)

### 4.4 Use Template Parts Efficiently

**Impact: HIGH (Reduces code duplication and improves maintainability)**

*Tags: theme, templates, partials, organization*

Use `get_template_part()` to create reusable template components. Pass data using the third parameter (WordPress 5.5+) instead of relying on global variables. This creates cleaner, more maintainable, and cacheable template code.

**Incorrect (duplicated code, global variable reliance):**

```php
// Duplicated markup across templates
// In archive.php
<?php while ( have_posts() ) : the_post(); ?>
    <article class="post-card">
        <h2><a href="<?php the_permalink(); ?>"><?php the_title(); ?></a></h2>
        <div class="excerpt"><?php the_excerpt(); ?></div>
        <span class="date"><?php echo get_the_date(); ?></span>
    </article>
<?php endwhile; ?>

// Same markup repeated in search.php, category.php, etc.

// Using globals to pass data
// In template
global $custom_data;
$custom_data = ['show_date' => true];
get_template_part( 'partials/post-card' );

// In partials/post-card.php
global $custom_data;
$show_date = $custom_data['show_date'] ?? false;
```

**Correct (reusable template parts with passed data):**

```php
// partials/post-card.php - reusable component
<?php
/**
 * Post Card Template Part
 *
 * @param array $args {
 *     @type int    $post_id   Post ID (required)
 *     @type bool   $show_date Whether to show date
 *     @type string $size      Card size: 'small', 'medium', 'large'
 * }
 */

$post_id = $args['post_id'] ?? get_the_ID();
$show_date = $args['show_date'] ?? true;
$size = $args['size'] ?? 'medium';

$post = get_post( $post_id );
if ( ! $post ) {
    return;
}
?>

<article class="post-card post-card--<?php echo esc_attr( $size ); ?>">
    <?php if ( has_post_thumbnail( $post_id ) ) : ?>
        <div class="post-card__image">
            <?php echo get_the_post_thumbnail( $post_id, 'medium' ); ?>
        </div>
    <?php endif; ?>

    <div class="post-card__content">
        <h2 class="post-card__title">
            <a href="<?php echo esc_url( get_permalink( $post_id ) ); ?>">
                <?php echo esc_html( get_the_title( $post_id ) ); ?>
            </a>
        </h2>

        <?php if ( $show_date ) : ?>
            <time class="post-card__date" datetime="<?php echo esc_attr( get_the_date( 'c', $post_id ) ); ?>">
                <?php echo esc_html( get_the_date( '', $post_id ) ); ?>
            </time>
        <?php endif; ?>
    </div>
</article>

// In archive.php - clean loop
<?php while ( have_posts() ) : the_post(); ?>
    <?php
    get_template_part( 'partials/post-card', null, [
        'post_id'   => get_the_ID(),
        'show_date' => true,
        'size'      => 'medium',
    ]);
    ?>
<?php endwhile; ?>

// In front-page.php - different configuration
<?php foreach ( $featured_ids as $post_id ) : ?>
    <?php
    get_template_part( 'partials/post-card', null, [
        'post_id'   => $post_id,
        'show_date' => false,
        'size'      => 'large',
    ]);
    ?>
<?php endforeach; ?>

// Use named variations for different contexts
// partials/post-card-minimal.php for search results
get_template_part( 'partials/post-card', 'minimal', ['post_id' => get_the_ID()] );

// partials/post-card-featured.php for featured posts
get_template_part( 'partials/post-card', 'featured', ['post_id' => get_the_ID()] );
```

Reference: [get_template_part](https://developer.wordpress.org/reference/functions/get_template_part/)

---

## 5. Plugin Architecture

**Impact Level:** MEDIUM-HIGH

Well-architected plugins load efficiently and don't impact performance when not needed. Proper hook usage, conditional loading, autoloading, and following WordPress plugin standards ensure plugins scale with site growth.

### 5.1 Use Activation and Deactivation Hooks Properly

**Impact: MEDIUM (Prevents unnecessary setup on every page load)**

*Tags: plugin, activation, hooks, setup*

Use activation hooks for one-time setup tasks like creating database tables, setting default options, and scheduling cron jobs. Don't perform these tasks on every page load. Use deactivation hooks to clean up scheduled events.

**Incorrect (setup on every load):**

```php
// Runs on every request - wasteful
function my_plugin_init() {
    global $wpdb;

    // Bad: checking/creating table on every load
    $table_name = $wpdb->prefix . 'my_plugin_data';
    $wpdb->query( "CREATE TABLE IF NOT EXISTS $table_name ..." );

    // Bad: setting options on every load
    if ( ! get_option( 'my_plugin_version' ) ) {
        update_option( 'my_plugin_version', '1.0.0' );
        update_option( 'my_plugin_settings', ['default' => 'value'] );
    }

    // Bad: scheduling cron on every load
    if ( ! wp_next_scheduled( 'my_plugin_cron' ) ) {
        wp_schedule_event( time(), 'hourly', 'my_plugin_cron' );
    }
}
add_action( 'init', 'my_plugin_init' );
```

**Correct (activation/deactivation hooks):**

```php
// Activation hook - runs once when plugin is activated
register_activation_hook( __FILE__, 'my_plugin_activate' );

function my_plugin_activate() {
    // Create database tables
    my_plugin_create_tables();

    // Set default options
    my_plugin_set_defaults();

    // Schedule cron events
    my_plugin_schedule_events();

    // Flush rewrite rules if plugin adds custom post types/taxonomies
    flush_rewrite_rules();

    // Store version for upgrade routines
    update_option( 'my_plugin_version', MY_PLUGIN_VERSION );
}

function my_plugin_create_tables() {
    global $wpdb;
    $charset_collate = $wpdb->get_charset_collate();

    $table_name = $wpdb->prefix . 'my_plugin_data';

    $sql = "CREATE TABLE $table_name (
        id bigint(20) unsigned NOT NULL AUTO_INCREMENT,
        user_id bigint(20) unsigned NOT NULL,
        data longtext NOT NULL,
        created_at datetime DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY  (id),
        KEY user_id (user_id)
    ) $charset_collate;";

    require_once ABSPATH . 'wp-admin/includes/upgrade.php';
    dbDelta( $sql );
}

function my_plugin_set_defaults() {
    $defaults = [
        'enabled'     => true,
        'cache_time'  => 3600,
        'max_items'   => 100,
    ];

    // Only set if not already set (preserves user settings on reactivation)
    if ( false === get_option( 'my_plugin_settings' ) ) {
        add_option( 'my_plugin_settings', $defaults );
    }
}

function my_plugin_schedule_events() {
    if ( ! wp_next_scheduled( 'my_plugin_daily_cleanup' ) ) {
        wp_schedule_event( time(), 'daily', 'my_plugin_daily_cleanup' );
    }
}

// Deactivation hook - cleanup
register_deactivation_hook( __FILE__, 'my_plugin_deactivate' );

function my_plugin_deactivate() {
    // Clear scheduled events
    wp_clear_scheduled_hook( 'my_plugin_daily_cleanup' );

    // Flush rewrite rules
    flush_rewrite_rules();

    // Optionally clear transients
    delete_transient( 'my_plugin_cache' );
}

// Uninstall hook - complete cleanup (use uninstall.php for better practice)
register_uninstall_hook( __FILE__, 'my_plugin_uninstall' );

function my_plugin_uninstall() {
    global $wpdb;

    // Delete options
    delete_option( 'my_plugin_settings' );
    delete_option( 'my_plugin_version' );

    // Delete custom tables
    $wpdb->query( "DROP TABLE IF EXISTS {$wpdb->prefix}my_plugin_data" );

    // Delete user meta
    $wpdb->query( "DELETE FROM {$wpdb->usermeta} WHERE meta_key LIKE 'my_plugin_%'" );
}

// Version-based upgrade routine
function my_plugin_maybe_upgrade() {
    $current = get_option( 'my_plugin_version', '0' );

    if ( version_compare( $current, MY_PLUGIN_VERSION, '<' ) ) {
        my_plugin_upgrade( $current );
        update_option( 'my_plugin_version', MY_PLUGIN_VERSION );
    }
}
add_action( 'plugins_loaded', 'my_plugin_maybe_upgrade' );
```

Reference: [Plugin Activation Hooks](https://developer.wordpress.org/plugins/plugin-basics/activation-deactivation-hooks/)

### 5.2 Use Autoloading for Plugin Classes

**Impact: MEDIUM-HIGH (Loads only required classes, reduces memory footprint)**

*Tags: plugin, autoloading, classes, composer*

Use PHP autoloading instead of manually requiring files. Autoloading ensures classes are only loaded when actually used, reducing memory consumption and improving performance. Use Composer's autoloader or implement PSR-4 compatible autoloading.

**Incorrect (manual requires):**

```php
// Every class loaded regardless of whether it's used
require_once plugin_dir_path( __FILE__ ) . 'includes/class-post-handler.php';
require_once plugin_dir_path( __FILE__ ) . 'includes/class-user-handler.php';
require_once plugin_dir_path( __FILE__ ) . 'includes/class-comment-handler.php';
require_once plugin_dir_path( __FILE__ ) . 'includes/class-media-handler.php';
require_once plugin_dir_path( __FILE__ ) . 'includes/class-settings.php';
require_once plugin_dir_path( __FILE__ ) . 'includes/class-api.php';
require_once plugin_dir_path( __FILE__ ) . 'includes/class-export.php';
require_once plugin_dir_path( __FILE__ ) . 'includes/class-import.php';
// ... 20 more files

// Class check before use still loads the file
if ( class_exists( 'My_Export_Handler' ) ) {
    // Already loaded above
}
```

**Correct (PSR-4 autoloading with Composer):**

```php
// composer.json
{
    "name": "vendor/my-plugin",
    "autoload": {
        "psr-4": {
            "MyPlugin\\": "src/"
        }
    },
    "autoload-dev": {
        "psr-4": {
            "MyPlugin\\Tests\\": "tests/"
        }
    }
}

// Directory structure:
// my-plugin/
// ├── src/
// │   ├── Admin/
// │   │   ├── Settings.php
// │   │   └── Menu.php
// │   ├── Frontend/
// │   │   └── Display.php
// │   ├── Handlers/
// │   │   ├── PostHandler.php
// │   │   └── UserHandler.php
// │   └── Plugin.php
// ├── vendor/
// ├── composer.json
// └── my-plugin.php

// my-plugin.php
<?php
/**
 * Plugin Name: My Plugin
 */

defined( 'ABSPATH' ) || exit;

// Load Composer autoloader
if ( file_exists( __DIR__ . '/vendor/autoload.php' ) ) {
    require_once __DIR__ . '/vendor/autoload.php';
}

// Initialize plugin
function my_plugin_init() {
    return \MyPlugin\Plugin::instance();
}
add_action( 'plugins_loaded', 'my_plugin_init' );

// src/Plugin.php
namespace MyPlugin;

class Plugin {
    private static $instance = null;

    public static function instance() {
        if ( null === self::$instance ) {
            self::$instance = new self();
        }
        return self::$instance;
    }

    private function __construct() {
        $this->init_hooks();
    }

    private function init_hooks() {
        // Classes are autoloaded only when instantiated
        if ( is_admin() ) {
            new Admin\Settings();
            new Admin\Menu();
        }

        // Only loaded if this code path is reached
        add_action( 'save_post', function( $post_id ) {
            $handler = new Handlers\PostHandler();
            $handler->process( $post_id );
        });
    }
}

// Without Composer - custom autoloader
spl_autoload_register( function( $class ) {
    $namespace = 'MyPlugin\\';

    if ( strpos( $class, $namespace ) !== 0 ) {
        return;
    }

    $relative = substr( $class, strlen( $namespace ) );
    $path = plugin_dir_path( __FILE__ ) . 'src/' . str_replace( '\\', '/', $relative ) . '.php';

    if ( file_exists( $path ) ) {
        require_once $path;
    }
});
```

Reference: [PSR-4 Autoloading](https://www.php-fig.org/psr/psr-4/)

### 5.3 Load Plugin Code Conditionally

**Impact: MEDIUM-HIGH (Reduces memory usage and execution time on irrelevant requests)**

*Tags: plugin, conditional, loading, performance*

Don't load all plugin code on every request. Use conditional checks to only load code when it's actually needed. Frontend code shouldn't load in admin, admin code shouldn't load on frontend, and feature-specific code should only load when that feature is used.

**Incorrect (loading everything everywhere):**

```php
// main-plugin.php - loads everything on every request
require_once plugin_dir_path( __FILE__ ) . 'includes/class-admin.php';
require_once plugin_dir_path( __FILE__ ) . 'includes/class-frontend.php';
require_once plugin_dir_path( __FILE__ ) . 'includes/class-api.php';
require_once plugin_dir_path( __FILE__ ) . 'includes/class-widgets.php';
require_once plugin_dir_path( __FILE__ ) . 'includes/class-shortcodes.php';
require_once plugin_dir_path( __FILE__ ) . 'includes/class-woocommerce.php';

new Admin();
new Frontend();
new API();
new Widgets();
new Shortcodes();
new WooCommerce_Integration();
```

**Correct (conditional, lazy loading):**

```php
// main-plugin.php - smart loading
class My_Plugin {

    public function __construct() {
        // Only load what's needed for this request
        $this->load_dependencies();
        $this->init_hooks();
    }

    private function load_dependencies() {
        // Always needed
        require_once plugin_dir_path( __FILE__ ) . 'includes/functions.php';

        // Admin only
        if ( is_admin() ) {
            require_once plugin_dir_path( __FILE__ ) . 'includes/class-admin.php';
        }

        // Frontend only
        if ( ! is_admin() || wp_doing_ajax() ) {
            require_once plugin_dir_path( __FILE__ ) . 'includes/class-frontend.php';
        }

        // REST API only
        if ( $this->is_rest_request() ) {
            require_once plugin_dir_path( __FILE__ ) . 'includes/class-api.php';
        }

        // WooCommerce integration only if WooCommerce is active
        if ( class_exists( 'WooCommerce' ) ) {
            require_once plugin_dir_path( __FILE__ ) . 'includes/class-woocommerce.php';
        }
    }

    private function init_hooks() {
        // Lazy load widgets only when needed
        add_action( 'widgets_init', [$this, 'load_widgets'] );

        // Lazy load shortcodes only when needed
        add_action( 'init', [$this, 'register_shortcodes'] );

        // Admin hooks
        if ( is_admin() ) {
            add_action( 'admin_menu', [$this, 'admin_menu'] );
        }
    }

    public function load_widgets() {
        require_once plugin_dir_path( __FILE__ ) . 'includes/class-widgets.php';
        register_widget( 'My_Plugin_Widget' );
    }

    public function register_shortcodes() {
        // Only load shortcode class when shortcode might be used
        add_shortcode( 'my_shortcode', function( $atts ) {
            if ( ! class_exists( 'My_Plugin_Shortcode' ) ) {
                require_once plugin_dir_path( __FILE__ ) . 'includes/class-shortcode.php';
            }
            return My_Plugin_Shortcode::render( $atts );
        });
    }

    private function is_rest_request() {
        return defined( 'REST_REQUEST' ) && REST_REQUEST;
    }
}

// Use autoloading for cleaner code
spl_autoload_register( function( $class ) {
    $prefix = 'My_Plugin\\';
    $base_dir = plugin_dir_path( __FILE__ ) . 'includes/';

    $len = strlen( $prefix );
    if ( strncmp( $prefix, $class, $len ) !== 0 ) {
        return;
    }

    $relative_class = substr( $class, $len );
    $file = $base_dir . 'class-' . strtolower( str_replace( '\\', '-', $relative_class ) ) . '.php';

    if ( file_exists( $file ) ) {
        require $file;
    }
});
```

Reference: [Plugin Architecture](https://developer.wordpress.org/plugins/plugin-basics/best-practices/)

### 5.4 Remove Hooks Properly When Needed

**Impact: MEDIUM (Prevents memory leaks and unwanted behavior)**

*Tags: plugin, hooks, removal, cleanup*

When you need to remove hooks added by WordPress core, themes, or other plugins, use `remove_action()` and `remove_filter()` correctly. Match the exact function reference and priority. Use proper timing to ensure hooks are removed after they're added.

**Incorrect (improper hook removal):**

```php
// Wrong: trying to remove before hook is added
remove_action( 'wp_head', 'wp_generator' ); // Too early in plugin file

// Wrong: priority doesn't match
add_action( 'wp_head', 'my_function', 5 );
remove_action( 'wp_head', 'my_function' ); // Default priority 10 - won't work

// Wrong: trying to remove closure (impossible)
add_action( 'init', function() {
    echo 'Hello';
});
// Can't remove anonymous functions!

// Wrong: class method removal with wrong syntax
remove_action( 'init', 'My_Class::my_method' ); // String won't match
```

**Correct (proper hook removal):**

```php
// Remove core hooks at the right time
function remove_unwanted_hooks() {
    // Remove generator tag
    remove_action( 'wp_head', 'wp_generator' );

    // Remove RSD link
    remove_action( 'wp_head', 'rsd_link' );

    // Remove shortlink
    remove_action( 'wp_head', 'wp_shortlink_wp_head' );

    // Remove emoji scripts
    remove_action( 'wp_head', 'print_emoji_detection_script', 7 );
    remove_action( 'wp_print_styles', 'print_emoji_styles' );
}
add_action( 'init', 'remove_unwanted_hooks' );

// Match priority exactly
add_action( 'wp_head', 'my_function', 5 );
remove_action( 'wp_head', 'my_function', 5 ); // Must match priority

// Use named functions instead of closures when removal might be needed
function my_init_function() {
    // Do something
}
add_action( 'init', 'my_init_function' );
// Can be removed later:
remove_action( 'init', 'my_init_function' );

// Class method removal - store instance or use singleton
class My_Plugin {
    private static $instance = null;

    public static function instance() {
        if ( null === self::$instance ) {
            self::$instance = new self();
        }
        return self::$instance;
    }

    public function __construct() {
        add_action( 'init', [$this, 'init_method'] );
    }

    public function init_method() {
        // Do something
    }
}

// Remove class method hook
$plugin = My_Plugin::instance();
remove_action( 'init', [$plugin, 'init_method'] );

// Remove hooks from other plugins (after they're added)
function remove_plugin_hooks() {
    // Remove after the plugin has added its hooks
    if ( class_exists( 'Other_Plugin' ) ) {
        $other = Other_Plugin::instance();
        remove_action( 'wp_footer', [$other, 'render_footer'], 10 );
    }

    // Remove WooCommerce hooks
    if ( function_exists( 'WC' ) ) {
        remove_action( 'woocommerce_before_main_content', 'woocommerce_output_content_wrapper', 10 );
        remove_action( 'woocommerce_after_main_content', 'woocommerce_output_content_wrapper_end', 10 );
    }
}
add_action( 'init', 'remove_plugin_hooks', 20 ); // Late priority to run after plugins

// Finding and removing hooks by searching
function find_and_remove_hook( $tag, $function_name ) {
    global $wp_filter;

    if ( ! isset( $wp_filter[ $tag ] ) ) {
        return false;
    }

    foreach ( $wp_filter[ $tag ]->callbacks as $priority => $callbacks ) {
        foreach ( $callbacks as $key => $callback ) {
            if ( is_array( $callback['function'] ) ) {
                if ( $callback['function'][1] === $function_name ) {
                    remove_action( $tag, $callback['function'], $priority );
                    return true;
                }
            } elseif ( $callback['function'] === $function_name ) {
                remove_action( $tag, $function_name, $priority );
                return true;
            }
        }
    }

    return false;
}
```

Reference: [remove_action](https://developer.wordpress.org/reference/functions/remove_action/)

---

## 6. Media Optimization

**Impact Level:** MEDIUM

Images and media often account for the majority of page weight. Proper image sizing, lazy loading, responsive images, and leveraging WordPress's built-in media handling improve load times and user experience.

### 6.1 Define and Use Appropriate Image Sizes

**Impact: MEDIUM (Prevents serving oversized images)**

*Tags: media, images, sizes, optimization*

Register custom image sizes that match your design requirements. Don't use 'full' size when a smaller size would work. Properly named sizes make development clearer and ensure optimized images are served.

**Incorrect (using wrong sizes):**

```php
// Always using full size - wastes bandwidth
the_post_thumbnail( 'full' );
wp_get_attachment_image( $id, 'full' );

// Using generic sizes that don't match design
the_post_thumbnail( 'medium' ); // May not match your card dimensions

// No custom sizes defined - relying on defaults
// thumbnail: 150x150
// medium: 300x300
// large: 1024x1024
// These rarely match actual design needs
```

**Correct (design-appropriate image sizes):**

```php
// Register sizes that match your actual design
add_action( 'after_setup_theme', function() {
    // Card images in archive pages
    add_image_size( 'card-small', 400, 300, true );
    add_image_size( 'card-medium', 600, 400, true );

    // Featured images
    add_image_size( 'featured-wide', 1200, 630, true ); // Social sharing ratio
    add_image_size( 'featured-hero', 1920, 800, true ); // Hero sections

    // Thumbnails
    add_image_size( 'author-avatar', 100, 100, true );
    add_image_size( 'gallery-thumb', 250, 250, true );

    // Content images (soft crop - maintains aspect ratio)
    add_image_size( 'content-medium', 800, 600, false );
    add_image_size( 'content-large', 1200, 900, false );

    // Enable support for custom sizes in editor
    add_theme_support( 'post-thumbnails' );
});

// Make custom sizes available in media library dropdown
add_filter( 'image_size_names_choose', function( $sizes ) {
    return array_merge( $sizes, [
        'card-small'     => __( 'Card Small', 'theme' ),
        'card-medium'    => __( 'Card Medium', 'theme' ),
        'featured-wide'  => __( 'Featured Wide', 'theme' ),
        'content-medium' => __( 'Content Medium', 'theme' ),
    ]);
});

// Use appropriate sizes in templates
// Archive page cards
while ( have_posts() ) {
    the_post();
    the_post_thumbnail( 'card-medium', ['class' => 'card__image'] );
}

// Single post featured image
if ( is_singular( 'post' ) ) {
    the_post_thumbnail( 'featured-wide' );
}

// Sidebar widgets
the_post_thumbnail( 'card-small' );

// Helper function to get appropriate size based on context
function get_contextual_image_size() {
    if ( is_singular() ) {
        return 'featured-wide';
    }

    if ( is_home() || is_archive() ) {
        return 'card-medium';
    }

    if ( is_search() ) {
        return 'card-small';
    }

    return 'medium';
}

// Dynamic size based on context
the_post_thumbnail( get_contextual_image_size() );

// Remove unused default sizes to save disk space
add_filter( 'intermediate_image_sizes_advanced', function( $sizes ) {
    // Remove sizes you don't use
    unset( $sizes['medium_large'] ); // 768px - often redundant
    unset( $sizes['1536x1536'] );    // 2x medium_large
    unset( $sizes['2048x2048'] );    // 2x large

    return $sizes;
});

// Limit max image dimensions on upload
add_filter( 'big_image_size_threshold', function() {
    return 2560; // Max dimension for scaled images
});
```

Reference: [add_image_size](https://developer.wordpress.org/reference/functions/add_image_size/)

### 6.2 Implement Proper Lazy Loading

**Impact: MEDIUM (Reduces initial page weight by 40-60%)**

*Tags: media, lazy-loading, images, performance*

Use native lazy loading for images and iframes below the fold. WordPress 5.5+ adds `loading="lazy"` by default. Don't lazy load above-the-fold images (especially LCP images) as this hurts Core Web Vitals.

**Incorrect (lazy loading everything or nothing):**

```php
// Lazy loading LCP image - hurts performance
<img src="hero.jpg" loading="lazy" alt="Hero"> <!-- Don't lazy load hero! -->

// No lazy loading - loads all images immediately
<img src="below-fold.jpg" alt="...">

// Using JavaScript lazy loading when native works
<img data-src="image.jpg" class="lazyload" alt="...">
<script src="lazysizes.js"></script>
```

**Correct (strategic lazy loading):**

```php
// WordPress 5.5+ automatically adds loading="lazy"
// Control it with filters

// Skip lazy loading for specific images (LCP candidates)
add_filter( 'wp_img_tag_add_loading_attr', function( $value, $image, $context ) {
    // Don't lazy load featured images on singular pages (likely LCP)
    if ( 'the_content' === $context && is_singular() ) {
        // Check if this is the first/featured image
        static $first_image = true;
        if ( $first_image ) {
            $first_image = false;
            return false; // Disable lazy loading
        }
    }

    // Don't lazy load hero images
    if ( strpos( $image, 'hero-image' ) !== false ) {
        return false;
    }

    return $value;
}, 10, 3 );

// Manually control lazy loading
function render_image( $attachment_id, $is_above_fold = false ) {
    $loading = $is_above_fold ? 'eager' : 'lazy';
    $fetchpriority = $is_above_fold ? 'high' : 'auto';

    echo wp_get_attachment_image( $attachment_id, 'large', false, [
        'loading'       => $loading,
        'fetchpriority' => $fetchpriority,
        'decoding'      => 'async',
    ]);
}

// Hero/LCP image - don't lazy load, add fetchpriority
<img
    src="<?php echo esc_url( $hero_url ); ?>"
    loading="eager"
    fetchpriority="high"
    decoding="async"
    alt="<?php echo esc_attr( $alt ); ?>"
>

// Below-fold images - lazy load
<img
    src="<?php echo esc_url( $image_url ); ?>"
    loading="lazy"
    decoding="async"
    alt="<?php echo esc_attr( $alt ); ?>"
>

// Lazy load iframes (embeds, videos)
<iframe
    src="https://www.youtube.com/embed/VIDEO_ID"
    loading="lazy"
    title="Video title"
></iframe>

// For complex scenarios, use Intersection Observer
function lazy_load_script() {
    if ( ! is_singular() ) {
        return;
    }
    ?>
    <script>
    document.addEventListener('DOMContentLoaded', function() {
        // Only for complex lazy loading needs (e.g., background images)
        const lazyBgs = document.querySelectorAll('[data-bg]');

        if ('IntersectionObserver' in window) {
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        entry.target.style.backgroundImage = `url(${entry.target.dataset.bg})`;
                        observer.unobserve(entry.target);
                    }
                });
            }, { rootMargin: '100px' });

            lazyBgs.forEach(el => observer.observe(el));
        }
    });
    </script>
    <?php
}
add_action( 'wp_footer', 'lazy_load_script' );

// Skip lazy loading for first N images in content
add_filter( 'wp_omit_loading_attr_threshold', function() {
    return 3; // Don't lazy load first 3 images
});
```

Reference: [Native Lazy Loading](https://developer.wordpress.org/reference/functions/wp_img_tag_add_loading_attr/)

### 6.3 Use Responsive Images Properly

**Impact: MEDIUM (30-70% reduction in image bytes transferred)**

*Tags: media, images, responsive, srcset*

Use WordPress's built-in responsive image support with srcset and sizes attributes. This ensures browsers download appropriately sized images for each device, saving bandwidth and improving load times.

**Incorrect (fixed-size images):**

```php
// Single size - downloads full image on all devices
<img src="<?php echo esc_url( get_the_post_thumbnail_url( $post_id, 'full' ) ); ?>" alt="...">

// Hardcoded image without srcset
echo '<img src="' . esc_url( $image_url ) . '" width="800" height="600">';

// Using full-size images everywhere
$image = wp_get_attachment_image_src( $attachment_id, 'full' );
echo '<img src="' . esc_url( $image[0] ) . '">';
```

**Correct (responsive images):**

```php
// WordPress automatically adds srcset when using these functions
// Use wp_get_attachment_image() - includes srcset/sizes automatically
echo wp_get_attachment_image(
    $attachment_id,
    'large', // Base size
    false,
    [
        'class'   => 'featured-image',
        'loading' => 'lazy',
        'sizes'   => '(max-width: 768px) 100vw, 800px',
    ]
);

// the_post_thumbnail() also includes responsive attributes
the_post_thumbnail( 'large', [
    'sizes' => '(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 800px',
] );

// For custom HTML, use wp_get_attachment_image_srcset()
$image_src = wp_get_attachment_image_url( $attachment_id, 'large' );
$image_srcset = wp_get_attachment_image_srcset( $attachment_id, 'large' );
$image_sizes = '(max-width: 768px) 100vw, 800px';
?>

<img
    src="<?php echo esc_url( $image_src ); ?>"
    srcset="<?php echo esc_attr( $image_srcset ); ?>"
    sizes="<?php echo esc_attr( $image_sizes ); ?>"
    alt="<?php echo esc_attr( get_post_meta( $attachment_id, '_wp_attachment_image_alt', true ) ); ?>"
    loading="lazy"
    decoding="async"
>

<?php
// Register appropriate image sizes for your design
add_action( 'after_setup_theme', function() {
    // Add custom sizes that match your breakpoints
    add_image_size( 'hero-mobile', 480, 320, true );
    add_image_size( 'hero-tablet', 768, 512, true );
    add_image_size( 'hero-desktop', 1200, 800, true );

    // Ensure these sizes are included in srcset
    add_filter( 'intermediate_image_sizes_advanced', function( $sizes ) {
        $sizes['hero-mobile'] = [
            'width'  => 480,
            'height' => 320,
            'crop'   => true,
        ];
        return $sizes;
    });
});

// Customize srcset output
add_filter( 'wp_calculate_image_srcset', function( $sources, $size_array, $image_src, $image_meta, $attachment_id ) {
    // Remove very small sizes that won't be used
    foreach ( $sources as $width => $source ) {
        if ( $width < 300 ) {
            unset( $sources[ $width ] );
        }
    }
    return $sources;
}, 10, 5 );

// Picture element for art direction
function responsive_hero_image( $attachment_id ) {
    $mobile  = wp_get_attachment_image_url( $attachment_id, 'hero-mobile' );
    $tablet  = wp_get_attachment_image_url( $attachment_id, 'hero-tablet' );
    $desktop = wp_get_attachment_image_url( $attachment_id, 'hero-desktop' );
    $alt     = get_post_meta( $attachment_id, '_wp_attachment_image_alt', true );
    ?>
    <picture>
        <source media="(min-width: 1200px)" srcset="<?php echo esc_url( $desktop ); ?>">
        <source media="(min-width: 768px)" srcset="<?php echo esc_url( $tablet ); ?>">
        <img src="<?php echo esc_url( $mobile ); ?>" alt="<?php echo esc_attr( $alt ); ?>" loading="lazy">
    </picture>
    <?php
}
```

Reference: [Responsive Images in WordPress](https://developer.wordpress.org/reference/functions/wp_get_attachment_image/)

---

## 7. API and AJAX

**Impact Level:** MEDIUM

REST API and AJAX requests require careful optimization. Proper endpoint design, response caching, nonce handling, and avoiding admin-ajax bottlenecks are essential for interactive WordPress applications.

### 7.1 Avoid Admin-Ajax Bottleneck

**Impact: MEDIUM (Reduces server load and response latency)**

*Tags: api, ajax, admin-ajax, rest-api*

Admin-ajax.php loads the entire WordPress admin environment, making it slow for frontend AJAX requests. For frontend functionality, use the REST API instead. Reserve admin-ajax for admin-only features.

**Incorrect (using admin-ajax for frontend):**

```php
// Frontend AJAX through admin-ajax.php - slow
add_action( 'wp_ajax_get_posts', 'ajax_get_posts' );
add_action( 'wp_ajax_nopriv_get_posts', 'ajax_get_posts' ); // Loads admin

function ajax_get_posts() {
    $posts = get_posts(['numberposts' => 10]);
    wp_send_json_success( $posts );
}

// JavaScript
jQuery.ajax({
    url: ajaxurl, // Points to admin-ajax.php
    data: { action: 'get_posts' },
    success: function(response) {
        // Handle response
    }
});

// Multiple AJAX calls to admin-ajax - compounds the problem
function load_page_data() {
    jQuery.ajax({ url: ajaxurl, data: { action: 'get_sidebar' }});
    jQuery.ajax({ url: ajaxurl, data: { action: 'get_footer' }});
    jQuery.ajax({ url: ajaxurl, data: { action: 'get_notifications' }});
}
```

**Correct (REST API for frontend, admin-ajax for admin):**

```php
// Register REST endpoint for frontend AJAX
register_rest_route( 'mytheme/v1', '/posts', [
    'methods'             => 'GET',
    'callback'            => 'mytheme_get_posts_rest',
    'permission_callback' => '__return_true',
]);

function mytheme_get_posts_rest( $request ) {
    $posts = get_posts([
        'numberposts' => 10,
        'fields'      => 'ids',
    ]);

    $result = array_map( function( $id ) {
        return [
            'id'    => $id,
            'title' => get_the_title( $id ),
            'link'  => get_permalink( $id ),
        ];
    }, $posts );

    return rest_ensure_response( $result );
}

// JavaScript using REST API
fetch('/wp-json/mytheme/v1/posts')
    .then(response => response.json())
    .then(posts => {
        // Handle posts
    });

// Or with nonce for authenticated requests
wp_localize_script( 'theme-main', 'themeAPI', [
    'root'  => esc_url_raw( rest_url( 'mytheme/v1/' ) ),
    'nonce' => wp_create_nonce( 'wp_rest' ),
]);

// JavaScript
fetch(themeAPI.root + 'posts', {
    headers: {
        'X-WP-Nonce': themeAPI.nonce
    }
})
.then(response => response.json())
.then(posts => {
    // Handle posts
});

// Keep admin-ajax for actual admin functionality
add_action( 'wp_ajax_save_admin_settings', 'ajax_save_admin_settings' );
// Note: no nopriv hook - admin only

function ajax_save_admin_settings() {
    // Verify this is an admin request
    if ( ! current_user_can( 'manage_options' ) ) {
        wp_send_json_error( 'Unauthorized', 403 );
    }

    check_ajax_referer( 'admin_settings_nonce', 'nonce' );

    $settings = sanitize_text_field( $_POST['settings'] );
    update_option( 'my_plugin_settings', $settings );

    wp_send_json_success( 'Settings saved' );
}

// If you must use admin-ajax for frontend, minimize load
add_action( 'wp_ajax_nopriv_lightweight_action', 'lightweight_ajax_handler' );

function lightweight_ajax_handler() {
    // Verify nonce
    if ( ! wp_verify_nonce( $_POST['nonce'], 'lightweight_nonce' ) ) {
        wp_send_json_error( 'Invalid nonce' );
    }

    // Do minimal work
    $result = simple_calculation( $_POST['input'] );

    wp_send_json_success( $result );
    // wp_die() is called by wp_send_json_*
}

// Consider custom endpoint file for heavy frontend AJAX
// custom-ajax.php - bypasses admin loading
define( 'SHORTINIT', true );
require_once dirname( __FILE__ ) . '/wp-load.php';

// Only load what's needed
require_once ABSPATH . WPINC . '/formatting.php';
require_once ABSPATH . WPINC . '/meta.php';

// Handle request
$action = sanitize_key( $_REQUEST['action'] ?? '' );
// ... process and return JSON
```

Reference: [AJAX in Plugins](https://developer.wordpress.org/plugins/javascript/ajax/)

### 7.2 Implement Proper Nonce Validation

**Impact: MEDIUM (Prevents CSRF attacks without excessive overhead)**

*Tags: api, security, nonce, validation*

Use WordPress nonces correctly to prevent CSRF attacks. Create nonces with specific actions, validate them on the receiving end, and understand their limitations. Don't over-rely on nonces for authentication.

**Incorrect (missing or improper nonce handling):**

```php
// No nonce validation - vulnerable to CSRF
add_action( 'wp_ajax_delete_item', function() {
    $id = intval( $_POST['id'] );
    wp_delete_post( $id );
    wp_send_json_success();
});

// Generic nonce - less secure
wp_nonce_field( 'my_nonce' ); // Same for all actions
wp_verify_nonce( $_POST['nonce'], 'my_nonce' );

// Nonce in URL without proper handling
$url = admin_url( 'admin.php?action=delete&id=' . $id );
// Missing nonce!

// Using nonces for authentication (wrong!)
if ( wp_verify_nonce( $_POST['nonce'], 'user_action' ) ) {
    // User is authenticated! <- WRONG
    perform_admin_action();
}
```

**Correct (proper nonce implementation):**

```php
// Create action-specific nonces
// In form
wp_nonce_field( 'delete_item_' . $item_id, 'delete_item_nonce' );

// In URL
$delete_url = wp_nonce_url(
    admin_url( 'admin.php?action=delete_item&id=' . $item_id ),
    'delete_item_' . $item_id,
    'delete_nonce'
);

// Validate nonce AND check capabilities
add_action( 'wp_ajax_delete_item', function() {
    // Check nonce first
    if ( ! check_ajax_referer( 'delete_item_' . intval( $_POST['id'] ), 'nonce', false ) ) {
        wp_send_json_error( 'Invalid security token', 403 );
    }

    // Then check capabilities
    if ( ! current_user_can( 'delete_posts' ) ) {
        wp_send_json_error( 'Permission denied', 403 );
    }

    $id = intval( $_POST['id'] );

    // Additional ownership check
    $post = get_post( $id );
    if ( $post->post_author !== get_current_user_id() && ! current_user_can( 'delete_others_posts' ) ) {
        wp_send_json_error( 'Cannot delete others posts', 403 );
    }

    wp_delete_post( $id );
    wp_send_json_success( 'Item deleted' );
});

// REST API nonce handling
wp_localize_script( 'my-script', 'myAPI', [
    'nonce' => wp_create_nonce( 'wp_rest' ),
    'root'  => rest_url( 'myplugin/v1/' ),
]);

// JavaScript
fetch(myAPI.root + 'items/' + itemId, {
    method: 'DELETE',
    headers: {
        'X-WP-Nonce': myAPI.nonce,
        'Content-Type': 'application/json',
    },
});

// REST endpoint with proper permission callback
register_rest_route( 'myplugin/v1', '/items/(?P<id>\d+)', [
    'methods'             => 'DELETE',
    'callback'            => 'delete_item_callback',
    'permission_callback' => function( $request ) {
        // Nonce is verified automatically by REST API when X-WP-Nonce header present
        // Check capabilities
        if ( ! current_user_can( 'delete_posts' ) ) {
            return new WP_Error( 'forbidden', 'Permission denied', ['status' => 403] );
        }

        $item_id = $request->get_param( 'id' );
        $post = get_post( $item_id );

        if ( ! $post ) {
            return new WP_Error( 'not_found', 'Item not found', ['status' => 404] );
        }

        // Check ownership
        if ( $post->post_author !== get_current_user_id() && ! current_user_can( 'delete_others_posts' ) ) {
            return new WP_Error( 'forbidden', 'Cannot delete others items', ['status' => 403] );
        }

        return true;
    },
]);

// Admin page action with nonce
add_action( 'admin_init', function() {
    if ( isset( $_GET['action'] ) && 'delete_item' === $_GET['action'] ) {
        $item_id = intval( $_GET['id'] ?? 0 );

        // Verify nonce
        if ( ! wp_verify_nonce( $_GET['delete_nonce'] ?? '', 'delete_item_' . $item_id ) ) {
            wp_die( 'Security check failed' );
        }

        // Verify capabilities
        if ( ! current_user_can( 'manage_options' ) ) {
            wp_die( 'Permission denied' );
        }

        // Perform action
        delete_item( $item_id );

        // Redirect with message
        wp_safe_redirect( add_query_arg( 'deleted', '1', admin_url( 'admin.php?page=my-items' ) ) );
        exit;
    }
});
```

Reference: [Nonces](https://developer.wordpress.org/plugins/security/nonces/)

### 7.3 Optimize REST API Endpoints

**Impact: MEDIUM (Reduces API response time and payload size)**

*Tags: api, rest, endpoints, optimization*

Design REST API endpoints for performance: return only needed fields, implement pagination, add proper caching headers, and use efficient queries. Avoid N+1 queries and unnecessary data serialization.

**Incorrect (unoptimized endpoints):**

```php
// Returns everything - large payloads
register_rest_route( 'myplugin/v1', '/posts', [
    'callback' => function() {
        $posts = get_posts(['numberposts' => -1]); // All posts!
        return $posts; // Full post objects
    },
]);

// N+1 queries in endpoint
register_rest_route( 'myplugin/v1', '/products', [
    'callback' => function() {
        $products = get_posts(['post_type' => 'product', 'numberposts' => 100]);

        foreach ( $products as &$product ) {
            // Query for each product!
            $product->price = get_post_meta( $product->ID, 'price', true );
            $product->stock = get_post_meta( $product->ID, 'stock', true );
            $product->category = wp_get_post_terms( $product->ID, 'product_cat' );
        }

        return $products;
    },
]);

// No caching headers
register_rest_route( 'myplugin/v1', '/settings', [
    'callback' => function() {
        return get_option( 'my_settings' );
    },
]);
```

**Correct (optimized REST endpoints):**

```php
// Optimized endpoint with pagination and field selection
register_rest_route( 'myplugin/v1', '/posts', [
    'methods'  => 'GET',
    'callback' => 'myplugin_get_posts',
    'permission_callback' => '__return_true',
    'args'     => [
        'page'     => [
            'default'           => 1,
            'sanitize_callback' => 'absint',
        ],
        'per_page' => [
            'default'           => 10,
            'sanitize_callback' => 'absint',
            'validate_callback' => function( $value ) {
                return $value <= 100; // Max limit
            },
        ],
        'fields'   => [
            'default'           => 'id,title,excerpt',
            'sanitize_callback' => 'sanitize_text_field',
        ],
    ],
]);

function myplugin_get_posts( $request ) {
    $page     = $request->get_param( 'page' );
    $per_page = $request->get_param( 'per_page' );
    $fields   = explode( ',', $request->get_param( 'fields' ) );

    $query = new WP_Query([
        'post_type'      => 'post',
        'posts_per_page' => $per_page,
        'paged'          => $page,
        'fields'         => 'ids', // Fetch only IDs initially
    ]);

    $posts = [];
    foreach ( $query->posts as $post_id ) {
        $post_data = ['id' => $post_id];

        if ( in_array( 'title', $fields, true ) ) {
            $post_data['title'] = get_the_title( $post_id );
        }
        if ( in_array( 'excerpt', $fields, true ) ) {
            $post_data['excerpt'] = get_the_excerpt( $post_id );
        }
        if ( in_array( 'content', $fields, true ) ) {
            $post_data['content'] = get_post_field( 'post_content', $post_id );
        }

        $posts[] = $post_data;
    }

    $response = new WP_REST_Response( $posts );

    // Add pagination headers
    $response->header( 'X-WP-Total', $query->found_posts );
    $response->header( 'X-WP-TotalPages', $query->max_num_pages );

    // Add caching headers
    $response->header( 'Cache-Control', 'max-age=300, public' );

    return $response;
}

// Batch meta queries to avoid N+1
register_rest_route( 'myplugin/v1', '/products', [
    'methods'  => 'GET',
    'callback' => function( $request ) {
        $products = get_posts([
            'post_type'      => 'product',
            'posts_per_page' => 50,
            'fields'         => 'ids',
        ]);

        // Batch fetch all meta at once
        update_meta_cache( 'post', $products );

        // Batch fetch all terms at once
        update_object_term_cache( $products, 'product' );

        $result = [];
        foreach ( $products as $id ) {
            $result[] = [
                'id'       => $id,
                'title'    => get_the_title( $id ),
                'price'    => get_post_meta( $id, 'price', true ), // From cache
                'stock'    => get_post_meta( $id, 'stock', true ), // From cache
                'category' => wp_get_post_terms( $id, 'product_cat', ['fields' => 'names'] ),
            ];
        }

        $response = new WP_REST_Response( $result );
        $response->header( 'Cache-Control', 'max-age=60, public' );

        return $response;
    },
    'permission_callback' => '__return_true',
]);

// Cached endpoint
register_rest_route( 'myplugin/v1', '/settings', [
    'methods'  => 'GET',
    'callback' => function() {
        $cache_key = 'rest_settings_response';
        $cached = wp_cache_get( $cache_key, 'rest_api' );

        if ( false !== $cached ) {
            return new WP_REST_Response( $cached );
        }

        $settings = get_option( 'my_settings' );
        wp_cache_set( $cache_key, $settings, 'rest_api', HOUR_IN_SECONDS );

        return new WP_REST_Response( $settings );
    },
    'permission_callback' => '__return_true',
]);
```

Reference: [REST API Handbook](https://developer.wordpress.org/rest-api/)

---

## 8. Advanced Patterns

**Impact Level:** LOW-MEDIUM

Advanced optimization techniques for high-traffic sites including autoload optimization, WP-Cron management, memory management, and platform-specific optimizations used by enterprise WordPress hosts.

### 8.1 Optimize Options Autoloading

**Impact: LOW-MEDIUM (Reduces memory usage and query time on large sites)**

*Tags: advanced, options, autoload, database*

WordPress loads all autoloaded options on every page request. Excessive autoloaded data (over 800KB) slows down every page load. Set autoload to 'no' for options that aren't needed on every request, and regularly audit autoloaded options.

**Incorrect (autoloading large or rarely-used options):**

```php
// Default autoload is 'yes' - loaded on every request
update_option( 'my_plugin_large_data', $large_array ); // Autoloaded!
update_option( 'my_plugin_logs', $logs ); // Rarely needed, still autoloaded
update_option( 'my_plugin_cache', $cache_data ); // Redundant with object cache

// Adding options without considering autoload
add_option( 'my_plugin_settings', $settings ); // Defaults to autoload=yes

// Storing large serialized data
update_option( 'my_plugin_all_products', serialize( $products ) ); // Could be megabytes!
```

**Correct (strategic autoload management):**

```php
// Only autoload options needed on every page
add_option( 'my_plugin_settings', $settings, '', 'yes' ); // Small, needed everywhere
add_option( 'my_plugin_version', '1.0.0', '', 'yes' ); // Tiny, used for upgrades

// Don't autoload large or rarely-used data
add_option( 'my_plugin_logs', [], '', 'no' ); // Only needed in admin
add_option( 'my_plugin_analytics', [], '', 'no' ); // Fetched on specific pages
add_option( 'my_plugin_license', '', '', 'no' ); // Only needed for validation

// Update existing options to not autoload
function fix_option_autoload() {
    global $wpdb;

    // Set specific options to not autoload
    $options_to_fix = [
        'my_plugin_cache',
        'my_plugin_logs',
        'my_plugin_backup',
    ];

    foreach ( $options_to_fix as $option ) {
        $wpdb->update(
            $wpdb->options,
            ['autoload' => 'no'],
            ['option_name' => $option]
        );
    }
}

// Audit autoloaded options (admin tool)
function get_autoload_stats() {
    global $wpdb;

    $results = $wpdb->get_results(
        "SELECT option_name, LENGTH(option_value) as size
         FROM {$wpdb->options}
         WHERE autoload = 'yes'
         ORDER BY size DESC
         LIMIT 50"
    );

    $total = $wpdb->get_var(
        "SELECT SUM(LENGTH(option_value))
         FROM {$wpdb->options}
         WHERE autoload = 'yes'"
    );

    return [
        'total_bytes' => $total,
        'top_options' => $results,
        'warning'     => $total > 800000, // Warn if over 800KB
    ];
}

// Clean up plugin's autoloaded data on deactivation
register_deactivation_hook( __FILE__, function() {
    global $wpdb;

    // Remove large autoloaded options or set to no
    $wpdb->update(
        $wpdb->options,
        ['autoload' => 'no'],
        ['option_name' => 'my_plugin_cached_data']
    );
});

// Use transients or object cache instead of options for cached data
// Good: transient for cached API data
set_transient( 'my_plugin_api_cache', $data, DAY_IN_SECONDS );

// Good: object cache for frequently accessed data
wp_cache_set( 'my_plugin_data', $data, 'my_plugin', HOUR_IN_SECONDS );

// For truly large data, consider custom tables
function maybe_use_custom_table( $data ) {
    if ( strlen( serialize( $data ) ) > 50000 ) {
        // Store in custom table instead
        store_in_custom_table( $data );
    } else {
        update_option( 'my_data', $data, 'no' );
    }
}

// WordPress 6.6+ supports autoload values: 'on', 'off', 'auto'
// 'auto' lets WordPress decide based on option size
add_option( 'my_option', $value, '', 'auto' );
```

Reference: [Options API](https://developer.wordpress.org/reference/functions/add_option/)

### 8.2 Optimize WP-Cron Usage

**Impact: LOW-MEDIUM (Prevents cron from blocking page loads)**

*Tags: advanced, cron, scheduling, background*

WP-Cron runs on page loads, which can slow down user requests. For high-traffic sites, disable WP-Cron's page-load trigger and use system cron instead. Schedule events wisely and clean up unused scheduled events.

**Incorrect (problematic cron usage):**

```php
// Scheduling on every page load (if not scheduled)
function maybe_schedule_my_event() {
    if ( ! wp_next_scheduled( 'my_hourly_event' ) ) {
        wp_schedule_event( time(), 'hourly', 'my_hourly_event' );
    }
}
add_action( 'init', 'maybe_schedule_my_event' ); // Runs every page load!

// Long-running cron task blocks page load
add_action( 'my_sync_event', function() {
    // Syncs 10,000 products - takes 30 seconds
    $products = fetch_all_products_from_api();
    foreach ( $products as $product ) {
        update_product( $product );
    }
});

// Not cleaning up events on deactivation
// Events keep running after plugin is disabled!

// Using too-frequent intervals
wp_schedule_event( time(), 'every_minute', 'my_frequent_task' );
```

**Correct (optimized cron handling):**

```php
// Schedule events during activation, not init
register_activation_hook( __FILE__, function() {
    if ( ! wp_next_scheduled( 'my_plugin_daily_task' ) ) {
        wp_schedule_event( time(), 'daily', 'my_plugin_daily_task' );
    }
});

// Clear events on deactivation
register_deactivation_hook( __FILE__, function() {
    wp_clear_scheduled_hook( 'my_plugin_daily_task' );
    wp_clear_scheduled_hook( 'my_plugin_hourly_task' );
});

// Batch processing for long-running tasks
add_action( 'my_sync_event', function() {
    $offset = get_option( 'my_sync_offset', 0 );
    $batch_size = 100;

    $products = fetch_products_from_api( $batch_size, $offset );

    if ( empty( $products ) ) {
        // Done - reset for next run
        delete_option( 'my_sync_offset' );
        return;
    }

    foreach ( $products as $product ) {
        update_product( $product );
    }

    // Update offset for next batch
    update_option( 'my_sync_offset', $offset + $batch_size );

    // Schedule next batch immediately
    wp_schedule_single_event( time() + 1, 'my_sync_event' );
});

// Use system cron for high-traffic sites
// In wp-config.php:
define( 'DISABLE_WP_CRON', true );

// Then set up system cron:
// */5 * * * * wget -q -O - https://example.com/wp-cron.php?doing_wp_cron >/dev/null 2>&1
// or
// */5 * * * * cd /path/to/wordpress && php wp-cron.php >/dev/null 2>&1

// Custom cron intervals
add_filter( 'cron_schedules', function( $schedules ) {
    $schedules['every_five_minutes'] = [
        'interval' => 5 * MINUTE_IN_SECONDS,
        'display'  => __( 'Every Five Minutes' ),
    ];
    $schedules['twice_daily'] = [
        'interval' => 12 * HOUR_IN_SECONDS,
        'display'  => __( 'Twice Daily' ),
    ];
    return $schedules;
});

// Check cron health (admin diagnostic)
function check_cron_health() {
    $crons = _get_cron_array();
    $issues = [];

    // Check for too many scheduled events
    $total_events = 0;
    foreach ( $crons as $time => $hooks ) {
        $total_events += count( $hooks );
    }

    if ( $total_events > 50 ) {
        $issues[] = "Too many cron events: {$total_events}";
    }

    // Check for orphaned events (hooks without handlers)
    foreach ( $crons as $time => $hooks ) {
        foreach ( $hooks as $hook => $events ) {
            if ( ! has_action( $hook ) ) {
                $issues[] = "Orphaned cron hook: {$hook}";
            }
        }
    }

    // Check if cron is running
    $last_run = get_option( 'my_plugin_cron_last_run', 0 );
    if ( $last_run && ( time() - $last_run ) > DAY_IN_SECONDS ) {
        $issues[] = 'Cron appears to not be running';
    }

    return $issues;
}

// Track cron execution
add_action( 'my_plugin_daily_task', function() {
    update_option( 'my_plugin_cron_last_run', time() );
    // ... do task
}, 1 ); // Early priority to track execution
```

Reference: [WP-Cron](https://developer.wordpress.org/plugins/cron/)

### 8.3 Manage Memory Usage Effectively

**Impact: LOW-MEDIUM (Prevents memory exhaustion on resource-intensive operations)**

*Tags: advanced, memory, optimization, batch-processing*

Large operations can exhaust PHP's memory limit. Monitor memory usage, process data in batches, and clean up resources when done. This is especially important for imports, exports, and batch operations.

**Incorrect (memory-intensive operations):**

```php
// Loading all posts into memory
$all_posts = get_posts(['numberposts' => -1]);
foreach ( $all_posts as $post ) {
    process_post( $post );
}

// Accumulating data without cleanup
$results = [];
foreach ( $huge_dataset as $item ) {
    $results[] = expensive_operation( $item ); // Memory grows unbounded
}

// Not releasing references
function process_large_file( $file ) {
    $content = file_get_contents( $file ); // Could be 100MB
    $processed = transform( $content );
    save_result( $processed );
    // $content and $processed still in memory until function ends
}
```

**Correct (memory-efficient operations):**

```php
// Process in batches with memory cleanup
function process_all_posts_efficiently() {
    $batch_size = 100;
    $offset = 0;

    // Increase memory limit for batch operations if needed
    wp_raise_memory_limit( 'admin' );

    do {
        $posts = get_posts([
            'numberposts' => $batch_size,
            'offset'      => $offset,
            'fields'      => 'ids', // Only get IDs
        ]);

        if ( empty( $posts ) ) {
            break;
        }

        foreach ( $posts as $post_id ) {
            process_post( $post_id );
        }

        $offset += $batch_size;

        // Clear caches to free memory
        wp_cache_flush();

        // Clear static caches in WP core functions
        clean_post_cache( $posts );

        // Log memory usage
        if ( defined( 'WP_DEBUG' ) && WP_DEBUG ) {
            error_log( 'Memory usage: ' . memory_get_usage( true ) / 1024 / 1024 . ' MB' );
        }

    } while ( count( $posts ) === $batch_size );
}

// Generator pattern for memory-efficient iteration
function get_posts_generator( $args = [] ) {
    $defaults = [
        'posts_per_page' => 100,
        'paged'          => 1,
        'fields'         => 'ids',
    ];
    $args = wp_parse_args( $args, $defaults );

    do {
        $query = new WP_Query( $args );

        foreach ( $query->posts as $post_id ) {
            yield $post_id;
        }

        $args['paged']++;

        // Free memory
        wp_cache_flush();

    } while ( $query->have_posts() );
}

// Usage
foreach ( get_posts_generator(['post_type' => 'product']) as $product_id ) {
    update_product( $product_id );
}

// Process large file in chunks
function process_large_file_efficiently( $file ) {
    $handle = fopen( $file, 'r' );

    if ( ! $handle ) {
        return false;
    }

    $chunk_size = 8192; // 8KB chunks

    while ( ! feof( $handle ) ) {
        $chunk = fread( $handle, $chunk_size );
        process_chunk( $chunk );
        unset( $chunk ); // Explicitly free memory
    }

    fclose( $handle );
}

// Monitor memory usage
function check_memory_usage() {
    $limit = ini_get( 'memory_limit' );
    $limit_bytes = wp_convert_hr_to_bytes( $limit );
    $usage = memory_get_usage( true );
    $percentage = ( $usage / $limit_bytes ) * 100;

    if ( $percentage > 80 ) {
        error_log( sprintf(
            'High memory usage: %d%% (%s of %s)',
            $percentage,
            size_format( $usage ),
            $limit
        ));
    }

    return [
        'limit'      => $limit_bytes,
        'usage'      => $usage,
        'percentage' => $percentage,
    ];
}

// Cleanup helper for batch operations
function batch_cleanup() {
    global $wpdb, $wp_object_cache;

    // Clear query log
    $wpdb->queries = [];

    // Clear object cache
    if ( is_object( $wp_object_cache ) ) {
        $wp_object_cache->flush();
    }

    // Clear WP_Query static cache
    wp_reset_query();

    // Force garbage collection (PHP 5.3+)
    if ( function_exists( 'gc_collect_cycles' ) ) {
        gc_collect_cycles();
    }
}

// WP-CLI command with memory management
if ( defined( 'WP_CLI' ) && WP_CLI ) {
    WP_CLI::add_command( 'my-process', function( $args ) {
        $count = 0;

        foreach ( get_posts_generator(['post_type' => 'post']) as $post_id ) {
            process_post( $post_id );
            $count++;

            if ( $count % 100 === 0 ) {
                WP_CLI::log( "Processed {$count} posts, memory: " . size_format( memory_get_usage( true ) ) );
                batch_cleanup();
            }
        }

        WP_CLI::success( "Processed {$count} posts" );
    });
}
```

Reference: [Memory Limit](https://developer.wordpress.org/reference/functions/wp_raise_memory_limit/)

### 8.4 Profile and Monitor Performance

**Impact: LOW-MEDIUM (Enables identification of actual bottlenecks)**

*Tags: advanced, profiling, debugging, query-monitor*

Use profiling tools to identify actual performance bottlenecks rather than optimizing blindly. Query Monitor, Debug Bar, and New Relic help pinpoint slow queries, excessive hooks, and memory issues. Profile in production-like environments.

**Incorrect (blind optimization):**

```php
// Optimizing without measuring
// "I think this is slow, so I'll add caching everywhere"
function get_data() {
    $cached = wp_cache_get( 'my_data' );
    if ( ! $cached ) {
        $cached = 'simple string'; // Caching a simple operation!
        wp_cache_set( 'my_data', $cached );
    }
    return $cached;
}

// Assuming the problem without profiling
// "WordPress is slow, must be the database"
// Actually: it's a plugin loading 50 external scripts
```

**Correct (data-driven optimization):**

```php
// Built-in query logging (development only)
define( 'SAVEQUERIES', true );

// Display query log (in footer or debug panel)
function show_query_log() {
    if ( ! current_user_can( 'manage_options' ) || ! defined( 'SAVEQUERIES' ) ) {
        return;
    }

    global $wpdb;

    $total_time = 0;
    $slow_queries = [];

    foreach ( $wpdb->queries as $query ) {
        $total_time += $query[1];
        if ( $query[1] > 0.05 ) { // Queries over 50ms
            $slow_queries[] = $query;
        }
    }

    echo '<!-- Queries: ' . count( $wpdb->queries ) . ', Time: ' . round( $total_time, 4 ) . 's -->';

    if ( ! empty( $slow_queries ) ) {
        echo '<!-- Slow queries: -->';
        foreach ( $slow_queries as $q ) {
            echo '<!-- ' . esc_html( $q[0] ) . ' (' . round( $q[1] * 1000 ) . 'ms) -->';
        }
    }
}
add_action( 'wp_footer', 'show_query_log', 9999 );

// Custom timing for specific operations
function measure_execution( $callback, $label = 'Operation' ) {
    $start_time = microtime( true );
    $start_memory = memory_get_usage();
    $start_queries = get_num_queries();

    $result = $callback();

    $time = microtime( true ) - $start_time;
    $memory = memory_get_usage() - $start_memory;
    $queries = get_num_queries() - $start_queries;

    if ( defined( 'WP_DEBUG' ) && WP_DEBUG ) {
        error_log( sprintf(
            '%s: %.4fs, %s memory, %d queries',
            $label,
            $time,
            size_format( $memory ),
            $queries
        ));
    }

    return $result;
}

// Usage
$posts = measure_execution( function() {
    return get_posts(['numberposts' => 100]);
}, 'Get posts' );

// Hook timing
class Hook_Timer {
    private static $timings = [];

    public static function start( $hook ) {
        self::$timings[ $hook ] = [
            'start' => microtime( true ),
            'callbacks' => [],
        ];
    }

    public static function end( $hook ) {
        if ( isset( self::$timings[ $hook ] ) ) {
            self::$timings[ $hook ]['total'] = microtime( true ) - self::$timings[ $hook ]['start'];
        }
    }

    public static function get_slow_hooks( $threshold = 0.01 ) {
        $slow = [];
        foreach ( self::$timings as $hook => $data ) {
            if ( isset( $data['total'] ) && $data['total'] > $threshold ) {
                $slow[ $hook ] = $data['total'];
            }
        }
        arsort( $slow );
        return $slow;
    }
}

// Track slow hooks
add_action( 'all', function( $hook ) {
    Hook_Timer::start( $hook );
}, 0 );

add_action( 'all', function( $hook ) {
    Hook_Timer::end( $hook );
}, 9999 );

// Server Timing API (visible in browser DevTools)
function add_server_timing_header() {
    global $wpdb;

    $db_time = 0;
    if ( defined( 'SAVEQUERIES' ) && $wpdb->queries ) {
        foreach ( $wpdb->queries as $q ) {
            $db_time += $q[1];
        }
    }

    $total_time = microtime( true ) - $_SERVER['REQUEST_TIME_FLOAT'];

    header( sprintf(
        'Server-Timing: db;dur=%.1f, total;dur=%.1f, queries;desc="%d"',
        $db_time * 1000,
        $total_time * 1000,
        get_num_queries()
    ));
}
add_action( 'send_headers', 'add_server_timing_header' );

// Integrate with Query Monitor plugin
add_filter( 'qm/collectors', function( $collectors ) {
    // Add custom collector
    $collectors['my_plugin'] = new My_Plugin_QM_Collector();
    return $collectors;
});

// Production monitoring - log slow requests
function log_slow_request() {
    $total_time = microtime( true ) - $_SERVER['REQUEST_TIME_FLOAT'];

    if ( $total_time > 2.0 ) { // Over 2 seconds
        error_log( sprintf(
            'Slow request: %s (%.2fs, %d queries, %s memory)',
            $_SERVER['REQUEST_URI'],
            $total_time,
            get_num_queries(),
            size_format( memory_get_peak_usage() )
        ));
    }
}
add_action( 'shutdown', 'log_slow_request' );
```

Reference: [Query Monitor Plugin](https://querymonitor.com/)

---

## References

- https://developer.wordpress.org/
- https://developer.wordpress.org/coding-standards/
- https://docs.wpvip.com/
- https://github.com/Automattic/VIP-Coding-Standards
- https://github.com/WordPress/WordPress-Coding-Standards
- https://developer.wordpress.org/apis/transients/
- https://developer.wordpress.org/plugins/
- https://developer.wordpress.org/themes/
- https://developer.wordpress.org/rest-api/
- https://10up.github.io/Engineering-Best-Practices/
