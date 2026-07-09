---
title: Implement Proper Nonce Validation
impact: MEDIUM
impactDescription: Prevents CSRF attacks without excessive overhead
tags: api, security, nonce, validation
---

## Implement Proper Nonce Validation

Use WordPress nonces correctly to prevent CSRF attacks. Create nonces with specific actions, validate them on the receiving end, and understand their limitations. Don't over-rely on nonces for authentication.

**Incorrect (missing or improper nonce handling):**

```php
// No nonce validation - vulnerable to CSRF
add_action( 'wp_ajax_delete_item', function() {
    $id = intval( $_POST['id'] );
    wp_delete_post( $id );
    wp_send_json_success();
});

// Generic nonce - less secure
wp_nonce_field( 'my_nonce' ); // Same for all actions
wp_verify_nonce( $_POST['nonce'], 'my_nonce' );

// Nonce in URL without proper handling
$url = admin_url( 'admin.php?action=delete&id=' . $id );
// Missing nonce!

// Using nonces for authentication (wrong!)
if ( wp_verify_nonce( $_POST['nonce'], 'user_action' ) ) {
    // User is authenticated! <- WRONG
    perform_admin_action();
}
```

**Correct (proper nonce implementation):**

```php
// Create action-specific nonces
// In form
wp_nonce_field( 'delete_item_' . $item_id, 'delete_item_nonce' );

// In URL
$delete_url = wp_nonce_url(
    admin_url( 'admin.php?action=delete_item&id=' . $item_id ),
    'delete_item_' . $item_id,
    'delete_nonce'
);

// Validate nonce AND check capabilities
add_action( 'wp_ajax_delete_item', function() {
    // Check nonce first
    if ( ! check_ajax_referer( 'delete_item_' . intval( $_POST['id'] ), 'nonce', false ) ) {
        wp_send_json_error( 'Invalid security token', 403 );
    }

    // Then check capabilities
    if ( ! current_user_can( 'delete_posts' ) ) {
        wp_send_json_error( 'Permission denied', 403 );
    }

    $id = intval( $_POST['id'] );

    // Additional ownership check
    $post = get_post( $id );
    if ( $post->post_author !== get_current_user_id() && ! current_user_can( 'delete_others_posts' ) ) {
        wp_send_json_error( 'Cannot delete others posts', 403 );
    }

    wp_delete_post( $id );
    wp_send_json_success( 'Item deleted' );
});

// REST API nonce handling
wp_localize_script( 'my-script', 'myAPI', [
    'nonce' => wp_create_nonce( 'wp_rest' ),
    'root'  => rest_url( 'myplugin/v1/' ),
]);

// JavaScript
fetch(myAPI.root + 'items/' + itemId, {
    method: 'DELETE',
    headers: {
        'X-WP-Nonce': myAPI.nonce,
        'Content-Type': 'application/json',
    },
});

// REST endpoint with proper permission callback
register_rest_route( 'myplugin/v1', '/items/(?P<id>\d+)', [
    'methods'             => 'DELETE',
    'callback'            => 'delete_item_callback',
    'permission_callback' => function( $request ) {
        // Nonce is verified automatically by REST API when X-WP-Nonce header present
        // Check capabilities
        if ( ! current_user_can( 'delete_posts' ) ) {
            return new WP_Error( 'forbidden', 'Permission denied', ['status' => 403] );
        }

        $item_id = $request->get_param( 'id' );
        $post = get_post( $item_id );

        if ( ! $post ) {
            return new WP_Error( 'not_found', 'Item not found', ['status' => 404] );
        }

        // Check ownership
        if ( $post->post_author !== get_current_user_id() && ! current_user_can( 'delete_others_posts' ) ) {
            return new WP_Error( 'forbidden', 'Cannot delete others items', ['status' => 403] );
        }

        return true;
    },
]);

// Admin page action with nonce
add_action( 'admin_init', function() {
    if ( isset( $_GET['action'] ) && 'delete_item' === $_GET['action'] ) {
        $item_id = intval( $_GET['id'] ?? 0 );

        // Verify nonce
        if ( ! wp_verify_nonce( $_GET['delete_nonce'] ?? '', 'delete_item_' . $item_id ) ) {
            wp_die( 'Security check failed' );
        }

        // Verify capabilities
        if ( ! current_user_can( 'manage_options' ) ) {
            wp_die( 'Permission denied' );
        }

        // Perform action
        delete_item( $item_id );

        // Redirect with message
        wp_safe_redirect( add_query_arg( 'deleted', '1', admin_url( 'admin.php?page=my-items' ) ) );
        exit;
    }
});
```

Reference: [Nonces](https://developer.wordpress.org/plugins/security/nonces/)
