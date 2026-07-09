---
title: Manage Memory Usage Effectively
impact: LOW-MEDIUM
impactDescription: Prevents memory exhaustion on resource-intensive operations
tags: advanced, memory, optimization, batch-processing
---

## Manage Memory Usage Effectively

Large operations can exhaust PHP's memory limit. Monitor memory usage, process data in batches, and clean up resources when done. This is especially important for imports, exports, and batch operations.

**Incorrect (memory-intensive operations):**

```php
// Loading all posts into memory
$all_posts = get_posts(['numberposts' => -1]);
foreach ( $all_posts as $post ) {
    process_post( $post );
}

// Accumulating data without cleanup
$results = [];
foreach ( $huge_dataset as $item ) {
    $results[] = expensive_operation( $item ); // Memory grows unbounded
}

// Not releasing references
function process_large_file( $file ) {
    $content = file_get_contents( $file ); // Could be 100MB
    $processed = transform( $content );
    save_result( $processed );
    // $content and $processed still in memory until function ends
}
```

**Correct (memory-efficient operations):**

```php
// Process in batches with memory cleanup
function process_all_posts_efficiently() {
    $batch_size = 100;
    $offset = 0;

    // Increase memory limit for batch operations if needed
    wp_raise_memory_limit( 'admin' );

    do {
        $posts = get_posts([
            'numberposts' => $batch_size,
            'offset'      => $offset,
            'fields'      => 'ids', // Only get IDs
        ]);

        if ( empty( $posts ) ) {
            break;
        }

        foreach ( $posts as $post_id ) {
            process_post( $post_id );
        }

        $offset += $batch_size;

        // Clear caches to free memory
        wp_cache_flush();

        // Clear static caches in WP core functions
        clean_post_cache( $posts );

        // Log memory usage
        if ( defined( 'WP_DEBUG' ) && WP_DEBUG ) {
            error_log( 'Memory usage: ' . memory_get_usage( true ) / 1024 / 1024 . ' MB' );
        }

    } while ( count( $posts ) === $batch_size );
}

// Generator pattern for memory-efficient iteration
function get_posts_generator( $args = [] ) {
    $defaults = [
        'posts_per_page' => 100,
        'paged'          => 1,
        'fields'         => 'ids',
    ];
    $args = wp_parse_args( $args, $defaults );

    do {
        $query = new WP_Query( $args );

        foreach ( $query->posts as $post_id ) {
            yield $post_id;
        }

        $args['paged']++;

        // Free memory
        wp_cache_flush();

    } while ( $query->have_posts() );
}

// Usage
foreach ( get_posts_generator(['post_type' => 'product']) as $product_id ) {
    update_product( $product_id );
}

// Process large file in chunks
function process_large_file_efficiently( $file ) {
    $handle = fopen( $file, 'r' );

    if ( ! $handle ) {
        return false;
    }

    $chunk_size = 8192; // 8KB chunks

    while ( ! feof( $handle ) ) {
        $chunk = fread( $handle, $chunk_size );
        process_chunk( $chunk );
        unset( $chunk ); // Explicitly free memory
    }

    fclose( $handle );
}

// Monitor memory usage
function check_memory_usage() {
    $limit = ini_get( 'memory_limit' );
    $limit_bytes = wp_convert_hr_to_bytes( $limit );
    $usage = memory_get_usage( true );
    $percentage = ( $usage / $limit_bytes ) * 100;

    if ( $percentage > 80 ) {
        error_log( sprintf(
            'High memory usage: %d%% (%s of %s)',
            $percentage,
            size_format( $usage ),
            $limit
        ));
    }

    return [
        'limit'      => $limit_bytes,
        'usage'      => $usage,
        'percentage' => $percentage,
    ];
}

// Cleanup helper for batch operations
function batch_cleanup() {
    global $wpdb, $wp_object_cache;

    // Clear query log
    $wpdb->queries = [];

    // Clear object cache
    if ( is_object( $wp_object_cache ) ) {
        $wp_object_cache->flush();
    }

    // Clear WP_Query static cache
    wp_reset_query();

    // Force garbage collection (PHP 5.3+)
    if ( function_exists( 'gc_collect_cycles' ) ) {
        gc_collect_cycles();
    }
}

// WP-CLI command with memory management
if ( defined( 'WP_CLI' ) && WP_CLI ) {
    WP_CLI::add_command( 'my-process', function( $args ) {
        $count = 0;

        foreach ( get_posts_generator(['post_type' => 'post']) as $post_id ) {
            process_post( $post_id );
            $count++;

            if ( $count % 100 === 0 ) {
                WP_CLI::log( "Processed {$count} posts, memory: " . size_format( memory_get_usage( true ) ) );
                batch_cleanup();
            }
        }

        WP_CLI::success( "Processed {$count} posts" );
    });
}
```

Reference: [Memory Limit](https://developer.wordpress.org/reference/functions/wp_raise_memory_limit/)
