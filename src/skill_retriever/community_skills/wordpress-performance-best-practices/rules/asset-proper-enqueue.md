---
title: Use Proper Script and Style Enqueueing
impact: HIGH
impactDescription: Enables dependency management and prevents conflicts
tags: assets, scripts, styles, enqueue
---

## Use Proper Script and Style Enqueueing

Always use `wp_enqueue_script()` and `wp_enqueue_style()` to load assets. Never hardcode script or link tags in templates. Proper enqueueing enables dependency management, versioning, conditional loading, and prevents duplicate asset loading.

**Incorrect (hardcoded assets):**

```php
// Don't hardcode in header.php or templates
<script src="<?php echo get_template_directory_uri(); ?>/js/custom.js"></script>
<link rel="stylesheet" href="<?php echo get_template_directory_uri(); ?>/css/custom.css">

// Don't echo script tags in functions
function add_my_scripts() {
    echo '<script src="https://example.com/script.js"></script>';
}
add_action( 'wp_head', 'add_my_scripts' );

// Don't use wp_head for inline scripts that should be enqueued
add_action( 'wp_head', function() {
    ?>
    <script>
        var myConfig = { api: '<?php echo esc_js( $api_url ); ?>' };
    </script>
    <?php
});
```

**Correct (proper enqueueing):**

```php
// Enqueue scripts and styles properly
function theme_enqueue_assets() {
    // Enqueue styles
    wp_enqueue_style(
        'theme-main',
        get_template_directory_uri() . '/css/main.css',
        [], // dependencies
        wp_get_theme()->get( 'Version' )
    );

    // Enqueue scripts with dependencies
    wp_enqueue_script(
        'theme-main',
        get_template_directory_uri() . '/js/main.js',
        ['jquery'], // dependencies
        wp_get_theme()->get( 'Version' ),
        true // in footer
    );

    // Pass data to scripts using wp_localize_script or wp_add_inline_script
    wp_localize_script( 'theme-main', 'themeConfig', [
        'ajaxUrl' => admin_url( 'admin-ajax.php' ),
        'nonce'   => wp_create_nonce( 'theme_nonce' ),
        'apiUrl'  => esc_url( $api_url ),
    ]);

    // Or use wp_add_inline_script for more control
    wp_add_inline_script(
        'theme-main',
        'const THEME_VERSION = ' . wp_json_encode( wp_get_theme()->get( 'Version' ) ) . ';',
        'before'
    );
}
add_action( 'wp_enqueue_scripts', 'theme_enqueue_assets' );

// For admin scripts
function admin_enqueue_assets( $hook ) {
    // Only load on specific admin pages
    if ( 'edit.php' !== $hook ) {
        return;
    }

    wp_enqueue_script(
        'admin-custom',
        get_template_directory_uri() . '/js/admin.js',
        ['jquery'],
        '1.0.0',
        true
    );
}
add_action( 'admin_enqueue_scripts', 'admin_enqueue_assets' );

// For login page
add_action( 'login_enqueue_scripts', function() {
    wp_enqueue_style( 'custom-login', get_template_directory_uri() . '/css/login.css' );
});
```

Reference: [wp_enqueue_script](https://developer.wordpress.org/reference/functions/wp_enqueue_script/)
