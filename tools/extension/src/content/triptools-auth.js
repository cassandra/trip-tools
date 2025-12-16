/*
 * Trip Tools Chrome Extension - Authorization Content Script
 * Listens for postMessage token delivery on triptools.net authorization pages.
 * Security: Verifies message origin before accepting token.
 */

(function() {
    'use strict';

    // Only run on extension pages
    if ( !window.location.pathname.startsWith( '/user/extensions/' ) ) {
        return;
    }

    /**
     * Handle incoming postMessage events.
     * Listens for tt_extension_data messages from the page and sends ack back.
     */
    function handleMessage( event ) {
        // Security: Verify origin matches current page origin
        if ( event.origin !== window.location.origin ) {
            return;
        }

        // Check message structure
        if ( !event.data || typeof event.data !== 'object' ) {
            return;
        }

        // Check message type matches expected data message
        if ( event.data.type !== TT.SERVER_SYNC.EXT_POSTMESSAGE_DATA_TYPE ) {
            return;
        }

        var payload = event.data.payload;
        if ( !payload || payload.action !== 'authorize' || !payload.token ) {
            return;
        }

        handleAuthorize( payload.token );
    }

    /**
     * Handle authorization by sending token to service worker and ack back to page.
     */
    function handleAuthorize( token ) {
        // Validate token format
        if ( typeof token !== 'string' || !token.startsWith( 'tt_' ) ) {
            sendAck( false, 'Invalid token format' );
            return;
        }

        // Send token to background worker
        chrome.runtime.sendMessage(
            {
                type: TT.MESSAGE.TYPE_TOKEN_RECEIVED,
                data: { token: token }
            },
            function( response ) {
                if ( chrome.runtime.lastError ) {
                    console.error( 'Trip Tools: Failed to send token to extension', chrome.runtime.lastError );
                    sendAck( false, 'Failed to communicate with extension' );
                    return;
                }

                if ( response && response.success ) {
                    sendAck( true, null );
                } else {
                    var errorMsg = response && response.data && response.data.error
                        ? response.data.error
                        : 'Token validation failed';
                    sendAck( false, errorMsg );
                }
            }
        );
    }

    /**
     * Send acknowledgment back to the page.
     */
    function sendAck( success, error ) {
        window.postMessage( {
            type: TT.SERVER_SYNC.EXT_POSTMESSAGE_ACK_TYPE,
            payload: {
                action: 'authorize',
                success: success,
                error: error
            }
        }, window.location.origin );
    }

    // Register message listener
    window.addEventListener( 'message', handleMessage );

})();
