---
title: Optimize Meta Queries with Proper Indexing
impact: HIGH
impactDescription: 5-50x improvement for meta-heavy queries
tags: database, meta_query, indexing, performance
---

## Optimize Meta Queries with Proper Indexing

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
