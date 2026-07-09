---
title: Use Template Parts Efficiently
impact: HIGH
impactDescription: Reduces code duplication and improves maintainability
tags: theme, templates, partials, organization
---

## Use Template Parts Efficiently

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
