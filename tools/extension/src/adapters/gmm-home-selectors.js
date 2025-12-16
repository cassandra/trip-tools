/*
 * Google My Maps Home Page DOM Selectors
 * Centralized selector configuration for GMM home page manipulation.
 * Update this file when Google changes their UI.
 *
 * IMPORTANT: Only use stable attributes (role, aria-label).
 * NEVER use obfuscated/auto-generated class names.
 */

var TTGmmHomeSelectors = {
    // Version identifier for tracking UI changes
    VERSION: '2024-12',

    // =========================================================================
    // Map Creation
    // =========================================================================

    // "Create a new map" button - uses stable aria-label
    CREATE_MAP_BUTTON: 'div[role="button"][aria-label="Create a new map"]',

    // =========================================================================
    // Map List (for future "Use Existing Map" feature - Issue #123)
    // =========================================================================

    // Filter tabs (All, Owned, Not owned, Shared, Recent)
    FILTER_TABS: 'div[role="tablist"]',
    FILTER_TAB_ITEM: 'div[role="tab"]',

    // Map list container and items
    MAP_LIST_CONTAINER: 'div[role="listbox"]',
    MAP_LIST_ITEM: 'div[role="option"]',

    // =========================================================================
    // Attribute Names
    // =========================================================================

    ATTR_ARIA_LABEL: 'aria-label',
    ATTR_ARIA_SELECTED: 'aria-selected'
};
