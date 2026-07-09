---
title: Use Autoloading for Plugin Classes
impact: MEDIUM-HIGH
impactDescription: Loads only required classes, reduces memory footprint
tags: plugin, autoloading, classes, composer
---

## Use Autoloading for Plugin Classes

Use PHP autoloading instead of manually requiring files. Autoloading ensures classes are only loaded when actually used, reducing memory consumption and improving performance. Use Composer's autoloader or implement PSR-4 compatible autoloading.

**Incorrect (manual requires):**

```php
// Every class loaded regardless of whether it's used
require_once plugin_dir_path( __FILE__ ) . 'includes/class-post-handler.php';
require_once plugin_dir_path( __FILE__ ) . 'includes/class-user-handler.php';
require_once plugin_dir_path( __FILE__ ) . 'includes/class-comment-handler.php';
require_once plugin_dir_path( __FILE__ ) . 'includes/class-media-handler.php';
require_once plugin_dir_path( __FILE__ ) . 'includes/class-settings.php';
require_once plugin_dir_path( __FILE__ ) . 'includes/class-api.php';
require_once plugin_dir_path( __FILE__ ) . 'includes/class-export.php';
require_once plugin_dir_path( __FILE__ ) . 'includes/class-import.php';
// ... 20 more files

// Class check before use still loads the file
if ( class_exists( 'My_Export_Handler' ) ) {
    // Already loaded above
}
```

**Correct (PSR-4 autoloading with Composer):**

```php
// composer.json
{
    "name": "vendor/my-plugin",
    "autoload": {
        "psr-4": {
            "MyPlugin\\": "src/"
        }
    },
    "autoload-dev": {
        "psr-4": {
            "MyPlugin\\Tests\\": "tests/"
        }
    }
}

// Directory structure:
// my-plugin/
// ├── src/
// │   ├── Admin/
// │   │   ├── Settings.php
// │   │   └── Menu.php
// │   ├── Frontend/
// │   │   └── Display.php
// │   ├── Handlers/
// │   │   ├── PostHandler.php
// │   │   └── UserHandler.php
// │   └── Plugin.php
// ├── vendor/
// ├── composer.json
// └── my-plugin.php

// my-plugin.php
<?php
/**
 * Plugin Name: My Plugin
 */

defined( 'ABSPATH' ) || exit;

// Load Composer autoloader
if ( file_exists( __DIR__ . '/vendor/autoload.php' ) ) {
    require_once __DIR__ . '/vendor/autoload.php';
}

// Initialize plugin
function my_plugin_init() {
    return \MyPlugin\Plugin::instance();
}
add_action( 'plugins_loaded', 'my_plugin_init' );

// src/Plugin.php
namespace MyPlugin;

class Plugin {
    private static $instance = null;

    public static function instance() {
        if ( null === self::$instance ) {
            self::$instance = new self();
        }
        return self::$instance;
    }

    private function __construct() {
        $this->init_hooks();
    }

    private function init_hooks() {
        // Classes are autoloaded only when instantiated
        if ( is_admin() ) {
            new Admin\Settings();
            new Admin\Menu();
        }

        // Only loaded if this code path is reached
        add_action( 'save_post', function( $post_id ) {
            $handler = new Handlers\PostHandler();
            $handler->process( $post_id );
        });
    }
}

// Without Composer - custom autoloader
spl_autoload_register( function( $class ) {
    $namespace = 'MyPlugin\\';

    if ( strpos( $class, $namespace ) !== 0 ) {
        return;
    }

    $relative = substr( $class, strlen( $namespace ) );
    $path = plugin_dir_path( __FILE__ ) . 'src/' . str_replace( '\\', '/', $relative ) . '.php';

    if ( file_exists( $path ) ) {
        require_once $path;
    }
});
```

Reference: [PSR-4 Autoloading](https://www.php-fig.org/psr/psr-4/)
