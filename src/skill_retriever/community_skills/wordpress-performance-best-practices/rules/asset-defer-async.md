---
title: Use Defer and Async for Non-Critical Scripts
impact: HIGH
impactDescription: Improves LCP and reduces render-blocking time
tags: assets, defer, async, core-web-vitals
---

## Use Defer and Async for Non-Critical Scripts

Add `defer` or `async` attributes to non-critical scripts to prevent them from blocking page rendering. Since WordPress 6.3, use the `strategy` parameter in `wp_register_script()` and `wp_enqueue_script()` for clean defer/async support.

**Incorrect (render-blocking scripts):**

```php
// All scripts block rendering by default
wp_enqueue_script( 'analytics', 'https://example.com/analytics.js', [], '1.0', false );
wp_enqueue_script( 'chat-widget', 'https://example.com/chat.js', [], '1.0', false );

// Old hack using script_loader_tag filter (fragile)
add_filter( 'script_loader_tag', function( $tag, $handle ) {
    if ( 'my-script' === $handle ) {
        return str_replace( ' src', ' defer src', $tag );
    }
    return $tag;
}, 10, 2 );
```

**Correct (using defer/async strategies):**

```php
// WordPress 6.3+ native defer/async support
function enqueue_optimized_scripts() {
    // Defer non-critical scripts (executes after HTML parsing, maintains order)
    wp_enqueue_script(
        'analytics',
        'https://example.com/analytics.js',
        [],
        '1.0',
        [
            'strategy'  => 'defer',
            'in_footer' => true,
        ]
    );

    // Async for independent scripts (executes as soon as loaded)
    wp_enqueue_script(
        'chat-widget',
        'https://example.com/chat.js',
        [],
        '1.0',
        [
            'strategy'  => 'async',
            'in_footer' => true,
        ]
    );

    // Regular script that needs to run immediately
    wp_enqueue_script(
        'critical-above-fold',
        get_template_directory_uri() . '/js/critical.js',
        [],
        '1.0',
        false // Load in head, no defer
    );

    // Deferred script with dependencies
    wp_enqueue_script(
        'theme-main',
        get_template_directory_uri() . '/js/main.js',
        ['jquery'],
        '1.0',
        [
            'strategy'  => 'defer',
            'in_footer' => true,
        ]
    );
}
add_action( 'wp_enqueue_scripts', 'enqueue_optimized_scripts' );

// For WordPress < 6.3, use filter approach
function add_defer_attribute( $tag, $handle, $src ) {
    $defer_scripts = ['analytics', 'chat-widget', 'social-share'];

    if ( in_array( $handle, $defer_scripts, true ) ) {
        return '<script src="' . esc_url( $src ) . '" defer></script>' . "\n";
    }

    $async_scripts = ['beacon', 'pixel'];

    if ( in_array( $handle, $async_scripts, true ) ) {
        return '<script src="' . esc_url( $src ) . '" async></script>' . "\n";
    }

    return $tag;
}
add_filter( 'script_loader_tag', 'add_defer_attribute', 10, 3 );

// Defer third-party scripts
function defer_third_party_scripts( $tag, $handle, $src ) {
    // Defer all external scripts by default
    if ( strpos( $src, home_url() ) === false && strpos( $tag, 'defer' ) === false ) {
        return str_replace( '<script ', '<script defer ', $tag );
    }
    return $tag;
}
add_filter( 'script_loader_tag', 'defer_third_party_scripts', 10, 3 );
```

Use `defer` for scripts that depend on DOM or other scripts. Use `async` only for independent scripts like analytics that don't depend on anything.

Reference: [WordPress Script Loading Strategies](https://developer.wordpress.org/reference/functions/wp_enqueue_script/#script-loading-strategies)
