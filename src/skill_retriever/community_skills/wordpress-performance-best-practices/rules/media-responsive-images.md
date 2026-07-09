---
title: Use Responsive Images Properly
impact: MEDIUM
impactDescription: 30-70% reduction in image bytes transferred
tags: media, images, responsive, srcset
---

## Use Responsive Images Properly

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
