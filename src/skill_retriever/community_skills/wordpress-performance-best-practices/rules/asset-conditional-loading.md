---
title: Load Assets Conditionally
impact: HIGH
impactDescription: 30-50% reduction in unnecessary asset loading
tags: assets, conditional, performance, optimization
---

## Load Assets Conditionally

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
