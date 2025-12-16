/*
 * Trip Tools Chrome Extension - State Content Script
 * Adds CSS classes to the page body indicating extension state.
 * Runs on all triptools.net pages to enable state-aware UI.
 *
 * Classes added to <body> (defined in TT.SERVER_SYNC):
 *   tt-ext-authorized     - Extension is installed and has valid auth
 *   tt-ext-not-authorized - Extension is installed but not authorized
 *
 * If neither class is present, extension is not installed.
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

    /**
     * Read cached auth state from storage and update body classes.
     * Does not validate with server - just uses locally stored state.
     */
    function updateExtensionState() {
        chrome.storage.local.get( TT.STORAGE.KEY_AUTH_STATE, function( result ) {
            if ( chrome.runtime.lastError ) {
                setStateClass( STATE_CLASS_NOT_AUTHORIZED );
                return;
            }

            var authState = result[TT.STORAGE.KEY_AUTH_STATE];
            if ( authState === TT.AUTH.STATE_AUTHORIZED ) {
                setStateClass( STATE_CLASS_AUTHORIZED );
            } else {
                setStateClass( STATE_CLASS_NOT_AUTHORIZED );
            }
        });
    }

    /**
     * Set the appropriate state class on the body element.
     */
    function setStateClass( stateClass ) {
        document.body.classList.remove( STATE_CLASS_AUTHORIZED, STATE_CLASS_NOT_AUTHORIZED );
        document.body.classList.add( stateClass );
    }

    // Run when DOM is ready
    if ( document.readyState === 'loading' ) {
        document.addEventListener( 'DOMContentLoaded', updateExtensionState );
    } else {
        updateExtensionState();
    }

})();
