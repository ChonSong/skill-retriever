---
title: Use Activation and Deactivation Hooks Properly
impact: MEDIUM
impactDescription: Prevents unnecessary setup on every page load
tags: plugin, activation, hooks, setup
---

## Use Activation and Deactivation Hooks Properly

Use activation hooks for one-time setup tasks like creating database tables, setting default options, and scheduling cron jobs. Don't perform these tasks on every page load. Use deactivation hooks to clean up scheduled events.

**Incorrect (setup on every load):**

```php
// Runs on every request - wasteful
function my_plugin_init() {
    global $wpdb;

    // Bad: checking/creating table on every load
    $table_name = $wpdb->prefix . 'my_plugin_data';
    $wpdb->query( "CREATE TABLE IF NOT EXISTS $table_name ..." );

    // Bad: setting options on every load
    if ( ! get_option( 'my_plugin_version' ) ) {
        update_option( 'my_plugin_version', '1.0.0' );
        update_option( 'my_plugin_settings', ['default' => 'value'] );
    }

    // Bad: scheduling cron on every load
    if ( ! wp_next_scheduled( 'my_plugin_cron' ) ) {
        wp_schedule_event( time(), 'hourly', 'my_plugin_cron' );
    }
}
add_action( 'init', 'my_plugin_init' );
```

**Correct (activation/deactivation hooks):**

```php
// Activation hook - runs once when plugin is activated
register_activation_hook( __FILE__, 'my_plugin_activate' );

function my_plugin_activate() {
    // Create database tables
    my_plugin_create_tables();

    // Set default options
    my_plugin_set_defaults();

    // Schedule cron events
    my_plugin_schedule_events();

    // Flush rewrite rules if plugin adds custom post types/taxonomies
    flush_rewrite_rules();

    // Store version for upgrade routines
    update_option( 'my_plugin_version', MY_PLUGIN_VERSION );
}

function my_plugin_create_tables() {
    global $wpdb;
    $charset_collate = $wpdb->get_charset_collate();

    $table_name = $wpdb->prefix . 'my_plugin_data';

    $sql = "CREATE TABLE $table_name (
        id bigint(20) unsigned NOT NULL AUTO_INCREMENT,
        user_id bigint(20) unsigned NOT NULL,
        data longtext NOT NULL,
        created_at datetime DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY  (id),
        KEY user_id (user_id)
    ) $charset_collate;";

    require_once ABSPATH . 'wp-admin/includes/upgrade.php';
    dbDelta( $sql );
}

function my_plugin_set_defaults() {
    $defaults = [
        'enabled'     => true,
        'cache_time'  => 3600,
        'max_items'   => 100,
    ];

    // Only set if not already set (preserves user settings on reactivation)
    if ( false === get_option( 'my_plugin_settings' ) ) {
        add_option( 'my_plugin_settings', $defaults );
    }
}

function my_plugin_schedule_events() {
    if ( ! wp_next_scheduled( 'my_plugin_daily_cleanup' ) ) {
        wp_schedule_event( time(), 'daily', 'my_plugin_daily_cleanup' );
    }
}

// Deactivation hook - cleanup
register_deactivation_hook( __FILE__, 'my_plugin_deactivate' );

function my_plugin_deactivate() {
    // Clear scheduled events
    wp_clear_scheduled_hook( 'my_plugin_daily_cleanup' );

    // Flush rewrite rules
    flush_rewrite_rules();

    // Optionally clear transients
    delete_transient( 'my_plugin_cache' );
}

// Uninstall hook - complete cleanup (use uninstall.php for better practice)
register_uninstall_hook( __FILE__, 'my_plugin_uninstall' );

function my_plugin_uninstall() {
    global $wpdb;

    // Delete options
    delete_option( 'my_plugin_settings' );
    delete_option( 'my_plugin_version' );

    // Delete custom tables
    $wpdb->query( "DROP TABLE IF EXISTS {$wpdb->prefix}my_plugin_data" );

    // Delete user meta
    $wpdb->query( "DELETE FROM {$wpdb->usermeta} WHERE meta_key LIKE 'my_plugin_%'" );
}

// Version-based upgrade routine
function my_plugin_maybe_upgrade() {
    $current = get_option( 'my_plugin_version', '0' );

    if ( version_compare( $current, MY_PLUGIN_VERSION, '<' ) ) {
        my_plugin_upgrade( $current );
        update_option( 'my_plugin_version', MY_PLUGIN_VERSION );
    }
}
add_action( 'plugins_loaded', 'my_plugin_maybe_upgrade' );
```

Reference: [Plugin Activation Hooks](https://developer.wordpress.org/plugins/plugin-basics/activation-deactivation-hooks/)
