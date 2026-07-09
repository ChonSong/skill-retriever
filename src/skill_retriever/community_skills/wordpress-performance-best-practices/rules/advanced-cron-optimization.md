---
title: Optimize WP-Cron Usage
impact: LOW-MEDIUM
impactDescription: Prevents cron from blocking page loads
tags: advanced, cron, scheduling, background
---

## Optimize WP-Cron Usage

WP-Cron runs on page loads, which can slow down user requests. For high-traffic sites, disable WP-Cron's page-load trigger and use system cron instead. Schedule events wisely and clean up unused scheduled events.

**Incorrect (problematic cron usage):**

```php
// Scheduling on every page load (if not scheduled)
function maybe_schedule_my_event() {
    if ( ! wp_next_scheduled( 'my_hourly_event' ) ) {
        wp_schedule_event( time(), 'hourly', 'my_hourly_event' );
    }
}
add_action( 'init', 'maybe_schedule_my_event' ); // Runs every page load!

// Long-running cron task blocks page load
add_action( 'my_sync_event', function() {
    // Syncs 10,000 products - takes 30 seconds
    $products = fetch_all_products_from_api();
    foreach ( $products as $product ) {
        update_product( $product );
    }
});

// Not cleaning up events on deactivation
// Events keep running after plugin is disabled!

// Using too-frequent intervals
wp_schedule_event( time(), 'every_minute', 'my_frequent_task' );
```

**Correct (optimized cron handling):**

```php
// Schedule events during activation, not init
register_activation_hook( __FILE__, function() {
    if ( ! wp_next_scheduled( 'my_plugin_daily_task' ) ) {
        wp_schedule_event( time(), 'daily', 'my_plugin_daily_task' );
    }
});

// Clear events on deactivation
register_deactivation_hook( __FILE__, function() {
    wp_clear_scheduled_hook( 'my_plugin_daily_task' );
    wp_clear_scheduled_hook( 'my_plugin_hourly_task' );
});

// Batch processing for long-running tasks
add_action( 'my_sync_event', function() {
    $offset = get_option( 'my_sync_offset', 0 );
    $batch_size = 100;

    $products = fetch_products_from_api( $batch_size, $offset );

    if ( empty( $products ) ) {
        // Done - reset for next run
        delete_option( 'my_sync_offset' );
        return;
    }

    foreach ( $products as $product ) {
        update_product( $product );
    }

    // Update offset for next batch
    update_option( 'my_sync_offset', $offset + $batch_size );

    // Schedule next batch immediately
    wp_schedule_single_event( time() + 1, 'my_sync_event' );
});

// Use system cron for high-traffic sites
// In wp-config.php:
define( 'DISABLE_WP_CRON', true );

// Then set up system cron:
// */5 * * * * wget -q -O - https://example.com/wp-cron.php?doing_wp_cron >/dev/null 2>&1
// or
// */5 * * * * cd /path/to/wordpress && php wp-cron.php >/dev/null 2>&1

// Custom cron intervals
add_filter( 'cron_schedules', function( $schedules ) {
    $schedules['every_five_minutes'] = [
        'interval' => 5 * MINUTE_IN_SECONDS,
        'display'  => __( 'Every Five Minutes' ),
    ];
    $schedules['twice_daily'] = [
        'interval' => 12 * HOUR_IN_SECONDS,
        'display'  => __( 'Twice Daily' ),
    ];
    return $schedules;
});

// Check cron health (admin diagnostic)
function check_cron_health() {
    $crons = _get_cron_array();
    $issues = [];

    // Check for too many scheduled events
    $total_events = 0;
    foreach ( $crons as $time => $hooks ) {
        $total_events += count( $hooks );
    }

    if ( $total_events > 50 ) {
        $issues[] = "Too many cron events: {$total_events}";
    }

    // Check for orphaned events (hooks without handlers)
    foreach ( $crons as $time => $hooks ) {
        foreach ( $hooks as $hook => $events ) {
            if ( ! has_action( $hook ) ) {
                $issues[] = "Orphaned cron hook: {$hook}";
            }
        }
    }

    // Check if cron is running
    $last_run = get_option( 'my_plugin_cron_last_run', 0 );
    if ( $last_run && ( time() - $last_run ) > DAY_IN_SECONDS ) {
        $issues[] = 'Cron appears to not be running';
    }

    return $issues;
}

// Track cron execution
add_action( 'my_plugin_daily_task', function() {
    update_option( 'my_plugin_cron_last_run', time() );
    // ... do task
}, 1 ); // Early priority to track execution
```

Reference: [WP-Cron](https://developer.wordpress.org/plugins/cron/)
