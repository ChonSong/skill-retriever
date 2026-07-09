---
title: Optimize REST API Endpoints
impact: MEDIUM
impactDescription: Reduces API response time and payload size
tags: api, rest, endpoints, optimization
---

## Optimize REST API Endpoints

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
