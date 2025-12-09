/*
 * Trip Tools Chrome Extension - Client Config Module
 * Manages client configuration synced from the server.
 * Includes location categories/subcategories.
 * Depends on: constants.js, storage.js, api.js
 */

var TTClientConfig = TTClientConfig || {};

// =============================================================================
// Storage Access
// =============================================================================

/**
 * Get the cached client config from storage.
 * @returns {Promise<Object|null>} Config object or null if not cached.
 */
TTClientConfig.getConfig = function() {
    return TTStorage.get( TT.STORAGE.KEY_CLIENT_CONFIG, null );
};

/**
 * Store the client config.
 * @param {Object} config - Config object with version and location_categories.
 * @returns {Promise<void>}
 */
TTClientConfig.setConfig = function( config ) {
    return TTStorage.set( TT.STORAGE.KEY_CLIENT_CONFIG, config );
};

/**
 * Get the cached config version.
 * @returns {Promise<string|null>} Version hash or null if not cached.
 */
TTClientConfig.getVersion = function() {
    return TTStorage.get( TT.STORAGE.KEY_CLIENT_CONFIG_VERSION, null );
};

/**
 * Store the config version.
 * @param {string} version - Version hash string.
 * @returns {Promise<void>}
 */
TTClientConfig.setVersion = function( version ) {
    return TTStorage.set( TT.STORAGE.KEY_CLIENT_CONFIG_VERSION, version );
};

/**
 * Check if config is marked as stale.
 * @returns {Promise<boolean>} True if stale.
 */
TTClientConfig.isStale = function() {
    return TTStorage.get( TT.STORAGE.KEY_CLIENT_CONFIG_STALE, false );
};

/**
 * Mark config as stale (needs refresh).
 * @returns {Promise<void>}
 */
TTClientConfig.markStale = function() {
    return TTStorage.set( TT.STORAGE.KEY_CLIENT_CONFIG_STALE, true );
};

/**
 * Clear stale flag.
 * @returns {Promise<void>}
 */
TTClientConfig.clearStale = function() {
    return TTStorage.remove( TT.STORAGE.KEY_CLIENT_CONFIG_STALE );
};

// =============================================================================
// Server Interaction
// =============================================================================

/**
 * Fetch client config from the server.
 * @returns {Promise<Object>} Config object with version and location_categories.
 */
TTClientConfig.fetchFromServer = function() {
    return TTApi.get( TT.CONFIG.API_CLIENT_CONFIG_ENDPOINT )
        .then( function( response ) {
            return TTApi.processResponse( response );
        });
};

/**
 * Refresh config from server and update local cache.
 * Clears stale flag on success.
 * @returns {Promise<Object>} The fetched config.
 */
TTClientConfig.refresh = function() {
    return TTClientConfig.fetchFromServer()
        .then( function( config ) {
            return Promise.all([
                TTClientConfig.setConfig( config ),
                TTClientConfig.setVersion( config.version ),
                TTClientConfig.clearStale()
            ]).then( function() {
                return config;
            });
        });
};

/**
 * Refresh config if marked as stale.
 * @returns {Promise<Object|null>} The config (possibly refreshed) or null.
 */
TTClientConfig.refreshIfStale = function() {
    return TTClientConfig.isStale()
        .then( function( stale ) {
            if ( stale ) {
                return TTClientConfig.refresh();
            }
            return TTClientConfig.getConfig();
        });
};

// =============================================================================
// Version Sync
// =============================================================================

/**
 * Handle version from extension status response.
 * Compares server version with cached version. If different, marks config as stale
 * and stores the new version for display purposes.
 * @param {string} serverVersion - Version hash from server.
 * @returns {Promise<void>}
 */
TTClientConfig.handleVersionSync = function( serverVersion ) {
    if ( !serverVersion ) {
        return Promise.resolve();
    }

    return TTClientConfig.getVersion()
        .then( function( cachedVersion ) {
            if ( cachedVersion !== serverVersion ) {
                // Version changed - mark stale and store new version
                return Promise.all([
                    TTClientConfig.markStale(),
                    TTClientConfig.setVersion( serverVersion )
                ]);
            }
        });
};

// =============================================================================
// Location Category Helpers
// =============================================================================

/**
 * Get all location categories.
 * Refreshes if stale before returning.
 * @returns {Promise<Array>} Array of category objects.
 */
TTClientConfig.getLocationCategories = function() {
    return TTClientConfig.refreshIfStale()
        .then( function( config ) {
            if ( config && config.location_categories ) {
                return config.location_categories;
            }
            return [];
        });
};

/**
 * Get a category by slug.
 * @param {string} slug - Category slug.
 * @returns {Promise<Object|null>} Category object or null.
 */
TTClientConfig.getCategoryBySlug = function( slug ) {
    return TTClientConfig.getLocationCategories()
        .then( function( categories ) {
            return categories.find( function( c ) {
                return c.slug === slug;
            }) || null;
        });
};

/**
 * Get a subcategory by slug.
 * Searches across all categories.
 * @param {string} slug - Subcategory slug.
 * @returns {Promise<Object|null>} Subcategory object or null.
 */
TTClientConfig.getSubcategoryBySlug = function( slug ) {
    return TTClientConfig.getLocationCategories()
        .then( function( categories ) {
            for ( var i = 0; i < categories.length; i++ ) {
                var category = categories[i];
                var subcategories = category.subcategories || [];
                var found = subcategories.find( function( s ) {
                    return s.slug === slug;
                });
                if ( found ) {
                    return found;
                }
            }
            return null;
        });
};

// =============================================================================
// Cleanup
// =============================================================================

/**
 * Clear all client config state.
 * Used when disconnecting from the server.
 * @returns {Promise<void>}
 */
TTClientConfig.clearAll = function() {
    return Promise.all([
        TTStorage.remove( TT.STORAGE.KEY_CLIENT_CONFIG ),
        TTStorage.remove( TT.STORAGE.KEY_CLIENT_CONFIG_VERSION ),
        TTStorage.remove( TT.STORAGE.KEY_CLIENT_CONFIG_STALE )
    ]);
};
