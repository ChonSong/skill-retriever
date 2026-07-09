---
title: Dequeue Unused Plugin Assets
impact: MEDIUM-HIGH
impactDescription: Removes unnecessary HTTP requests and reduces page weight
tags: assets, plugins, optimization, dequeue
---

## Dequeue Unused Plugin Assets

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
