---
title: Place Hooks at Appropriate Priority Levels
impact: MEDIUM
impactDescription: Ensures proper execution order and avoids conflicts
tags: theme, hooks, actions, filters
---

## Place Hooks at Appropriate Priority Levels

Use appropriate priority levels when adding actions and filters. Lower numbers run first. Understanding hook priority prevents conflicts with plugins and ensures your code runs at the right time.

**Incorrect (ignoring priority or using arbitrary values):**

```php
// All at default priority - order is unpredictable
add_action( 'wp_enqueue_scripts', 'theme_styles' );
add_action( 'wp_enqueue_scripts', 'theme_scripts' );
add_action( 'wp_enqueue_scripts', 'override_plugin_styles' );

// Random priority values
add_filter( 'the_content', 'add_social_buttons', 999999 );

// Trying to run before everything with very low number
add_action( 'init', 'my_early_init', -99999 );
```

**Correct (intentional, documented priorities):**

```php
// Standard priority levels:
// 1-9:    Very early, before most things
// 10:     Default, normal execution
// 11-19:  After defaults, modifications
// 20+:    Late execution, overrides
// 100+:   Very late, final modifications

// Load base styles first, then customizations
add_action( 'wp_enqueue_scripts', 'theme_base_styles', 10 );
add_action( 'wp_enqueue_scripts', 'theme_component_styles', 15 );
add_action( 'wp_enqueue_scripts', 'theme_override_plugin_styles', 20 );

// Dequeue plugin assets after they're enqueued
add_action( 'wp_enqueue_scripts', 'dequeue_unnecessary_assets', 100 );

// Filter content modifications in logical order
add_filter( 'the_content', 'process_shortcodes', 10 );     // Default
add_filter( 'the_content', 'add_related_posts', 15 );      // After shortcodes
add_filter( 'the_content', 'add_social_buttons', 20 );     // After related posts
add_filter( 'the_content', 'wrap_content_sections', 25 );  // Final wrapping

// Document why you're using non-default priorities
/**
 * Override plugin's body classes.
 * Priority 20 ensures this runs after the plugin's filter at default priority.
 */
add_filter( 'body_class', 'override_plugin_body_class', 20 );

// Use early priority for setup tasks
add_action( 'init', 'register_custom_post_types', 5 );  // Before anything uses them
add_action( 'init', 'register_taxonomies', 5 );

// Default priority for normal functionality
add_action( 'init', 'setup_theme_features', 10 );

// Late priority for modifications that depend on other init hooks
add_action( 'init', 'modify_registered_post_types', 15 );

// WordPress standard hook priorities
add_action( 'after_setup_theme', 'theme_setup', 10 );  // Standard
add_action( 'widgets_init', 'register_sidebars', 10 ); // Standard

// Remove then re-add with different priority
remove_action( 'woocommerce_before_main_content', 'woocommerce_output_content_wrapper', 10 );
add_action( 'woocommerce_before_main_content', 'theme_content_wrapper', 10 );

// Helper for consistent priority management
class Theme_Hooks {
    const EARLY    = 5;
    const DEFAULT  = 10;
    const LATE     = 15;
    const OVERRIDE = 20;
    const FINAL    = 100;
}

add_action( 'init', 'register_cpts', Theme_Hooks::EARLY );
add_action( 'init', 'setup_features', Theme_Hooks::DEFAULT );
add_filter( 'the_content', 'final_content_filter', Theme_Hooks::FINAL );
```

Reference: [Plugin API - Actions](https://developer.wordpress.org/plugins/hooks/actions/)
