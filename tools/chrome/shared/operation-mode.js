/*
 * Trip Tools Chrome Extension - Operation Mode Manager
 * Coordinates modal operations and provides visual feedback.
 * Disables dialog decoration during certain modes to prevent interference.
 */

var TTOperationMode = ( function() {
    'use strict';

    var BANNER_ID = 'tt-operation-banner';
    var BORDER_CLASS = 'tt-operation-active';
    var BANNER_PARTIAL_CLASS = 'tt-operation-banner-partial';

    // Banner styles
    var BannerStyle = {
        FULL: 'full',      // Full width, covers search bar (for full automation)
        PARTIAL: 'partial' // Right 50%, leaves search bar accessible (for semi-automation)
    };

    // Mode definitions with metadata
    // GMM-specific modes are prefixed with GMM_
    var MODE_DEFS = {
        NORMAL: {
            id: 'normal',
            title: null,
            description: null,
            cssClass: null,
            suppressGmmIntercepts: false,
            bannerStyle: null
        },
        GMM_SYNC_EXECUTE: {
            id: 'gmm_sync_execute',
            title: 'Sync in Progress',
            description: 'Please do not interact with the map',
            cssClass: 'tt-operation-gmm-sync-execute',
            suppressGmmIntercepts: true,
            bannerStyle: BannerStyle.FULL
        },
        GMM_SYNC_UNDO: {
            id: 'gmm_sync_undo',
            title: 'Removing Location',
            description: null,
            cssClass: 'tt-operation-gmm-sync-undo',
            suppressGmmIntercepts: true,
            bannerStyle: BannerStyle.FULL
        },
        GMM_SYNC_FIX: {
            id: 'gmm_sync_fix',
            title: 'Manual Fix Mode',
            description: 'Select the correct location',
            cssClass: 'tt-operation-gmm-sync-fix',
            suppressGmmIntercepts: true,
            bannerStyle: BannerStyle.PARTIAL
        },
        GMM_USER_ADD: {
            id: 'gmm_user_add',
            title: 'Adding Location',
            description: null,
            cssClass: 'tt-operation-gmm-user-add',
            suppressGmmIntercepts: true,
            bannerStyle: BannerStyle.FULL
        }
    };

    // Expose mode keys for external use
    var Mode = {
        NORMAL: 'NORMAL',
        GMM_SYNC_EXECUTE: 'GMM_SYNC_EXECUTE',
        GMM_SYNC_UNDO: 'GMM_SYNC_UNDO',
        GMM_SYNC_FIX: 'GMM_SYNC_FIX',
        GMM_USER_ADD: 'GMM_USER_ADD'
    };

    var _currentMode = Mode.NORMAL;
    var _onStopCallback = null;

    /**
     * Get the current mode key.
     * @returns {string} Current mode key (e.g., 'NORMAL', 'SYNC_EXECUTE').
     */
    function getMode() {
        return _currentMode;
    }

    /**
     * Check if any operation is active (not NORMAL mode).
     * @returns {boolean}
     */
    function isActive() {
        return _currentMode !== Mode.NORMAL;
    }

    /**
     * Check if GMM intercepts should be suppressed in current mode.
     * Used by gmm.js to decide whether to decorate dialogs.
     * @returns {boolean}
     */
    function suppressGmmIntercepts() {
        var modeDef = MODE_DEFS[_currentMode];
        return modeDef ? modeDef.suppressGmmIntercepts : false;
    }

    /**
     * Enter a specific operation mode.
     * Shows visual indicator and configures mode behavior.
     * @param {string} mode - Mode key (from TTOperationMode.Mode).
     * @param {Object} [options] - Configuration options.
     * @param {string} [options.message] - Override default description.
     * @param {Function} [options.onStop] - Callback when user clicks Stop button.
     */
    function enter( mode, options ) {
        if ( _currentMode !== Mode.NORMAL ) {
            console.warn( '[TT Operation] Already in mode:', _currentMode, '- ignoring enter to:', mode );
            return;
        }

        if ( !MODE_DEFS[mode] ) {
            console.error( '[TT Operation] Unknown mode:', mode );
            return;
        }

        options = options || {};
        _currentMode = mode;
        _onStopCallback = options.onStop || null;

        var modeDef = MODE_DEFS[mode];
        var message = options.message || modeDef.description;

        _showIndicator( modeDef, message );
        console.log( '[TT Operation] Entered mode:', mode );
    }

    /**
     * Exit to NORMAL mode.
     * Hides visual indicator and resets state.
     */
    function exit() {
        if ( _currentMode === Mode.NORMAL ) {
            return;
        }

        var previousMode = _currentMode;
        _currentMode = Mode.NORMAL;
        _onStopCallback = null;

        _hideIndicator();
        console.log( '[TT Operation] Exited mode:', previousMode );
    }

    /**
     * Handle stop button click.
     * @private
     */
    function _handleStopClick() {
        console.log( '[TT Operation] Stop requested by user in mode:', _currentMode );

        if ( _onStopCallback ) {
            _onStopCallback();
        }

        // Don't call exit() here - let the calling code handle cleanup
        // The callback should eventually trigger exit()
    }

    /**
     * Show the operation mode visual indicator.
     * @param {Object} modeDef - Mode definition object.
     * @param {string} message - Message to display (may be null).
     * @private
     */
    function _showIndicator( modeDef, message ) {
        // Add border class to body
        document.body.classList.add( BORDER_CLASS );

        // Remove any existing banner
        var existing = document.getElementById( BANNER_ID );
        if ( existing ) {
            existing.remove();
        }

        // Create banner
        var banner = document.createElement( 'div' );
        banner.id = BANNER_ID;

        // Add mode-specific CSS class
        if ( modeDef.cssClass ) {
            banner.classList.add( modeDef.cssClass );
        }

        // Add partial banner class if mode uses partial style
        if ( modeDef.bannerStyle === BannerStyle.PARTIAL ) {
            banner.classList.add( BANNER_PARTIAL_CLASS );
        }

        // Title and message
        var textContent = modeDef.title || '';
        if ( message ) {
            textContent += textContent ? ' \u2014 ' + message : message;
        }

        var messageSpan = document.createElement( 'span' );
        messageSpan.className = 'tt-operation-message';
        messageSpan.textContent = textContent;
        banner.appendChild( messageSpan );

        // Stop button (only if callback provided)
        if ( _onStopCallback ) {
            var stopButton = document.createElement( 'button' );
            stopButton.className = 'tt-operation-stop-btn';
            stopButton.textContent = 'Stop';
            stopButton.addEventListener( 'click', _handleStopClick );
            banner.appendChild( stopButton );
        }

        document.body.appendChild( banner );
    }

    /**
     * Hide the operation mode visual indicator.
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
        Mode: Mode,
        getMode: getMode,
        isActive: isActive,
        suppressGmmIntercepts: suppressGmmIntercepts,
        enter: enter,
        exit: exit
    };

} )();
