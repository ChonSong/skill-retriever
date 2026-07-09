---
title: Optimize WordPress Loops
impact: MEDIUM-HIGH
impactDescription: Prevents memory issues and N+1 query patterns
tags: theme, loops, wp_query, optimization
---

## Optimize WordPress Loops

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
