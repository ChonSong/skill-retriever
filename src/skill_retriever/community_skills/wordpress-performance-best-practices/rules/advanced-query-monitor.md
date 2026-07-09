---
title: Profile and Monitor Performance
impact: LOW-MEDIUM
impactDescription: Enables identification of actual bottlenecks
tags: advanced, profiling, debugging, query-monitor
---

## Profile and Monitor Performance

Use profiling tools to identify actual performance bottlenecks rather than optimizing blindly. Query Monitor, Debug Bar, and New Relic help pinpoint slow queries, excessive hooks, and memory issues. Profile in production-like environments.

**Incorrect (blind optimization):**

```php
// Optimizing without measuring
// "I think this is slow, so I'll add caching everywhere"
function get_data() {
    $cached = wp_cache_get( 'my_data' );
    if ( ! $cached ) {
        $cached = 'simple string'; // Caching a simple operation!
        wp_cache_set( 'my_data', $cached );
    }
    return $cached;
}

// Assuming the problem without profiling
// "WordPress is slow, must be the database"
// Actually: it's a plugin loading 50 external scripts
```

**Correct (data-driven optimization):**

```php
// Built-in query logging (development only)
define( 'SAVEQUERIES', true );

// Display query log (in footer or debug panel)
function show_query_log() {
    if ( ! current_user_can( 'manage_options' ) || ! defined( 'SAVEQUERIES' ) ) {
        return;
    }

    global $wpdb;

    $total_time = 0;
    $slow_queries = [];

    foreach ( $wpdb->queries as $query ) {
        $total_time += $query[1];
        if ( $query[1] > 0.05 ) { // Queries over 50ms
            $slow_queries[] = $query;
        }
    }

    echo '<!-- Queries: ' . count( $wpdb->queries ) . ', Time: ' . round( $total_time, 4 ) . 's -->';

    if ( ! empty( $slow_queries ) ) {
        echo '<!-- Slow queries: -->';
        foreach ( $slow_queries as $q ) {
            echo '<!-- ' . esc_html( $q[0] ) . ' (' . round( $q[1] * 1000 ) . 'ms) -->';
        }
    }
}
add_action( 'wp_footer', 'show_query_log', 9999 );

// Custom timing for specific operations
function measure_execution( $callback, $label = 'Operation' ) {
    $start_time = microtime( true );
    $start_memory = memory_get_usage();
    $start_queries = get_num_queries();

    $result = $callback();

    $time = microtime( true ) - $start_time;
    $memory = memory_get_usage() - $start_memory;
    $queries = get_num_queries() - $start_queries;

    if ( defined( 'WP_DEBUG' ) && WP_DEBUG ) {
        error_log( sprintf(
            '%s: %.4fs, %s memory, %d queries',
            $label,
            $time,
            size_format( $memory ),
            $queries
        ));
    }

    return $result;
}

// Usage
$posts = measure_execution( function() {
    return get_posts(['numberposts' => 100]);
}, 'Get posts' );

// Hook timing
class Hook_Timer {
    private static $timings = [];

    public static function start( $hook ) {
        self::$timings[ $hook ] = [
            'start' => microtime( true ),
            'callbacks' => [],
        ];
    }

    public static function end( $hook ) {
        if ( isset( self::$timings[ $hook ] ) ) {
            self::$timings[ $hook ]['total'] = microtime( true ) - self::$timings[ $hook ]['start'];
        }
    }

    public static function get_slow_hooks( $threshold = 0.01 ) {
        $slow = [];
        foreach ( self::$timings as $hook => $data ) {
            if ( isset( $data['total'] ) && $data['total'] > $threshold ) {
                $slow[ $hook ] = $data['total'];
            }
        }
        arsort( $slow );
        return $slow;
    }
}

// Track slow hooks
add_action( 'all', function( $hook ) {
    Hook_Timer::start( $hook );
}, 0 );

add_action( 'all', function( $hook ) {
    Hook_Timer::end( $hook );
}, 9999 );

// Server Timing API (visible in browser DevTools)
function add_server_timing_header() {
    global $wpdb;

    $db_time = 0;
    if ( defined( 'SAVEQUERIES' ) && $wpdb->queries ) {
        foreach ( $wpdb->queries as $q ) {
            $db_time += $q[1];
        }
    }

    $total_time = microtime( true ) - $_SERVER['REQUEST_TIME_FLOAT'];

    header( sprintf(
        'Server-Timing: db;dur=%.1f, total;dur=%.1f, queries;desc="%d"',
        $db_time * 1000,
        $total_time * 1000,
        get_num_queries()
    ));
}
add_action( 'send_headers', 'add_server_timing_header' );

// Integrate with Query Monitor plugin
add_filter( 'qm/collectors', function( $collectors ) {
    // Add custom collector
    $collectors['my_plugin'] = new My_Plugin_QM_Collector();
    return $collectors;
});

// Production monitoring - log slow requests
function log_slow_request() {
    $total_time = microtime( true ) - $_SERVER['REQUEST_TIME_FLOAT'];

    if ( $total_time > 2.0 ) { // Over 2 seconds
        error_log( sprintf(
            'Slow request: %s (%.2fs, %d queries, %s memory)',
            $_SERVER['REQUEST_URI'],
            $total_time,
            get_num_queries(),
            size_format( memory_get_peak_usage() )
        ));
    }
}
add_action( 'shutdown', 'log_slow_request' );
```

Reference: [Query Monitor Plugin](https://querymonitor.com/)
