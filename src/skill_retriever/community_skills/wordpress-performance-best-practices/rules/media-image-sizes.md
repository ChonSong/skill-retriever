---
title: Define and Use Appropriate Image Sizes
impact: MEDIUM
impactDescription: Prevents serving oversized images
tags: media, images, sizes, optimization
---

## Define and Use Appropriate Image Sizes

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
