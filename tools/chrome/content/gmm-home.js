/*
 * Trip Tools Chrome Extension - GMM Home Page Content Script
 * Injected into Google My Maps home page.
 * Handles map creation automation triggered from background/popup.
 * Depends on: constants.js, dom.js, site-adapter.js,
 *             gmm-home-selectors.js, gmm-home-adapter.js
 */

( function() {
    'use strict';

    // =========================================================================
    // Initialization
    // =========================================================================

    function initialize() {
        console.log( '[TT GMM-Home] Content script loaded' );

        // Initialize adapter
        TTGmmHomeAdapter.initialize();

        // Set up message listener for commands from background
        chrome.runtime.onMessage.addListener( handleMessage );

        console.log( '[TT GMM-Home] Ready for commands' );
    }

    // =========================================================================
    // Message Handling
    // =========================================================================

    /**
     * Handle messages from background script or popup.
     * @param {Object} request - Message request.
     * @param {Object} sender - Message sender.
     * @param {Function} sendResponse - Response callback.
     * @returns {boolean} True if async response.
     */
    function handleMessage( request, sender, sendResponse ) {
        console.log( '[TT GMM-Home] Received message:', request.type );

        switch ( request.type ) {
            case TT.MESSAGE.TYPE_GMM_CREATE_MAP:
                handleCreateMap()
                    .then( function( result ) {
                        sendResponse({ success: true, data: result });
                    })
                    .catch( function( error ) {
                        sendResponse({ success: false, error: error.message });
                    });
                return true; // Async response

            case TT.MESSAGE.TYPE_PING:
                sendResponse({ success: true, page: 'gmm-home' });
                return false;

            default:
                return false;
        }
    }

    /**
     * Handle create map command.
     * Clicks the create button and waits briefly.
     * The page will navigate to the new map's edit page.
     * @returns {Promise<Object>}
     */
    function handleCreateMap() {
        console.log( '[TT GMM-Home] Creating new map...' );

        if ( !TTGmmHomeAdapter.isHomePage() ) {
            return Promise.reject( new Error( 'Not on GMM home page' ) );
        }

        return TTGmmHomeAdapter.clickCreateMap()
            .then( function() {
                console.log( '[TT GMM-Home] Create button clicked, page will navigate' );
                return { clicked: true };
            });
    }

    // =========================================================================
    // Start
    // =========================================================================

    initialize();

})();
