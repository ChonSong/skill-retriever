---
title: Cache Remote HTTP Requests
impact: CRITICAL
impactDescription: Eliminates network latency on repeated requests
tags: caching, http, api, wp_remote_get
---

## Cache Remote HTTP Requests

Always cache responses from `wp_remote_get()`, `wp_remote_post()`, and other HTTP API functions. Remote requests add significant latency (100ms-2s+) and can fail, causing page load delays. Cache successful responses and handle failures gracefully.

**Incorrect (uncached remote requests):**

```php
// Every page load makes HTTP request
function display_github_stars() {
    $response = wp_remote_get( 'https://api.github.com/repos/wordpress/wordpress' );
    $data = json_decode( wp_remote_retrieve_body( $response ) );
    return $data->stargazers_count ?? 0;
}

// No timeout set - can hang for 30+ seconds
$response = wp_remote_get( 'https://slow-api.example.com/data' );

// No error handling
function get_remote_data() {
    $response = wp_remote_get( 'https://api.example.com/data' );
    return json_decode( wp_remote_retrieve_body( $response ) );
}
```

**Correct (properly cached with error handling):**

```php
// Cache remote requests with transients
function get_github_stars( $repo ) {
    $cache_key = 'github_stars_' . sanitize_key( $repo );
    $stars = get_transient( $cache_key );

    if ( false !== $stars ) {
        return $stars;
    }

    $response = wp_remote_get(
        "https://api.github.com/repos/{$repo}",
        [
            'timeout' => 10,
            'headers' => [
                'Accept' => 'application/vnd.github.v3+json',
            ],
        ]
    );

    if ( is_wp_error( $response ) ) {
        // Log error and return cached/default value
        error_log( 'GitHub API error: ' . $response->get_error_message() );
        return get_option( "github_stars_{$repo}_fallback", 0 );
    }

    $code = wp_remote_retrieve_response_code( $response );
    if ( 200 !== $code ) {
        error_log( "GitHub API returned status {$code}" );
        return get_option( "github_stars_{$repo}_fallback", 0 );
    }

    $data = json_decode( wp_remote_retrieve_body( $response ) );
    $stars = $data->stargazers_count ?? 0;

    // Cache for 1 hour, store fallback for longer
    set_transient( $cache_key, $stars, HOUR_IN_SECONDS );
    update_option( "github_stars_{$repo}_fallback", $stars );

    return $stars;
}

// Background refresh pattern for critical data
function get_critical_api_data() {
    $cache_key = 'critical_api_data';
    $data = get_transient( $cache_key );

    if ( false !== $data ) {
        // Schedule background refresh if cache is getting stale
        $age = get_transient( $cache_key . '_time' );
        if ( $age && ( time() - $age ) > ( HOUR_IN_SECONDS / 2 ) ) {
            wp_schedule_single_event( time(), 'refresh_critical_api_data' );
        }
        return $data;
    }

    // Synchronous fetch if no cache
    return fetch_and_cache_api_data();
}

add_action( 'refresh_critical_api_data', 'fetch_and_cache_api_data' );

function fetch_and_cache_api_data() {
    $response = wp_remote_get( 'https://api.example.com/critical', ['timeout' => 15] );

    if ( ! is_wp_error( $response ) && 200 === wp_remote_retrieve_response_code( $response ) ) {
        $data = json_decode( wp_remote_retrieve_body( $response ), true );
        set_transient( 'critical_api_data', $data, 2 * HOUR_IN_SECONDS );
        set_transient( 'critical_api_data_time', time(), 2 * HOUR_IN_SECONDS );
        return $data;
    }

    return get_transient( 'critical_api_data' ) ?: [];
}
```

Reference: [WordPress HTTP API](https://developer.wordpress.org/plugins/http-api/)
