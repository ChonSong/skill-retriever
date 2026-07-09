---
title: Implement Proper Lazy Loading
impact: MEDIUM
impactDescription: Reduces initial page weight by 40-60%
tags: media, lazy-loading, images, performance
---

## Implement Proper Lazy Loading

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
