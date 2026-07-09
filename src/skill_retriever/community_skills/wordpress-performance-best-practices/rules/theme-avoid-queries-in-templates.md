---
title: Avoid Database Queries in Templates
impact: HIGH
impactDescription: Prevents N+1 queries and template-level bottlenecks
tags: theme, templates, queries, performance
---

## Avoid Database Queries in Templates

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
