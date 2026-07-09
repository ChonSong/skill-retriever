---
title: Use Transients for Expensive External Operations
impact: CRITICAL
impactDescription: 10-100x reduction in external API calls
tags: caching, transients, api, performance
---

## Use Transients for Expensive External Operations

Transients are ideal for caching expensive external operations like API calls, remote requests, and complex computations. They persist across page loads and work with or without a persistent object cache. Never use transients for data that originates from the WordPress database.

**Incorrect (no caching of external calls):**

```php
// Every page load makes an API call
function get_weather_data( $city ) {
    $response = wp_remote_get( "https://api.weather.com/v1/current?city={$city}" );
    return json_decode( wp_remote_retrieve_body( $response ) );
}

// Caching database data in transients is wasteful
function get_recent_posts_cached() {
    $cached = get_transient( 'recent_posts' );
    if ( $cached ) {
        return $cached;
    }
    // This already uses object cache via WP_Query
    $posts = get_posts(['numberposts' => 10]);
    set_transient( 'recent_posts', $posts, HOUR_IN_SECONDS );
    return $posts;
}

// Missing error handling
function get_api_data() {
    $data = get_transient( 'api_data' );
    if ( ! $data ) {
        $response = wp_remote_get( 'https://api.example.com/data' );
        $data = json_decode( wp_remote_retrieve_body( $response ) );
        set_transient( 'api_data', $data, DAY_IN_SECONDS );
    }
    return $data;
}
```

**Correct (proper transient usage):**

```php
// Cache external API calls with appropriate expiration
function get_weather_data( $city ) {
    $cache_key = 'weather_' . sanitize_key( $city );
    $data = get_transient( $cache_key );

    if ( false !== $data ) {
        return $data;
    }

    $response = wp_remote_get(
        "https://api.weather.com/v1/current?city=" . urlencode( $city ),
        ['timeout' => 10]
    );

    if ( is_wp_error( $response ) ) {
        // Return stale data if available, or false
        return false;
    }

    $data = json_decode( wp_remote_retrieve_body( $response ) );

    if ( $data ) {
        set_transient( $cache_key, $data, HOUR_IN_SECONDS );
    }

    return $data;
}

// Use object cache for database-originated data instead
function get_recent_posts_cached() {
    $cache_key = 'recent_posts_query';
    $posts = wp_cache_get( $cache_key, 'my_plugin' );

    if ( false === $posts ) {
        $posts = get_posts(['numberposts' => 10]);
        wp_cache_set( $cache_key, $posts, 'my_plugin', HOUR_IN_SECONDS );
    }

    return $posts;
}

// Handle API errors gracefully with stale-while-revalidate pattern
function get_api_data_robust() {
    $data = get_transient( 'api_data' );
    $last_fetch = get_transient( 'api_data_timestamp' );

    // Return cached data if fresh enough
    if ( false !== $data && $last_fetch && ( time() - $last_fetch ) < HOUR_IN_SECONDS ) {
        return $data;
    }

    // Attempt to refresh
    $response = wp_remote_get( 'https://api.example.com/data', ['timeout' => 5] );

    if ( ! is_wp_error( $response ) && 200 === wp_remote_retrieve_response_code( $response ) ) {
        $new_data = json_decode( wp_remote_retrieve_body( $response ), true );
        if ( $new_data ) {
            set_transient( 'api_data', $new_data, DAY_IN_SECONDS );
            set_transient( 'api_data_timestamp', time(), DAY_IN_SECONDS );
            return $new_data;
        }
    }

    // Return stale data on failure
    return $data ?: [];
}
```

Reference: [WordPress Transients API](https://developer.wordpress.org/apis/transients/)
