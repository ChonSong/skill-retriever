---
title: Remove Hooks Properly When Needed
impact: MEDIUM
impactDescription: Prevents memory leaks and unwanted behavior
tags: plugin, hooks, removal, cleanup
---

## Remove Hooks Properly When Needed

When you need to remove hooks added by WordPress core, themes, or other plugins, use `remove_action()` and `remove_filter()` correctly. Match the exact function reference and priority. Use proper timing to ensure hooks are removed after they're added.

**Incorrect (improper hook removal):**

```php
// Wrong: trying to remove before hook is added
remove_action( 'wp_head', 'wp_generator' ); // Too early in plugin file

// Wrong: priority doesn't match
add_action( 'wp_head', 'my_function', 5 );
remove_action( 'wp_head', 'my_function' ); // Default priority 10 - won't work

// Wrong: trying to remove closure (impossible)
add_action( 'init', function() {
    echo 'Hello';
});
// Can't remove anonymous functions!

// Wrong: class method removal with wrong syntax
remove_action( 'init', 'My_Class::my_method' ); // String won't match
```

**Correct (proper hook removal):**

```php
// Remove core hooks at the right time
function remove_unwanted_hooks() {
    // Remove generator tag
    remove_action( 'wp_head', 'wp_generator' );

    // Remove RSD link
    remove_action( 'wp_head', 'rsd_link' );

    // Remove shortlink
    remove_action( 'wp_head', 'wp_shortlink_wp_head' );

    // Remove emoji scripts
    remove_action( 'wp_head', 'print_emoji_detection_script', 7 );
    remove_action( 'wp_print_styles', 'print_emoji_styles' );
}
add_action( 'init', 'remove_unwanted_hooks' );

// Match priority exactly
add_action( 'wp_head', 'my_function', 5 );
remove_action( 'wp_head', 'my_function', 5 ); // Must match priority

// Use named functions instead of closures when removal might be needed
function my_init_function() {
    // Do something
}
add_action( 'init', 'my_init_function' );
// Can be removed later:
remove_action( 'init', 'my_init_function' );

// Class method removal - store instance or use singleton
class My_Plugin {
    private static $instance = null;

    public static function instance() {
        if ( null === self::$instance ) {
            self::$instance = new self();
        }
        return self::$instance;
    }

    public function __construct() {
        add_action( 'init', [$this, 'init_method'] );
    }

    public function init_method() {
        // Do something
    }
}

// Remove class method hook
$plugin = My_Plugin::instance();
remove_action( 'init', [$plugin, 'init_method'] );

// Remove hooks from other plugins (after they're added)
function remove_plugin_hooks() {
    // Remove after the plugin has added its hooks
    if ( class_exists( 'Other_Plugin' ) ) {
        $other = Other_Plugin::instance();
        remove_action( 'wp_footer', [$other, 'render_footer'], 10 );
    }

    // Remove WooCommerce hooks
    if ( function_exists( 'WC' ) ) {
        remove_action( 'woocommerce_before_main_content', 'woocommerce_output_content_wrapper', 10 );
        remove_action( 'woocommerce_after_main_content', 'woocommerce_output_content_wrapper_end', 10 );
    }
}
add_action( 'init', 'remove_plugin_hooks', 20 ); // Late priority to run after plugins

// Finding and removing hooks by searching
function find_and_remove_hook( $tag, $function_name ) {
    global $wp_filter;

    if ( ! isset( $wp_filter[ $tag ] ) ) {
        return false;
    }

    foreach ( $wp_filter[ $tag ]->callbacks as $priority => $callbacks ) {
        foreach ( $callbacks as $key => $callback ) {
            if ( is_array( $callback['function'] ) ) {
                if ( $callback['function'][1] === $function_name ) {
                    remove_action( $tag, $callback['function'], $priority );
                    return true;
                }
            } elseif ( $callback['function'] === $function_name ) {
                remove_action( $tag, $function_name, $priority );
                return true;
            }
        }
    }

    return false;
}
```

Reference: [remove_action](https://developer.wordpress.org/reference/functions/remove_action/)
