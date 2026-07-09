---
title: Minify and Combine Assets Appropriately
impact: MEDIUM
impactDescription: 20-40% reduction in asset file sizes
tags: assets, minification, optimization, http2
---

## Minify and Combine Assets Appropriately

Minify CSS and JavaScript files to reduce file sizes. With HTTP/2, combining files is less critical than before, but minification remains important. Use build tools for development and consider caching plugins for production.

**Incorrect (unminified production assets):**

```php
// Loading development/unminified versions in production
wp_enqueue_script( 'theme-main', get_template_directory_uri() . '/js/main.js' );
wp_enqueue_style( 'theme-style', get_template_directory_uri() . '/css/style.css' );

// Manually combining scripts incorrectly
function combine_scripts() {
    $combined = '';
    $combined .= file_get_contents( get_template_directory() . '/js/file1.js' );
    $combined .= file_get_contents( get_template_directory() . '/js/file2.js' );
    echo '<script>' . $combined . '</script>'; // Security risk, no caching
}
```

**Correct (environment-aware asset loading):**

```php
// Load minified in production, source in development
function enqueue_theme_assets() {
    $suffix = defined( 'SCRIPT_DEBUG' ) && SCRIPT_DEBUG ? '' : '.min';
    $version = wp_get_theme()->get( 'Version' );

    wp_enqueue_style(
        'theme-style',
        get_template_directory_uri() . "/css/style{$suffix}.css",
        [],
        $version
    );

    wp_enqueue_script(
        'theme-main',
        get_template_directory_uri() . "/js/main{$suffix}.js",
        ['jquery'],
        $version,
        true
    );
}
add_action( 'wp_enqueue_scripts', 'enqueue_theme_assets' );

// Use build tools (example package.json scripts)
/*
{
    "scripts": {
        "build:css": "sass src/scss:dist/css && postcss dist/css/*.css --use autoprefixer cssnano -d dist/css",
        "build:js": "esbuild src/js/main.js --bundle --minify --outfile=dist/js/main.min.js",
        "build": "npm run build:css && npm run build:js",
        "watch": "npm run build -- --watch"
    }
}
*/

// Critical CSS inline for above-the-fold content
function inline_critical_css() {
    $critical_css_file = get_template_directory() . '/css/critical.css';

    if ( file_exists( $critical_css_file ) ) {
        $critical_css = file_get_contents( $critical_css_file );
        echo '<style id="critical-css">' . $critical_css . '</style>';
    }
}
add_action( 'wp_head', 'inline_critical_css', 1 );

// Defer non-critical CSS
function defer_non_critical_css() {
    ?>
    <link rel="preload" href="<?php echo esc_url( get_template_directory_uri() . '/css/style.min.css' ); ?>" as="style" onload="this.onload=null;this.rel='stylesheet'">
    <noscript><link rel="stylesheet" href="<?php echo esc_url( get_template_directory_uri() . '/css/style.min.css' ); ?>"></noscript>
    <?php
}
add_action( 'wp_head', 'defer_non_critical_css', 2 );

// Add resource hints for external resources
function add_resource_hints() {
    // Preconnect to external domains
    echo '<link rel="preconnect" href="https://fonts.googleapis.com">';
    echo '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>';

    // DNS prefetch for analytics
    echo '<link rel="dns-prefetch" href="https://www.google-analytics.com">';
}
add_action( 'wp_head', 'add_resource_hints', 1 );
```

Consider using caching plugins (WP Rocket, W3 Total Cache) for automatic minification and combination in production environments.

Reference: [Resource Hints](https://developer.wordpress.org/reference/functions/wp_resource_hints/)
