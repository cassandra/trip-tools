/*
 * Trip Tools Chrome Extension - Auth Module
 * Handles API token storage, validation, and auth state management.
 * Security: Never logs token values, only presence/absence.
 */

var TTAuth = TTAuth || {};

/**
 * Get the stored API token.
 * @returns {Promise<string|null>} The token or null if not set.
 */
TTAuth.getApiToken = function() {
    return TTStorage.get( TT.STORAGE.KEY_API_TOKEN, null );
};

/**
 * Store the API token.
 * @param {string} token - The API token to store.
 * @returns {Promise<void>}
 */
TTAuth.setApiToken = function( token ) {
    return TTStorage.set( TT.STORAGE.KEY_API_TOKEN, token );
};

/**
 * Clear the stored API token.
 * @returns {Promise<void>}
 */
TTAuth.clearApiToken = function() {
    return TTStorage.remove( TT.STORAGE.KEY_API_TOKEN );
};

/**
 * Get the stored user UUID.
 * @returns {Promise<string|null>} The UUID or null if not set.
 */
TTAuth.getUserUuid = function() {
    return TTStorage.get( TT.STORAGE.KEY_USER_UUID, null );
};

/**
 * Store the user UUID.
 * @param {string} uuid - The user UUID to store.
 * @returns {Promise<void>}
 */
TTAuth.setUserUuid = function( uuid ) {
    return TTStorage.set( TT.STORAGE.KEY_USER_UUID, uuid );
};

/**
 * Clear the stored user UUID.
 * @returns {Promise<void>}
 */
TTAuth.clearUserUuid = function() {
    return TTStorage.remove( TT.STORAGE.KEY_USER_UUID );
};

/**
 * Get the current auth state.
 * @returns {Promise<string>} One of TT.AUTH.STATE_* values.
 */
TTAuth.getAuthState = function() {
    return TTStorage.get( TT.STORAGE.KEY_AUTH_STATE, TT.AUTH.STATE_NOT_AUTHORIZED );
};

/**
 * Set the auth state.
 * @param {string} state - One of TT.AUTH.STATE_* values.
 * @returns {Promise<void>}
 */
TTAuth.setAuthState = function( state ) {
    return TTStorage.set( TT.STORAGE.KEY_AUTH_STATE, state );
};

/**
 * Check if the extension is currently authorized.
 * @returns {Promise<boolean>}
 */
TTAuth.isAuthorized = function() {
    return TTAuth.getAuthState()
        .then( function( state ) {
            return state === TT.AUTH.STATE_AUTHORIZED;
        });
};

/**
 * Disconnect: clear token, UUID, and set state to not authorized.
 * Token remains valid on server - only cleared locally.
 * @returns {Promise<void>}
 */
TTAuth.disconnect = function() {
    return Promise.all([
        TTAuth.clearApiToken(),
        TTAuth.clearUserUuid(),
        TTAuth.setAuthState( TT.AUTH.STATE_NOT_AUTHORIZED )
    ]);
};

/**
 * Get platform information for token naming.
 * Delegates to TTPlatform module.
 * @returns {Object} Platform info with os and browser properties.
 */
TTAuth.getPlatformInfo = function() {
    return TTPlatform.getInfo();
};

/**
 * Check if a token string has valid format.
 * @param {string} token - The token to validate.
 * @returns {boolean} True if format is valid.
 */
TTAuth.isValidTokenFormat = function( token ) {
    if ( !token || typeof token !== 'string' ) {
        return false;
    }
    // Token format: tt_{lookup_key}_{secret_key}
    // lookup_key is 8 hex chars, secret_key is ~40 URL-safe chars (may contain underscores)
    // Split with limit 3 to handle underscores in secret_key
    var parts = token.split( '_', 3 );
    return parts.length === 3 && parts[0] === 'tt' && parts[1].length === 8 && parts[2].length > 0;
};

/**
 * Get a debug-safe representation of token presence.
 * Never returns the actual token value.
 * @param {string|null} token - The token (or null).
 * @returns {string} Debug-safe string.
 */
TTAuth.getTokenDebugInfo = function( token ) {
    if ( token && TTAuth.isValidTokenFormat( token ) ) {
        return TT.STRINGS.DEBUG_TOKEN_PRESENT;
    }
    return TT.STRINGS.DEBUG_TOKEN_ABSENT;
};

/**
 * Extract the lookup_key from a token string.
 * @param {string} token - The full token string (tt_{lookup_key}_{secret_key}).
 * @returns {string|null} The lookup_key or null if invalid format.
 */
TTAuth.getLookupKey = function( token ) {
    if ( !TTAuth.isValidTokenFormat( token ) ) {
        return null;
    }
    var parts = token.split( '_', 3 );
    return parts[1];
};

/**
 * Open the authorization page in a new tab.
 * Routes through signin with next/from params for proper UX flow.
 * - If user is already logged in, they redirect straight to extensions page.
 * - If not logged in, they see signin with extension context message.
 * @returns {Promise<void>}
 */
TTAuth.openAuthorizePage = function() {
    var defaultUrl = TT.CONFIG.IS_DEVELOPMENT
        ? TT.CONFIG.DEFAULT_SERVER_URL_DEV
        : TT.CONFIG.DEFAULT_SERVER_URL_PROD;

    return TTStorage.get( TT.STORAGE.KEY_SERVER_URL, defaultUrl )
        .then( function( serverUrl ) {
            var signinUrl = serverUrl + '/user/signin';
            var params = new URLSearchParams({
                next: TT.CONFIG.EXTENSION_AUTHORIZE_PATH,
                from: 'extension'
            });
            chrome.tabs.create( { url: signinUrl + '?' + params.toString() } );
        });
};
