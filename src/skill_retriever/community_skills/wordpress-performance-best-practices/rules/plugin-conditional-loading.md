---
title: Load Plugin Code Conditionally
impact: MEDIUM-HIGH
impactDescription: Reduces memory usage and execution time on irrelevant requests
tags: plugin, conditional, loading, performance
---

## Load Plugin Code Conditionally

Don't load all plugin code on every request. Use conditional checks to only load code when it's actually needed. Frontend code shouldn't load in admin, admin code shouldn't load on frontend, and feature-specific code should only load when that feature is used.

**Incorrect (loading everything everywhere):**

```php
// main-plugin.php - loads everything on every request
require_once plugin_dir_path( __FILE__ ) . 'includes/class-admin.php';
require_once plugin_dir_path( __FILE__ ) . 'includes/class-frontend.php';
require_once plugin_dir_path( __FILE__ ) . 'includes/class-api.php';
require_once plugin_dir_path( __FILE__ ) . 'includes/class-widgets.php';
require_once plugin_dir_path( __FILE__ ) . 'includes/class-shortcodes.php';
require_once plugin_dir_path( __FILE__ ) . 'includes/class-woocommerce.php';

new Admin();
new Frontend();
new API();
new Widgets();
new Shortcodes();
new WooCommerce_Integration();
```

**Correct (conditional, lazy loading):**

```php
// main-plugin.php - smart loading
class My_Plugin {

    public function __construct() {
        // Only load what's needed for this request
        $this->load_dependencies();
        $this->init_hooks();
    }

    private function load_dependencies() {
        // Always needed
        require_once plugin_dir_path( __FILE__ ) . 'includes/functions.php';

        // Admin only
        if ( is_admin() ) {
            require_once plugin_dir_path( __FILE__ ) . 'includes/class-admin.php';
        }

        // Frontend only
        if ( ! is_admin() || wp_doing_ajax() ) {
            require_once plugin_dir_path( __FILE__ ) . 'includes/class-frontend.php';
        }

        // REST API only
        if ( $this->is_rest_request() ) {
            require_once plugin_dir_path( __FILE__ ) . 'includes/class-api.php';
        }

        // WooCommerce integration only if WooCommerce is active
        if ( class_exists( 'WooCommerce' ) ) {
            require_once plugin_dir_path( __FILE__ ) . 'includes/class-woocommerce.php';
        }
    }

    private function init_hooks() {
        // Lazy load widgets only when needed
        add_action( 'widgets_init', [$this, 'load_widgets'] );

        // Lazy load shortcodes only when needed
        add_action( 'init', [$this, 'register_shortcodes'] );

        // Admin hooks
        if ( is_admin() ) {
            add_action( 'admin_menu', [$this, 'admin_menu'] );
        }
    }

    public function load_widgets() {
        require_once plugin_dir_path( __FILE__ ) . 'includes/class-widgets.php';
        register_widget( 'My_Plugin_Widget' );
    }

    public function register_shortcodes() {
        // Only load shortcode class when shortcode might be used
        add_shortcode( 'my_shortcode', function( $atts ) {
            if ( ! class_exists( 'My_Plugin_Shortcode' ) ) {
                require_once plugin_dir_path( __FILE__ ) . 'includes/class-shortcode.php';
            }
            return My_Plugin_Shortcode::render( $atts );
        });
    }

    private function is_rest_request() {
        return defined( 'REST_REQUEST' ) && REST_REQUEST;
    }
}

// Use autoloading for cleaner code
spl_autoload_register( function( $class ) {
    $prefix = 'My_Plugin\\';
    $base_dir = plugin_dir_path( __FILE__ ) . 'includes/';

    $len = strlen( $prefix );
    if ( strncmp( $prefix, $class, $len ) !== 0 ) {
        return;
    }

    $relative_class = substr( $class, $len );
    $file = $base_dir . 'class-' . strtolower( str_replace( '\\', '-', $relative_class ) ) . '.php';

    if ( file_exists( $file ) ) {
        require $file;
    }
});
```

Reference: [Plugin Architecture](https://developer.wordpress.org/plugins/plugin-basics/best-practices/)
