---
title: Optimize Options Autoloading
impact: LOW-MEDIUM
impactDescription: Reduces memory usage and query time on large sites
tags: advanced, options, autoload, database
---

## Optimize Options Autoloading

WordPress loads all autoloaded options on every page request. Excessive autoloaded data (over 800KB) slows down every page load. Set autoload to 'no' for options that aren't needed on every request, and regularly audit autoloaded options.

**Incorrect (autoloading large or rarely-used options):**

```php
// Default autoload is 'yes' - loaded on every request
update_option( 'my_plugin_large_data', $large_array ); // Autoloaded!
update_option( 'my_plugin_logs', $logs ); // Rarely needed, still autoloaded
update_option( 'my_plugin_cache', $cache_data ); // Redundant with object cache

// Adding options without considering autoload
add_option( 'my_plugin_settings', $settings ); // Defaults to autoload=yes

// Storing large serialized data
update_option( 'my_plugin_all_products', serialize( $products ) ); // Could be megabytes!
```

**Correct (strategic autoload management):**

```php
// Only autoload options needed on every page
add_option( 'my_plugin_settings', $settings, '', 'yes' ); // Small, needed everywhere
add_option( 'my_plugin_version', '1.0.0', '', 'yes' ); // Tiny, used for upgrades

// Don't autoload large or rarely-used data
add_option( 'my_plugin_logs', [], '', 'no' ); // Only needed in admin
add_option( 'my_plugin_analytics', [], '', 'no' ); // Fetched on specific pages
add_option( 'my_plugin_license', '', '', 'no' ); // Only needed for validation

// Update existing options to not autoload
function fix_option_autoload() {
    global $wpdb;

    // Set specific options to not autoload
    $options_to_fix = [
        'my_plugin_cache',
        'my_plugin_logs',
        'my_plugin_backup',
    ];

    foreach ( $options_to_fix as $option ) {
        $wpdb->update(
            $wpdb->options,
            ['autoload' => 'no'],
            ['option_name' => $option]
        );
    }
}

// Audit autoloaded options (admin tool)
function get_autoload_stats() {
    global $wpdb;

    $results = $wpdb->get_results(
        "SELECT option_name, LENGTH(option_value) as size
         FROM {$wpdb->options}
         WHERE autoload = 'yes'
         ORDER BY size DESC
         LIMIT 50"
    );

    $total = $wpdb->get_var(
        "SELECT SUM(LENGTH(option_value))
         FROM {$wpdb->options}
         WHERE autoload = 'yes'"
    );

    return [
        'total_bytes' => $total,
        'top_options' => $results,
        'warning'     => $total > 800000, // Warn if over 800KB
    ];
}

// Clean up plugin's autoloaded data on deactivation
register_deactivation_hook( __FILE__, function() {
    global $wpdb;

    // Remove large autoloaded options or set to no
    $wpdb->update(
        $wpdb->options,
        ['autoload' => 'no'],
        ['option_name' => 'my_plugin_cached_data']
    );
});

// Use transients or object cache instead of options for cached data
// Good: transient for cached API data
set_transient( 'my_plugin_api_cache', $data, DAY_IN_SECONDS );

// Good: object cache for frequently accessed data
wp_cache_set( 'my_plugin_data', $data, 'my_plugin', HOUR_IN_SECONDS );

// For truly large data, consider custom tables
function maybe_use_custom_table( $data ) {
    if ( strlen( serialize( $data ) ) > 50000 ) {
        // Store in custom table instead
        store_in_custom_table( $data );
    } else {
        update_option( 'my_data', $data, 'no' );
    }
}

// WordPress 6.6+ supports autoload values: 'on', 'off', 'auto'
// 'auto' lets WordPress decide based on option size
add_option( 'my_option', $value, '', 'auto' );
```

Reference: [Options API](https://developer.wordpress.org/reference/functions/add_option/)
