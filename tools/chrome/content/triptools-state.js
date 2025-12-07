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
 */

(function() {
    'use strict';

    var STATE_CLASS_AUTHORIZED = TT.SERVER_SYNC.EXT_STATE_CLASS_AUTHORIZED;
    var STATE_CLASS_NOT_AUTHORIZED = TT.SERVER_SYNC.EXT_STATE_CLASS_NOT_AUTHORIZED;

    /**
     * Query auth status from service worker and update body classes.
     */
    function updateExtensionState() {
        chrome.runtime.sendMessage(
            { type: TT.MESSAGE.TYPE_AUTH_STATUS_REQUEST, data: {} },
            function( response ) {
                if ( chrome.runtime.lastError ) {
                    // Service worker not responding - treat as not authorized
                    setStateClass( STATE_CLASS_NOT_AUTHORIZED );
                    return;
                }

                if ( response && response.success && response.data && response.data.authorized ) {
                    setStateClass( STATE_CLASS_AUTHORIZED );
                } else {
                    setStateClass( STATE_CLASS_NOT_AUTHORIZED );
                }
            }
        );
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
