/*
 * Trip Tools Chrome Extension - Sync Mode Manager
 * Coordinates modal sync operations and provides visual feedback.
 * Disables dialog decoration during sync to prevent interference.
 */

var TTSyncMode = ( function() {
    'use strict';

    var BANNER_ID = 'tt-sync-mode-banner';
    var BORDER_CLASS = 'tt-sync-mode-active';

    var _active = false;
    var _onStopCallback = null;

    /**
     * Check if sync mode is currently active.
     * @returns {boolean}
     */
    function isActive() {
        return _active;
    }

    /**
     * Enter sync mode.
     * Shows visual indicator and disables dialog decoration.
     * @param {Object} options - Configuration options.
     * @param {Function} options.onStop - Callback when user clicks Stop button.
     */
    function enter( options ) {
        if ( _active ) {
            return;
        }

        options = options || {};
        _onStopCallback = options.onStop || null;
        _active = true;

        _showIndicator();
        console.log( '[TT Sync Mode] Entered' );
    }

    /**
     * Exit sync mode.
     * Hides visual indicator and re-enables dialog decoration.
     */
    function exit() {
        if ( !_active ) {
            return;
        }

        _active = false;
        _onStopCallback = null;

        _hideIndicator();
        console.log( '[TT Sync Mode] Exited' );
    }

    /**
     * Handle stop button click.
     * @private
     */
    function _handleStopClick() {
        console.log( '[TT Sync Mode] Stop requested by user' );

        if ( _onStopCallback ) {
            _onStopCallback();
        }

        // Don't call exit() here - let the sync code handle cleanup
        // The callback should eventually call exit()
    }

    /**
     * Show the sync mode visual indicator.
     * @private
     */
    function _showIndicator() {
        // Add border class to body
        document.body.classList.add( BORDER_CLASS );

        // Create banner if it doesn't exist
        if ( document.getElementById( BANNER_ID ) ) {
            return;
        }

        var banner = document.createElement( 'div' );
        banner.id = BANNER_ID;

        var messageSpan = document.createElement( 'span' );
        messageSpan.className = 'tt-sync-mode-message';
        messageSpan.textContent = 'Sync in Progress \u2014 Please do not interact with the map';

        var stopButton = document.createElement( 'button' );
        stopButton.className = 'tt-sync-mode-stop-btn';
        stopButton.textContent = 'Stop Sync';
        stopButton.addEventListener( 'click', _handleStopClick );

        banner.appendChild( messageSpan );
        banner.appendChild( stopButton );
        document.body.appendChild( banner );
    }

    /**
     * Hide the sync mode visual indicator.
     * @private
     */
    function _hideIndicator() {
        // Remove border class from body
        document.body.classList.remove( BORDER_CLASS );

        // Remove banner
        var banner = document.getElementById( BANNER_ID );
        if ( banner ) {
            banner.remove();
        }
    }

    return {
        isActive: isActive,
        enter: enter,
        exit: exit
    };

} )();
