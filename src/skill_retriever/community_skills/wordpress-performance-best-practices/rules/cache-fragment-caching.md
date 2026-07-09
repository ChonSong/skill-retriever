---
title: Use Fragment Caching for Expensive Template Parts
impact: HIGH
impactDescription: Reduces template rendering time by 50-90%
tags: caching, templates, fragments, performance
---

## Use Fragment Caching for Expensive Template Parts

Cache expensive template fragments (widgets, complex loops, sidebars) separately from full-page caching. This allows dynamic pages to still benefit from caching static portions. Fragment caching is especially useful for logged-in users where page caching isn't possible.

**Incorrect (regenerating expensive content on every request):**

```php
// Sidebar regenerated on every page load
function render_popular_posts_widget() {
    $posts = new WP_Query([
        'post_type'      => 'post',
        'posts_per_page' => 5,
        'meta_key'       => 'views',
        'orderby'        => 'meta_value_num',
        'order'          => 'DESC',
    ]);

    ob_start();
    while ( $posts->have_posts() ) {
        $posts->the_post();
        // Complex template rendering
        get_template_part( 'partials/popular-post' );
    }
    wp_reset_postdata();
    return ob_get_clean();
}

// Navigation menu regenerated on every page
wp_nav_menu(['theme_location' => 'primary']);
```

**Correct (fragment caching):**

```php
// Cache expensive widget output
function render_popular_posts_widget() {
    $cache_key = 'popular_posts_widget';
    $output = wp_cache_get( $cache_key, 'widget_fragments' );

    if ( false === $output ) {
        $posts = new WP_Query([
            'post_type'      => 'post',
            'posts_per_page' => 5,
            'meta_key'       => 'views',
            'orderby'        => 'meta_value_num',
            'order'          => 'DESC',
        ]);

        ob_start();
        while ( $posts->have_posts() ) {
            $posts->the_post();
            get_template_part( 'partials/popular-post' );
        }
        wp_reset_postdata();
        $output = ob_get_clean();

        wp_cache_set( $cache_key, $output, 'widget_fragments', HOUR_IN_SECONDS );
    }

    return $output;
}

// Invalidate when posts are updated
add_action( 'save_post', function() {
    wp_cache_delete( 'popular_posts_widget', 'widget_fragments' );
});

// Reusable fragment caching helper
function cached_fragment( $key, $callback, $expiration = 3600, $group = 'fragments' ) {
    $output = wp_cache_get( $key, $group );

    if ( false === $output ) {
        ob_start();
        $callback();
        $output = ob_get_clean();
        wp_cache_set( $key, $output, $group, $expiration );
    }

    return $output;
}

// Usage in templates
echo cached_fragment( 'sidebar_popular', function() {
    get_template_part( 'partials/popular-posts' );
}, HOUR_IN_SECONDS );

// Cache navigation menus
function get_cached_nav_menu( $location, $args = [] ) {
    $cache_key = 'nav_menu_' . $location;
    $menu = wp_cache_get( $cache_key, 'nav_fragments' );

    if ( false === $menu ) {
        $menu = wp_nav_menu( array_merge( $args, [
            'theme_location' => $location,
            'echo'           => false,
        ]));
        wp_cache_set( $cache_key, $menu, 'nav_fragments', DAY_IN_SECONDS );
    }

    return $menu;
}

// Invalidate menu cache when menus change
add_action( 'wp_update_nav_menu', function() {
    wp_cache_delete( 'nav_menu_primary', 'nav_fragments' );
    wp_cache_delete( 'nav_menu_footer', 'nav_fragments' );
});

// User-specific fragment caching
function get_user_dashboard_fragment( $user_id ) {
    $cache_key = 'dashboard_' . $user_id;
    $fragment = wp_cache_get( $cache_key, 'user_fragments' );

    if ( false === $fragment ) {
        ob_start();
        // Render user-specific dashboard
        include 'partials/user-dashboard.php';
        $fragment = ob_get_clean();
        wp_cache_set( $cache_key, $fragment, 'user_fragments', 15 * MINUTE_IN_SECONDS );
    }

    return $fragment;
}
```

Reference: [10up Fragment Caching](https://10up.github.io/Engineering-Best-Practices/php/#caching)
