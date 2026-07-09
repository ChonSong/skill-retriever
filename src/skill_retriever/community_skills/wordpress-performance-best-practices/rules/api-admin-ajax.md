---
title: Avoid Admin-Ajax Bottleneck
impact: MEDIUM
impactDescription: Reduces server load and response latency
tags: api, ajax, admin-ajax, rest-api
---

## Avoid Admin-Ajax Bottleneck

Admin-ajax.php loads the entire WordPress admin environment, making it slow for frontend AJAX requests. For frontend functionality, use the REST API instead. Reserve admin-ajax for admin-only features.

**Incorrect (using admin-ajax for frontend):**

```php
// Frontend AJAX through admin-ajax.php - slow
add_action( 'wp_ajax_get_posts', 'ajax_get_posts' );
add_action( 'wp_ajax_nopriv_get_posts', 'ajax_get_posts' ); // Loads admin

function ajax_get_posts() {
    $posts = get_posts(['numberposts' => 10]);
    wp_send_json_success( $posts );
}

// JavaScript
jQuery.ajax({
    url: ajaxurl, // Points to admin-ajax.php
    data: { action: 'get_posts' },
    success: function(response) {
        // Handle response
    }
});

// Multiple AJAX calls to admin-ajax - compounds the problem
function load_page_data() {
    jQuery.ajax({ url: ajaxurl, data: { action: 'get_sidebar' }});
    jQuery.ajax({ url: ajaxurl, data: { action: 'get_footer' }});
    jQuery.ajax({ url: ajaxurl, data: { action: 'get_notifications' }});
}
```

**Correct (REST API for frontend, admin-ajax for admin):**

```php
// Register REST endpoint for frontend AJAX
register_rest_route( 'mytheme/v1', '/posts', [
    'methods'             => 'GET',
    'callback'            => 'mytheme_get_posts_rest',
    'permission_callback' => '__return_true',
]);

function mytheme_get_posts_rest( $request ) {
    $posts = get_posts([
        'numberposts' => 10,
        'fields'      => 'ids',
    ]);

    $result = array_map( function( $id ) {
        return [
            'id'    => $id,
            'title' => get_the_title( $id ),
            'link'  => get_permalink( $id ),
        ];
    }, $posts );

    return rest_ensure_response( $result );
}

// JavaScript using REST API
fetch('/wp-json/mytheme/v1/posts')
    .then(response => response.json())
    .then(posts => {
        // Handle posts
    });

// Or with nonce for authenticated requests
wp_localize_script( 'theme-main', 'themeAPI', [
    'root'  => esc_url_raw( rest_url( 'mytheme/v1/' ) ),
    'nonce' => wp_create_nonce( 'wp_rest' ),
]);

// JavaScript
fetch(themeAPI.root + 'posts', {
    headers: {
        'X-WP-Nonce': themeAPI.nonce
    }
})
.then(response => response.json())
.then(posts => {
    // Handle posts
});

// Keep admin-ajax for actual admin functionality
add_action( 'wp_ajax_save_admin_settings', 'ajax_save_admin_settings' );
// Note: no nopriv hook - admin only

function ajax_save_admin_settings() {
    // Verify this is an admin request
    if ( ! current_user_can( 'manage_options' ) ) {
        wp_send_json_error( 'Unauthorized', 403 );
    }

    check_ajax_referer( 'admin_settings_nonce', 'nonce' );

    $settings = sanitize_text_field( $_POST['settings'] );
    update_option( 'my_plugin_settings', $settings );

    wp_send_json_success( 'Settings saved' );
}

// If you must use admin-ajax for frontend, minimize load
add_action( 'wp_ajax_nopriv_lightweight_action', 'lightweight_ajax_handler' );

function lightweight_ajax_handler() {
    // Verify nonce
    if ( ! wp_verify_nonce( $_POST['nonce'], 'lightweight_nonce' ) ) {
        wp_send_json_error( 'Invalid nonce' );
    }

    // Do minimal work
    $result = simple_calculation( $_POST['input'] );

    wp_send_json_success( $result );
    // wp_die() is called by wp_send_json_*
}

// Consider custom endpoint file for heavy frontend AJAX
// custom-ajax.php - bypasses admin loading
define( 'SHORTINIT', true );
require_once dirname( __FILE__ ) . '/wp-load.php';

// Only load what's needed
require_once ABSPATH . WPINC . '/formatting.php';
require_once ABSPATH . WPINC . '/meta.php';

// Handle request
$action = sanitize_key( $_REQUEST['action'] ?? '' );
// ... process and return JSON
```

Reference: [AJAX in Plugins](https://developer.wordpress.org/plugins/javascript/ajax/)
