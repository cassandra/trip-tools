/*
 * Trip Tools Chrome Extension - State Content Script
 * Adds CSS classes to the page body indicating extension state.
 * Runs on all triptools.net pages to enable state-aware UI.
 *
 * Classes added to <body> (defined in TT.SERVER_SYNC):
 *   tt-ext-authorized       - Extension is installed, authorized, server and account match
 *   tt-ext-not-authorized   - Extension is installed but not authorized
 *   tt-ext-server-mismatch  - Extension is configured for a different server
 *   tt-ext-account-mismatch - Extension is authorized to a different account
 *
 * If no class is present, extension is not installed.
 *
 * Pages can use CSS visibility classes to show/hide content based on state.
 * See TtConst in src/tt/environment/constants.py for the full list.
 *
 * Note: This script reads cached auth state from storage. It does NOT
 * validate with the server - that happens when features are actually used.
 * This is intentional to avoid excessive server calls during navigation.
 */

(function() {
    'use strict';

    var STATE_CLASS_AUTHORIZED = TT.SERVER_SYNC.EXT_STATE_CLASS_AUTHORIZED;
    var STATE_CLASS_NOT_AUTHORIZED = TT.SERVER_SYNC.EXT_STATE_CLASS_NOT_AUTHORIZED;
    var STATE_CLASS_SERVER_MISMATCH = TT.SERVER_SYNC.EXT_STATE_CLASS_SERVER_MISMATCH;
    var STATE_CLASS_ACCOUNT_MISMATCH = TT.SERVER_SYNC.EXT_STATE_CLASS_ACCOUNT_MISMATCH;
    var USER_UUID_DATA_ATTR = TT.SERVER_SYNC.EXT_USER_UUID_DATA_ATTR;

    var ALL_STATE_CLASSES = [
        STATE_CLASS_AUTHORIZED,
        STATE_CLASS_NOT_AUTHORIZED,
        STATE_CLASS_SERVER_MISMATCH,
        STATE_CLASS_ACCOUNT_MISMATCH
    ];

    /**
     * Get the default server URL based on development mode.
     */
    function getDefaultServerUrl() {
        return TT.CONFIG.IS_DEVELOPMENT
            ? TT.CONFIG.DEFAULT_SERVER_URL_DEV
            : TT.CONFIG.DEFAULT_SERVER_URL_PROD;
    }

    /**
     * Extract normalized origin from a URL string.
     * Handles trailing slashes, paths, case differences, and default ports.
     * Returns the original string if parsing fails.
     */
    function getOriginFromUrl( url ) {
        try {
            var parsed = new URL( url );
            return parsed.origin;
        } catch ( e ) {
            return url;
        }
    }

    /**
     * Get the page's user UUID from the data attribute on body.
     * Returns null if not present (unauthenticated page or attribute missing).
     */
    function getPageUserUuid() {
        return document.body.getAttribute( USER_UUID_DATA_ATTR );
    }

    /**
     * Determine and set the appropriate extension state class.
     * Checks server URL match, auth state, and account UUID match.
     */
    function updateExtensionState() {
        var storageKeys = [
            TT.STORAGE.KEY_SERVER_URL,
            TT.STORAGE.KEY_AUTH_STATE,
            TT.STORAGE.KEY_USER_UUID
        ];

        chrome.storage.local.get( storageKeys, function( result ) {
            if ( chrome.runtime.lastError ) {
                // Storage error - show as not authorized
                setStateClass( STATE_CLASS_NOT_AUTHORIZED );
                return;
            }

            // Step 1: Check server URL match (normalize to handle trailing slashes, paths, etc.)
            var storedServerUrl = result[TT.STORAGE.KEY_SERVER_URL] || getDefaultServerUrl();
            var storedOrigin = getOriginFromUrl( storedServerUrl );
            var pageOrigin = window.location.origin;

            if ( storedOrigin !== pageOrigin ) {
                // Extension is configured for a different server
                setStateClass( STATE_CLASS_SERVER_MISMATCH );
                return;
            }

            // Step 2: Check authorization state
            var authState = result[TT.STORAGE.KEY_AUTH_STATE];
            if ( authState !== TT.AUTH.STATE_AUTHORIZED ) {
                // Extension is not authorized
                setStateClass( STATE_CLASS_NOT_AUTHORIZED );
                return;
            }

            // Step 3: Check account UUID match
            var storedUserUuid = result[TT.STORAGE.KEY_USER_UUID];
            var pageUserUuid = getPageUserUuid();

            // If page doesn't have a user UUID (unauthenticated page), allow authorized state
            // This handles public pages where we can't verify account but extension is valid
            if ( pageUserUuid && storedUserUuid && pageUserUuid !== storedUserUuid ) {
                // Extension is authorized to a different account
                setStateClass( STATE_CLASS_ACCOUNT_MISMATCH );
                return;
            }

            // All checks passed - extension is authorized for this server and account
            setStateClass( STATE_CLASS_AUTHORIZED );
        });
    }

    /**
     * Set the appropriate state class on the body element.
     * Removes all state classes first to ensure clean state.
     */
    function setStateClass( stateClass ) {
        ALL_STATE_CLASSES.forEach( function( cls ) {
            document.body.classList.remove( cls );
        });
        document.body.classList.add( stateClass );
    }

    // Run when DOM is ready
    if ( document.readyState === 'loading' ) {
        document.addEventListener( 'DOMContentLoaded', updateExtensionState );
    } else {
        updateExtensionState();
    }

})();
