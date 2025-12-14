/*
 * Trip Tools Chrome Extension - Popup Script
 * Handles popup UI initialization and user interactions.
 */

document.addEventListener( 'DOMContentLoaded', function() {
    initializePopup();
});

function initializePopup() {
    applyDevModeStyles();
    checkBackgroundConnection();
    loadSettings();
    setupEventListeners();
    loadDebugLog();
    checkAuthStatus();
    listenForAuthStateChanges();
    detectCurrentPage();
    // Trip loading happens after auth check via showAuthorizedState()
}

function listenForAuthStateChanges() {
    chrome.runtime.onMessage.addListener( function( message ) {
        if ( message.type === TT.MESSAGE.TYPE_AUTH_STATE_CHANGED ) {
            if ( message.data.authorized ) {
                showAuthorizedState( message.data.email, message.data.serverStatus );
            } else {
                showNotAuthorizedState();
            }
        }
    });
}

function applyDevModeStyles() {
    if ( TT.CONFIG.IS_DEVELOPMENT ) {
        var devBanner = document.getElementById( TT.DOM.ID_DEV_BANNER );
        if ( devBanner ) {
            devBanner.classList.remove( TT.DOM.CLASS_HIDDEN );
        }
    }
}

function checkBackgroundConnection() {
    var indicator = document.getElementById( TT.DOM.ID_STATUS_INDICATOR );
    var statusText = document.getElementById( TT.DOM.ID_STATUS_TEXT );

    TTMessaging.ping()
        .then( function( response ) {
            if ( response && response.success ) {
                // Store uptime for later use when we know auth status
                window.ttBackgroundUptime = response.data.uptime;
                addLocalDebugEntry( 'info', 'Background connection established' );
            } else {
                setDisconnectedStatus( indicator, statusText );
            }
        })
        .catch( function( error ) {
            setDisconnectedStatus( indicator, statusText );
            addLocalDebugEntry( 'error', 'Connection failed: ' + error.message );
        });
}

function setDisconnectedStatus( indicator, statusText ) {
    indicator.classList.remove( TT.DOM.CLASS_CONNECTED );
    indicator.classList.add( TT.DOM.CLASS_DISCONNECTED );
    statusText.textContent = 'Disconnected';
}

function loadSettings() {
    TTStorage.get( TT.STORAGE.KEY_SELECT_DECORATE_ENABLED, true )
        .then( function( enabled ) {
            var toggle = document.getElementById( TT.DOM.ID_DECORATE_TOGGLE );
            if ( toggle ) {
                toggle.checked = enabled;
            }
        });

    loadDebugPanelVisibility();
}

function loadDebugPanelVisibility() {
    var defaultDeveloperMode = TT.CONFIG.IS_DEVELOPMENT;

    TTStorage.get( TT.STORAGE.KEY_DEVELOPER_MODE, defaultDeveloperMode )
        .then( function( developerModeEnabled ) {
            if ( !developerModeEnabled ) {
                return false;
            }
            return TTStorage.get( TT.STORAGE.KEY_DEBUG_PANEL_ENABLED, true );
        })
        .then( function( showDebugPanel ) {
            var panel = document.getElementById( TT.DOM.ID_DEBUG_PANEL );
            if ( panel ) {
                if ( showDebugPanel ) {
                    panel.classList.remove( TT.DOM.CLASS_HIDDEN );
                } else {
                    panel.classList.add( TT.DOM.CLASS_HIDDEN );
                }
            }
        });
}

function setupEventListeners() {
    setupQuickSettingsListeners();
    setupAuthEventListeners();
    setupTripEventListeners();
    setupGmmEventListeners();
    setupLinkMapEventListeners();
    setupLinkSuccessEventListeners();

    var decorateToggle = document.getElementById( TT.DOM.ID_DECORATE_TOGGLE );
    if ( decorateToggle ) {
        decorateToggle.addEventListener( 'change', function() {
            TTStorage.set( TT.STORAGE.KEY_SELECT_DECORATE_ENABLED, this.checked );
            addLocalDebugEntry( 'info', 'Decoration toggled: ' + this.checked );
        });
    }

    var debugHeader = document.getElementById( TT.DOM.ID_DEBUG_HEADER );
    if ( debugHeader ) {
        debugHeader.addEventListener( 'click', function() {
            var content = document.getElementById( TT.DOM.ID_DEBUG_CONTENT );
            var arrow = document.getElementById( TT.DOM.ID_DEBUG_ARROW );
            if ( content.classList.contains( TT.DOM.CLASS_HIDDEN ) ) {
                content.classList.remove( TT.DOM.CLASS_HIDDEN );
                arrow.innerHTML = '&#9660;';
            } else {
                content.classList.add( TT.DOM.CLASS_HIDDEN );
                arrow.innerHTML = '&#9654;';
            }
        });
    }

    setupStubButtonListeners();
}

function setupStubButtonListeners() {
    var stubButtons = document.querySelectorAll( '.' + TT.DOM.CLASS_BTN_STUB );
    stubButtons.forEach( function( button ) {
        button.addEventListener( 'click', function() {
            addLocalDebugEntry( 'info', 'Stub button clicked: ' + this.id );
        });
    });
}

function setupQuickSettingsListeners() {
    var settingsBtn = document.getElementById( TT.DOM.ID_SETTINGS_BTN );
    if ( settingsBtn ) {
        settingsBtn.addEventListener( 'click', function() {
            showQuickSettings();
        });
    }

    var backBtn = document.getElementById( TT.DOM.ID_QUICK_SETTINGS_BACK );
    if ( backBtn ) {
        backBtn.addEventListener( 'click', function() {
            hideQuickSettings();
        });
    }

    var allOptionsLink = document.getElementById( TT.DOM.ID_ALL_OPTIONS_LINK );
    if ( allOptionsLink ) {
        allOptionsLink.addEventListener( 'click', function( e ) {
            e.preventDefault();
            chrome.runtime.openOptionsPage();
        });
    }
}

function showQuickSettings() {
    var panel = document.getElementById( TT.DOM.ID_QUICK_SETTINGS );
    if ( panel ) {
        panel.classList.remove( TT.DOM.CLASS_HIDDEN );
        requestAnimationFrame( function() {
            panel.classList.add( TT.DOM.CLASS_VISIBLE );
        });
    }
}

function hideQuickSettings() {
    var panel = document.getElementById( TT.DOM.ID_QUICK_SETTINGS );
    if ( panel ) {
        panel.classList.remove( TT.DOM.CLASS_VISIBLE );
        panel.addEventListener( 'transitionend', function handler() {
            panel.classList.add( TT.DOM.CLASS_HIDDEN );
            panel.removeEventListener( 'transitionend', handler );
        });
    }
}

function loadDebugLog() {
    TTStorage.get( TT.STORAGE.KEY_DEBUG_LOG, [] )
        .then( function( log ) {
            renderDebugLog( log );
        });

    addLocalDebugEntry( 'info', 'Extension popup loaded' );
}

function renderDebugLog( log ) {
    var logContainer = document.getElementById( TT.DOM.ID_DEBUG_LOG );
    if ( !logContainer ) {
        return;
    }

    logContainer.innerHTML = '';
    var displayLog = log.slice( 0, 10 );
    displayLog.forEach( function( entry ) {
        var entryDiv = document.createElement( 'div' );
        entryDiv.className = 'tt-debug-entry';

        var timestamp = new Date( entry.timestamp ).toLocaleTimeString();
        var levelClass = 'tt-debug-level-' + entry.level;

        // Use textContent to prevent XSS from debug log entries
        var timestampSpan = document.createElement( 'span' );
        timestampSpan.className = 'tt-debug-timestamp';
        timestampSpan.textContent = timestamp;

        var messageSpan = document.createElement( 'span' );
        messageSpan.className = levelClass;
        messageSpan.textContent = entry.message;

        entryDiv.appendChild( timestampSpan );
        entryDiv.appendChild( messageSpan );

        logContainer.appendChild( entryDiv );
    });
}

function addLocalDebugEntry( level, message ) {
    TTStorage.get( TT.STORAGE.KEY_DEBUG_LOG, [] )
        .then( function( log ) {
            var entry = {
                timestamp: Date.now(),
                level: level,
                message: message
            };
            log.unshift( entry );
            if ( log.length > TT.CONFIG.DEBUG_LOG_MAX_ENTRIES ) {
                log = log.slice( 0, TT.CONFIG.DEBUG_LOG_MAX_ENTRIES );
            }
            return TTStorage.set( TT.STORAGE.KEY_DEBUG_LOG, log );
        })
        .then( function() {
            return TTStorage.get( TT.STORAGE.KEY_DEBUG_LOG, [] );
        })
        .then( function( log ) {
            renderDebugLog( log );
        });
}

function checkAuthStatus() {
    TTMessaging.send( TT.MESSAGE.TYPE_AUTH_STATUS_REQUEST, {} )
        .then( function( response ) {
            if ( response && response.success && response.data.authorized ) {
                showAuthorizedState( response.data.email, response.data.serverStatus );
            } else {
                showNotAuthorizedState();
            }
        })
        .catch( function( error ) {
            showNotAuthorizedState();
            addLocalDebugEntry( 'error', 'Auth check failed: ' + error.message );
        });
}

function showAuthorizedState( email, serverStatus ) {
    var authSection = document.getElementById( TT.DOM.ID_AUTH_SECTION );
    if ( authSection ) {
        authSection.classList.add( TT.DOM.CLASS_HIDDEN );
    }

    // Update status bar based on server status
    var indicator = document.getElementById( TT.DOM.ID_STATUS_INDICATOR );
    var statusText = document.getElementById( TT.DOM.ID_STATUS_TEXT );
    if ( indicator && statusText ) {
        // Remove all state classes
        indicator.classList.remove(
            TT.DOM.CLASS_CONNECTED,
            TT.DOM.CLASS_DISCONNECTED,
            TT.DOM.CLASS_OFFLINE,
            TT.DOM.CLASS_SERVER_ERROR,
            TT.DOM.CLASS_RATE_LIMITED
        );

        switch ( serverStatus ) {
            case TT.AUTH.STATUS_OFFLINE:
                indicator.classList.add( TT.DOM.CLASS_OFFLINE );
                statusText.textContent = TT.STRINGS.STATUS_OFFLINE;
                break;
            case TT.AUTH.STATUS_SERVER_ERROR:
                indicator.classList.add( TT.DOM.CLASS_SERVER_ERROR );
                statusText.textContent = TT.STRINGS.STATUS_SERVER_ERROR;
                break;
            case TT.AUTH.STATUS_TIMEOUT:
                indicator.classList.add( TT.DOM.CLASS_SERVER_ERROR );
                statusText.textContent = TT.STRINGS.STATUS_TIMEOUT;
                break;
            case TT.AUTH.STATUS_RATE_LIMITED:
                indicator.classList.add( TT.DOM.CLASS_RATE_LIMITED );
                statusText.textContent = TT.STRINGS.STATUS_RATE_LIMITED;
                break;
            default:
                indicator.classList.add( TT.DOM.CLASS_CONNECTED );
                var uptimeSec = Math.floor( ( window.ttBackgroundUptime || 0 ) / 1000 );
                statusText.textContent = TT.STRINGS.STATUS_ONLINE + ' (uptime: ' + uptimeSec + 's)';
        }
    }

    updateDebugAuthInfo( email );

    // Show trip section and load trips
    showTripSection();
    loadTrips();
}

function showNotAuthorizedState() {
    var authSection = document.getElementById( TT.DOM.ID_AUTH_SECTION );
    if ( authSection ) {
        authSection.classList.remove( TT.DOM.CLASS_HIDDEN );

        var authStatus = document.getElementById( TT.DOM.ID_AUTH_STATUS );
        if ( authStatus ) {
            authStatus.textContent = TT.STRINGS.AUTH_PROMPT_CONNECT;
        }
    }

    // Update status bar to show not connected
    var indicator = document.getElementById( TT.DOM.ID_STATUS_INDICATOR );
    var statusText = document.getElementById( TT.DOM.ID_STATUS_TEXT );
    if ( indicator && statusText ) {
        indicator.classList.remove( TT.DOM.CLASS_CONNECTED );
        indicator.classList.add( TT.DOM.CLASS_DISCONNECTED );
        statusText.textContent = 'Not connected';
    }

    updateDebugAuthInfo( null );

    // Hide trip section when not authorized
    hideTripSection();
}

function setupAuthEventListeners() {
    var authorizeBtn = document.getElementById( TT.DOM.ID_AUTHORIZE_BTN );
    if ( authorizeBtn ) {
        authorizeBtn.addEventListener( 'click', function() {
            TTAuth.openAuthorizePage();
        });
    }
}

function setupTripEventListeners() {
    var newTripBtn = document.getElementById( TT.DOM.ID_NEW_TRIP_BTN );
    if ( newTripBtn ) {
        newTripBtn.addEventListener( 'click', function() {
            openNewTripPage();
        });
    }

    var moreTripsBtn = document.getElementById( TT.DOM.ID_MORE_TRIPS_BTN );
    if ( moreTripsBtn ) {
        moreTripsBtn.addEventListener( 'click', function() {
            showMoreTripsPanel();
        });
    }

    var moreTripsBackBtn = document.getElementById( TT.DOM.ID_MORE_TRIPS_BACK );
    if ( moreTripsBackBtn ) {
        moreTripsBackBtn.addEventListener( 'click', function() {
            hideMoreTripsPanel();
        });
    }

    var tripDetailsBackBtn = document.getElementById( TT.DOM.ID_TRIP_DETAILS_BACK );
    if ( tripDetailsBackBtn ) {
        tripDetailsBackBtn.addEventListener( 'click', function() {
            hideTripDetailsPanel();
        });
    }

    // Stale pin dismiss button
    var stalePinDismissBtn = document.getElementById( TT.DOM.ID_STALE_PIN_DISMISS );
    if ( stalePinDismissBtn ) {
        stalePinDismissBtn.addEventListener( 'click', handleStalePinDismiss );
    }

    var syncLocationsBtn = document.getElementById( TT.DOM.ID_TRIP_DETAILS_SYNC_BTN );
    if ( syncLocationsBtn ) {
        syncLocationsBtn.addEventListener( 'click', handleSyncLocations );
    }

    var unlinkMapBtn = document.getElementById( TT.DOM.ID_TRIP_DETAILS_UNLINK_BTN );
    if ( unlinkMapBtn ) {
        unlinkMapBtn.addEventListener( 'click', handleUnlinkMap );
    }

    // Unlinked trip action buttons
    var createMapBtn = document.getElementById( TT.DOM.ID_TRIP_DETAILS_CREATE_MAP_BTN );
    if ( createMapBtn ) {
        createMapBtn.addEventListener( 'click', handleCreateMapFromDetails );
    }

    var linkCurrentBtn = document.getElementById( TT.DOM.ID_TRIP_DETAILS_LINK_CURRENT_BTN );
    if ( linkCurrentBtn ) {
        linkCurrentBtn.addEventListener( 'click', handleLinkCurrentMapFromDetails );
    }

    // Create Trip panel listeners
    var createTripBackBtn = document.getElementById( TT.DOM.ID_CREATE_TRIP_BACK );
    if ( createTripBackBtn ) {
        createTripBackBtn.addEventListener( 'click', function() {
            hideCreateTripPanel();
        });
    }

    var createTripCancelBtn = document.getElementById( TT.DOM.ID_CREATE_TRIP_CANCEL );
    if ( createTripCancelBtn ) {
        createTripCancelBtn.addEventListener( 'click', function() {
            hideCreateTripPanel();
        });
    }

    var createTripSubmitBtn = document.getElementById( TT.DOM.ID_CREATE_TRIP_SUBMIT );
    if ( createTripSubmitBtn ) {
        createTripSubmitBtn.addEventListener( 'click', handleCreateTripSubmit );
    }
}

function openNewTripPage() {
    // Show create trip panel instead of opening web app
    showCreateTripPanel();
}

function updateDebugAuthInfo( email ) {
    var authInfo = document.getElementById( TT.DOM.ID_DEBUG_AUTH_INFO );
    if ( !authInfo ) {
        return;
    }

    // Clear existing content
    authInfo.innerHTML = '';

    var entryDiv = document.createElement( 'div' );
    entryDiv.className = 'tt-debug-entry';

    var messageSpan = document.createElement( 'span' );

    if ( email ) {
        messageSpan.className = 'tt-debug-level-info';
        // Use textContent to prevent XSS from email values
        messageSpan.textContent = TT.STRINGS.DEBUG_USER_EMAIL + ': ' + email;
    } else {
        messageSpan.className = 'tt-debug-level-warning';
        messageSpan.textContent = TT.STRINGS.AUTH_STATUS_NOT_AUTHORIZED;
    }

    entryDiv.appendChild( messageSpan );
    authInfo.appendChild( entryDiv );
}

// =============================================================================
// Trip Section
// =============================================================================

function showTripSection() {
    var tripSection = document.getElementById( TT.DOM.ID_TRIP_SECTION );
    if ( tripSection ) {
        tripSection.classList.remove( TT.DOM.CLASS_HIDDEN );
    }
}

function hideTripSection() {
    var tripSection = document.getElementById( TT.DOM.ID_TRIP_SECTION );
    if ( tripSection ) {
        tripSection.classList.add( TT.DOM.CLASS_HIDDEN );
    }
    // Clear trip list
    var tripList = document.getElementById( TT.DOM.ID_TRIP_LIST );
    if ( tripList ) {
        tripList.innerHTML = '';
    }
}

function showTripLoading() {
    var loading = document.getElementById( TT.DOM.ID_TRIP_LOADING );
    var workingSet = document.getElementById( TT.DOM.ID_WORKING_SET );
    var empty = document.getElementById( TT.DOM.ID_TRIP_EMPTY );

    if ( loading ) loading.classList.remove( TT.DOM.CLASS_HIDDEN );
    if ( workingSet ) workingSet.classList.add( TT.DOM.CLASS_HIDDEN );
    if ( empty ) empty.classList.add( TT.DOM.CLASS_HIDDEN );
}

function showTripContent() {
    var loading = document.getElementById( TT.DOM.ID_TRIP_LOADING );
    var workingSet = document.getElementById( TT.DOM.ID_WORKING_SET );
    var empty = document.getElementById( TT.DOM.ID_TRIP_EMPTY );

    if ( loading ) loading.classList.add( TT.DOM.CLASS_HIDDEN );
    if ( workingSet ) workingSet.classList.remove( TT.DOM.CLASS_HIDDEN );
    if ( empty ) empty.classList.add( TT.DOM.CLASS_HIDDEN );
}

function showTripEmpty() {
    var loading = document.getElementById( TT.DOM.ID_TRIP_LOADING );
    var workingSet = document.getElementById( TT.DOM.ID_WORKING_SET );
    var empty = document.getElementById( TT.DOM.ID_TRIP_EMPTY );

    if ( loading ) loading.classList.add( TT.DOM.CLASS_HIDDEN );
    if ( workingSet ) workingSet.classList.add( TT.DOM.CLASS_HIDDEN );
    if ( empty ) empty.classList.remove( TT.DOM.CLASS_HIDDEN );
}

function loadTrips() {
    showTripLoading();

    TTMessaging.send( TT.MESSAGE.TYPE_GET_TRIPS_WORKING_SET, {} )
        .then( function( response ) {
            if ( response && response.success ) {
                renderTrips(
                    response.data.workingSet,
                    response.data.pinnedTripUuid,
                    response.data.pinTimestamp
                );
            } else {
                showTripEmpty();
                var errorMsg = response && response.error ? response.error : 'Unknown error';
                addLocalDebugEntry( 'error', 'Load trips failed: ' + errorMsg );
            }
        })
        .catch( function( error ) {
            showTripEmpty();
            addLocalDebugEntry( 'error', 'Load trips error: ' + error.message );
        });
}

/**
 * Render the unified working set trip list.
 * @param {Array} workingSet - Array of trip objects sorted by recency.
 * @param {string|null} pinnedTripUuid - UUID of pinned trip, or null if auto mode.
 * @param {string|null} pinTimestamp - ISO timestamp when trip was pinned.
 */
function renderTrips( workingSet, pinnedTripUuid, pinTimestamp ) {
    if ( !workingSet || workingSet.length === 0 ) {
        showTripEmpty();
        return;
    }

    // Determine current trip: pinned or most recent
    var currentTripUuid = pinnedTripUuid || workingSet[0].uuid;

    // Store current trip for details panel
    var foundTrip = workingSet.find( function( t ) {
        return t.uuid === currentTripUuid;
    }) || workingSet[0];
    currentTrip = foundTrip;

    // Render unified trip list
    var tripList = document.getElementById( TT.DOM.ID_TRIP_LIST );
    if ( tripList ) {
        tripList.innerHTML = '';

        workingSet.forEach( function( trip ) {
            var isCurrent = trip.uuid === currentTripUuid;
            var isPinned = trip.uuid === pinnedTripUuid;
            var row = createTripRow( trip, isCurrent, isPinned );
            tripList.appendChild( row );
        });
    }

    // Check and show stale pin warning if needed
    checkStalePinWarning( pinnedTripUuid, pinTimestamp );

    showTripContent();
}

/**
 * Create a trip row element with pin control, title, GMM status, and info button.
 * @param {Object} trip - The trip object.
 * @param {boolean} isCurrent - Whether this is the current trip.
 * @param {boolean} isPinned - Whether this trip is pinned.
 * @returns {HTMLElement} The trip row element.
 */
function createTripRow( trip, isCurrent, isPinned ) {
    var row = document.createElement( 'div' );
    row.className = TT.DOM.CLASS_TRIP_ROW;
    if ( isCurrent ) {
        row.classList.add( TT.DOM.CLASS_TRIP_CURRENT );
    }
    row.setAttribute( 'data-trip-uuid', trip.uuid );

    // Anchor control button (pin/unpin trip)
    var pinBtn = document.createElement( 'button' );
    pinBtn.className = TT.DOM.CLASS_PIN_CONTROL;
    pinBtn.setAttribute( 'data-pinned', isPinned ? 'true' : 'false' );
    pinBtn.title = isPinned ? 'Release anchor' : 'Anchor as current';
    // Anchor icon: ring at top, vertical shaft, crossbar, curved flukes at bottom
    pinBtn.innerHTML = isPinned
        ? '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="5" r="3"/><line x1="12" y1="8" x2="12" y2="21"/><line x1="5" y1="12" x2="19" y2="12"/><path d="M5 19c2.5 2.5 4.5 3 7 3s4.5-.5 7-3"/></svg>'
        : '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="5" r="3"/><line x1="12" y1="8" x2="12" y2="21"/><line x1="5" y1="12" x2="19" y2="12"/><path d="M5 19c2.5 2.5 4.5 3 7 3s4.5-.5 7-3"/></svg>';

    pinBtn.addEventListener( 'click', function( e ) {
        e.stopPropagation();
        handlePinClick( trip.uuid, isPinned );
    });

    // Trip content area (title + GMM status)
    var content = document.createElement( 'div' );
    content.className = 'tt-trip-content';

    var title = document.createElement( 'span' );
    title.className = 'tt-trip-title';
    title.textContent = trip.title || 'Loading...';

    var gmmStatus = document.createElement( 'span' );
    gmmStatus.className = 'tt-gmm-status';
    if ( trip.gmm_map_id ) {
        gmmStatus.classList.add( TT.DOM.CLASS_GMM_LINKED );
        gmmStatus.title = 'Map linked';
        gmmStatus.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path><circle cx="12" cy="10" r="3"></circle></svg>';
    } else {
        gmmStatus.classList.add( TT.DOM.CLASS_GMM_UNLINKED );
        gmmStatus.title = 'No map linked';
        gmmStatus.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path><circle cx="12" cy="10" r="3"></circle><line x1="4" y1="4" x2="20" y2="20" stroke-width="2"></line></svg>';
    }

    content.appendChild( title );
    content.appendChild( gmmStatus );

    // Info button
    var infoBtn = document.createElement( 'button' );
    infoBtn.className = 'tt-trip-info-btn';
    infoBtn.title = 'Trip details';
    infoBtn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>';
    infoBtn.addEventListener( 'click', function( e ) {
        e.stopPropagation();
        showTripDetailsPanel( trip );
    });

    // Click on row -> visit map or show create dialog
    row.addEventListener( 'click', function() {
        handleTripRowClick( trip );
    });

    row.appendChild( pinBtn );
    row.appendChild( content );
    row.appendChild( infoBtn );

    return row;
}

/**
 * Handle pin button click - toggle pin state.
 * @param {string} tripUuid - The trip UUID.
 * @param {boolean} isCurrentlyPinned - Whether the trip is currently pinned.
 */
function handlePinClick( tripUuid, isCurrentlyPinned ) {
    if ( isCurrentlyPinned ) {
        // Unpin - return to auto mode
        TTMessaging.send( TT.MESSAGE.TYPE_SET_PINNED_TRIP, { uuid: null } )
            .then( function( response ) {
                if ( response && response.success ) {
                    addLocalDebugEntry( 'info', 'Trip unpinned, returned to auto mode' );
                    loadTrips();
                }
            });
    } else {
        // Pin this trip
        TTMessaging.send( TT.MESSAGE.TYPE_SET_PINNED_TRIP, { uuid: tripUuid } )
            .then( function( response ) {
                if ( response && response.success ) {
                    addLocalDebugEntry( 'info', 'Trip pinned: ' + tripUuid );
                    loadTrips();
                }
            });
    }
}

/**
 * Handle click on trip row - visit map or show create dialog.
 * @param {Object} trip - The trip object.
 */
function handleTripRowClick( trip ) {
    if ( trip.gmm_map_id ) {
        // Has map - open it
        openGmmMap( trip.gmm_map_id );
    } else {
        // No map - show trip details with map options
        showTripDetailsPanel( trip );
    }
}

/**
 * Check if pin is stale and show warning if needed.
 * @param {string|null} pinnedTripUuid - Pinned trip UUID.
 * @param {string|null} pinTimestamp - When trip was pinned.
 */
function checkStalePinWarning( pinnedTripUuid, pinTimestamp ) {
    var warningEl = document.getElementById( TT.DOM.ID_STALE_PIN_WARNING );
    if ( !warningEl ) return;

    // Only show warning if there is both a pinned trip AND a valid timestamp
    if ( !pinnedTripUuid || !pinTimestamp ) {
        warningEl.classList.add( TT.DOM.CLASS_HIDDEN );
        return;
    }

    // Validate timestamp is a parseable date
    var pinnedAt = new Date( pinTimestamp ).getTime();
    if ( isNaN( pinnedAt ) || pinnedAt <= 0 ) {
        warningEl.classList.add( TT.DOM.CLASS_HIDDEN );
        return;
    }

    // Check if pin is stale
    var age = Date.now() - pinnedAt;
    var thresholdMs = TT.CONFIG.PIN_STALE_THRESHOLD_DAYS * 24 * 60 * 60 * 1000;

    if ( age > thresholdMs ) {
        warningEl.classList.remove( TT.DOM.CLASS_HIDDEN );
    } else {
        warningEl.classList.add( TT.DOM.CLASS_HIDDEN );
    }
}

/**
 * Handle stale pin dismiss button click.
 */
function handleStalePinDismiss() {
    TTMessaging.send( TT.MESSAGE.TYPE_RESET_PIN_TIMESTAMP, {} )
        .then( function( response ) {
            if ( response && response.success ) {
                addLocalDebugEntry( 'info', 'Pin timestamp reset' );
                var warningEl = document.getElementById( TT.DOM.ID_STALE_PIN_WARNING );
                if ( warningEl ) {
                    warningEl.classList.add( TT.DOM.CLASS_HIDDEN );
                }
            }
        });
}

function switchToTrip( trip ) {
    TTMessaging.send( TT.MESSAGE.TYPE_SET_CURRENT_TRIP, { trip: trip } )
        .then( function( response ) {
            if ( response && response.success ) {
                addLocalDebugEntry( 'info', 'Switched to trip: ' + trip.title );
                loadTrips();
                // If trip has a linked GMM map, navigate to it
                if ( trip.gmm_map_id ) {
                    openGmmMap( trip.gmm_map_id );
                }
            } else {
                var errorMsg = response && response.error ? response.error : 'Unknown error';
                addLocalDebugEntry( 'error', 'Switch trip failed: ' + errorMsg );
            }
        })
        .catch( function( error ) {
            addLocalDebugEntry( 'error', 'Switch trip error: ' + error.message );
        });
}

// =============================================================================
// More Trips Panel
// =============================================================================

function showMoreTripsPanel() {
    var panel = document.getElementById( TT.DOM.ID_MORE_TRIPS_PANEL );
    if ( panel ) {
        panel.classList.remove( TT.DOM.CLASS_HIDDEN );
        requestAnimationFrame( function() {
            panel.classList.add( TT.DOM.CLASS_VISIBLE );
        });
    }

    loadAllTrips();
}

function hideMoreTripsPanel() {
    var panel = document.getElementById( TT.DOM.ID_MORE_TRIPS_PANEL );
    if ( panel ) {
        panel.classList.remove( TT.DOM.CLASS_VISIBLE );
        panel.addEventListener( 'transitionend', function handler() {
            panel.classList.add( TT.DOM.CLASS_HIDDEN );
            panel.removeEventListener( 'transitionend', handler );
        });
    }
}

// =============================================================================
// Trip Details Panel
// =============================================================================

// The trip currently being viewed in the details panel
var currentViewedTrip = null;

/**
 * Show the trip details panel for a given trip.
 * @param {Object} trip - The trip to show details for.
 */
function showTripDetailsPanel( trip ) {
    var panel = document.getElementById( TT.DOM.ID_TRIP_DETAILS_PANEL );
    if ( panel ) {
        currentViewedTrip = trip;
        populateTripDetails( trip );
        panel.classList.remove( TT.DOM.CLASS_HIDDEN );
        requestAnimationFrame( function() {
            panel.classList.add( TT.DOM.CLASS_VISIBLE );
        });
    }

}

function hideTripDetailsPanel() {
    var panel = document.getElementById( TT.DOM.ID_TRIP_DETAILS_PANEL );
    if ( panel ) {
        panel.classList.remove( TT.DOM.CLASS_VISIBLE );
        panel.addEventListener( 'transitionend', function handler() {
            panel.classList.add( TT.DOM.CLASS_HIDDEN );
            panel.removeEventListener( 'transitionend', handler );
        });
    }
}

/**
 * Populate the trip details panel with trip data.
 * @param {Object} trip - The trip to display.
 */
function populateTripDetails( trip ) {
    if ( !trip ) return;

    var titleEl = document.getElementById( TT.DOM.ID_TRIP_DETAILS_TITLE );
    var descEl = document.getElementById( TT.DOM.ID_TRIP_DETAILS_DESCRIPTION );
    var uuidEl = document.getElementById( TT.DOM.ID_TRIP_DETAILS_UUID );
    var gmmIdEl = document.getElementById( TT.DOM.ID_TRIP_DETAILS_GMM_ID );
    var gmmRow = document.getElementById( TT.DOM.ID_TRIP_DETAILS_GMM_ROW );
    var linkedActionsEl = document.getElementById( TT.DOM.ID_TRIP_DETAILS_ACTIONS );
    var unlinkedActionsEl = document.getElementById( TT.DOM.ID_TRIP_DETAILS_ACTIONS_UNLINKED );
    var linkCurrentBtn = document.getElementById( TT.DOM.ID_TRIP_DETAILS_LINK_CURRENT_BTN );
    var linkHint = document.getElementById( TT.DOM.ID_TRIP_DETAILS_LINK_HINT );

    if ( titleEl ) titleEl.textContent = trip.title;
    if ( descEl ) descEl.textContent = trip.description || '';
    if ( uuidEl ) uuidEl.textContent = trip.uuid;

    if ( trip.gmm_map_id ) {
        // LINKED: Show sync/unlink actions
        if ( gmmIdEl ) gmmIdEl.textContent = trip.gmm_map_id;
        if ( gmmRow ) gmmRow.classList.remove( TT.DOM.CLASS_HIDDEN );
        if ( linkedActionsEl ) linkedActionsEl.classList.remove( TT.DOM.CLASS_HIDDEN );
        if ( unlinkedActionsEl ) unlinkedActionsEl.classList.add( TT.DOM.CLASS_HIDDEN );
    } else {
        // UNLINKED: Show create/link actions
        if ( gmmRow ) gmmRow.classList.add( TT.DOM.CLASS_HIDDEN );
        if ( linkedActionsEl ) linkedActionsEl.classList.add( TT.DOM.CLASS_HIDDEN );
        if ( unlinkedActionsEl ) unlinkedActionsEl.classList.remove( TT.DOM.CLASS_HIDDEN );

        // Show "Link to Current Map" only if on unlinked GMM page
        var canLinkCurrent = currentPageInfo &&
                             currentPageInfo.site === 'gmm' &&
                             currentPageInfo.mapId &&
                             currentGmmLinkStatus &&
                             !currentGmmLinkStatus.isLinked;

        if ( linkCurrentBtn ) {
            if ( canLinkCurrent ) {
                linkCurrentBtn.classList.remove( TT.DOM.CLASS_HIDDEN );
                linkCurrentBtn.textContent = 'Link to ' + ( currentPageInfo.mapTitle || 'Current Map' );
            } else {
                linkCurrentBtn.classList.add( TT.DOM.CLASS_HIDDEN );
            }
        }

        // Show hint when not on linkable GMM page
        if ( linkHint ) {
            if ( canLinkCurrent ) {
                linkHint.classList.add( TT.DOM.CLASS_HIDDEN );
            } else {
                linkHint.classList.remove( TT.DOM.CLASS_HIDDEN );
            }
        }
    }
}

/**
 * Handle Sync Map button click.
 * Sends sync message to GMM content script if map is open.
 * Uses currentViewedTrip (the trip shown in details panel).
 */
function handleSyncLocations() {
    var trip = currentViewedTrip;
    if ( !trip ) {
        addLocalDebugEntry( 'warning', 'Sync: No trip selected' );
        return;
    }

    if ( !trip.gmm_map_id ) {
        addLocalDebugEntry( 'warning', 'Sync: Trip has no linked map' );
        return;
    }

    addLocalDebugEntry( 'info', 'Sync Map requested for trip: ' + trip.title );

    TTMessaging.send( TT.MESSAGE.TYPE_GMM_SYNC_LOCATIONS, {
        tripUuid: trip.uuid,
        tripTitle: trip.title,
        mapId: trip.gmm_map_id
    })
    .then( function( response ) {
        if ( response && response.success ) {
            addLocalDebugEntry( 'info', 'Sync dialog opened' );
            window.close();
        } else if ( response && response.data && response.data.code === 'MAP_NOT_OPEN' ) {
            // Map tab not open - prompt user
            // eslint-disable-next-line no-alert
            if ( confirm( 'The map must be open to sync.\n\nOpen the map now?' ) ) {
                openGmmMap( trip.gmm_map_id );
            }
        } else {
            var errorMsg = response && response.data && response.data.error
                ? response.data.error : 'Unknown error';
            addLocalDebugEntry( 'error', 'Sync failed: ' + errorMsg );
        }
    })
    .catch( function( error ) {
        addLocalDebugEntry( 'error', 'Sync error: ' + error.message );
    });
}

/**
 * Handle Unlink Map button click.
 * Uses currentViewedTrip (the trip shown in details panel).
 */
function handleUnlinkMap() {
    var trip = currentViewedTrip;
    if ( !trip || !trip.gmm_map_id ) return;

    // eslint-disable-next-line no-alert
    if ( !confirm( 'Unlink the Google My Maps map from this trip?' ) ) {
        return;
    }

    TTMessaging.send( TT.MESSAGE.TYPE_GMM_UNLINK_MAP, {
        tripUuid: trip.uuid
    })
    .then( function( response ) {
        if ( response && response.success ) {
            trip.gmm_map_id = null;
            currentViewedTrip = trip;
            populateTripDetails( trip );
            // Refresh the trip list to update GMM status
            loadTrips();
            addLocalDebugEntry( 'info', 'Map unlinked from trip' );
        } else {
            var errorMsg = response && response.error ? response.error : 'Unknown error';
            addLocalDebugEntry( 'error', 'Failed to unlink map: ' + errorMsg );
        }
    })
    .catch( function( error ) {
        addLocalDebugEntry( 'error', 'Unlink map error: ' + error.message );
    });
}

/**
 * Handle "Create Map" button click from trip details panel.
 * Uses currentViewedTrip (the trip shown in details panel).
 */
function handleCreateMapFromDetails() {
    var trip = currentViewedTrip;
    if ( !trip ) return;

    // Set currentTrip for confirmCreateMap to use
    currentTrip = trip;

    hideTripDetailsPanel();
    showCreatingMapDialog( 'Creating map in Google My Maps...' );

    TTMessaging.send( TT.MESSAGE.TYPE_GMM_CREATE_MAP, {
        tripUuid: trip.uuid,
        tripTitle: trip.title
    })
    .then( function( response ) {
        hideCreatingMapDialog();

        if ( response && response.success ) {
            addLocalDebugEntry( 'info', 'Created GMM map: ' + response.data.mapId );

            // Update local trip data
            trip.gmm_map_id = response.data.mapId;
            currentTrip = trip;

            // Refresh trip list to show new link status
            loadTrips();

            // Close popup - user is now on the new map
            window.close();
        } else {
            var errorMsg = response && response.error ? response.error : 'Unknown error';
            addLocalDebugEntry( 'error', 'Create map failed: ' + errorMsg );
            // eslint-disable-next-line no-alert
            alert( 'Failed to create map: ' + errorMsg );
        }
    })
    .catch( function( error ) {
        hideCreatingMapDialog();
        addLocalDebugEntry( 'error', 'Create map error: ' + error.message );
        // eslint-disable-next-line no-alert
        alert( 'Failed to create map: ' + error.message );
    });
}

/**
 * Handle "Link to Current Map" button click from trip details panel.
 * Links the currently viewed trip to the current GMM page.
 * Uses currentViewedTrip (the trip shown in details panel).
 */
function handleLinkCurrentMapFromDetails() {
    var trip = currentViewedTrip;
    if ( !trip ) return;
    if ( !currentPageInfo || !currentPageInfo.mapId ) return;

    addLocalDebugEntry( 'info', 'Linking current map to trip: ' + trip.title );

    TTMessaging.send( TT.MESSAGE.TYPE_GMM_LINK_MAP, {
        tripUuid: trip.uuid,
        gmmMapId: currentPageInfo.mapId
    })
    .then( function( response ) {
        if ( response && response.success ) {
            addLocalDebugEntry( 'info', 'Map linked to trip: ' + trip.title );
            hideTripDetailsPanel();

            // Update local state
            currentGmmLinkStatus = { isLinked: true, tripUuid: trip.uuid };
            updateUIForCurrentPage();

            // Refresh trip list to show new link status
            loadTrips();

            // Show success panel with reload prompt
            showLinkSuccessPanel( 'Trip Linked to Map' );
        } else {
            var errorMsg = response && response.error ? response.error : 'Unknown error';
            addLocalDebugEntry( 'error', 'Link map failed: ' + errorMsg );
            // eslint-disable-next-line no-alert
            alert( 'Failed to link map: ' + errorMsg );
        }
    })
    .catch( function( error ) {
        addLocalDebugEntry( 'error', 'Link map error: ' + error.message );
        // eslint-disable-next-line no-alert
        alert( 'Failed to link map: ' + error.message );
    });
}

// =============================================================================
// Create Trip Panel
// =============================================================================

function showCreateTripPanel() {
    var panel = document.getElementById( TT.DOM.ID_CREATE_TRIP_PANEL );

    // Reset form
    if ( panel ) {
        resetCreateTripForm();
        panel.classList.remove( TT.DOM.CLASS_HIDDEN );
        requestAnimationFrame( function() {
            panel.classList.add( TT.DOM.CLASS_VISIBLE );
        });
    }

}

function hideCreateTripPanel() {
    var panel = document.getElementById( TT.DOM.ID_CREATE_TRIP_PANEL );
    if ( panel ) {
        panel.classList.remove( TT.DOM.CLASS_VISIBLE );
        panel.addEventListener( 'transitionend', function handler() {
            panel.classList.add( TT.DOM.CLASS_HIDDEN );
            panel.removeEventListener( 'transitionend', handler );
        });
    }
}

function resetCreateTripForm() {
    var titleInput = document.getElementById( TT.DOM.ID_CREATE_TRIP_TITLE_INPUT );
    var descInput = document.getElementById( TT.DOM.ID_CREATE_TRIP_DESC_INPUT );
    var errorEl = document.getElementById( TT.DOM.ID_CREATE_TRIP_ERROR );
    var submitBtn = document.getElementById( TT.DOM.ID_CREATE_TRIP_SUBMIT );

    if ( titleInput ) titleInput.value = '';
    if ( descInput ) descInput.value = '';
    if ( errorEl ) {
        errorEl.classList.add( TT.DOM.CLASS_HIDDEN );
        errorEl.textContent = '';
    }
    if ( submitBtn ) {
        submitBtn.disabled = false;
        submitBtn.classList.remove( 'tt-btn-loading' );
        submitBtn.textContent = 'Create Trip';
    }

    // Reset link choice to default (No)
    resetLinkChoice();
}

function showCreateTripError( message ) {
    var errorEl = document.getElementById( TT.DOM.ID_CREATE_TRIP_ERROR );
    if ( errorEl ) {
        errorEl.textContent = message;
        errorEl.classList.remove( TT.DOM.CLASS_HIDDEN );
    }
}

function handleCreateTripSubmit() {
    var titleInput = document.getElementById( TT.DOM.ID_CREATE_TRIP_TITLE_INPUT );
    var descInput = document.getElementById( TT.DOM.ID_CREATE_TRIP_DESC_INPUT );
    var submitBtn = document.getElementById( TT.DOM.ID_CREATE_TRIP_SUBMIT );
    var errorEl = document.getElementById( TT.DOM.ID_CREATE_TRIP_ERROR );

    // Hide previous error
    if ( errorEl ) errorEl.classList.add( TT.DOM.CLASS_HIDDEN );

    // Validate title
    var title = titleInput ? titleInput.value.trim() : '';
    if ( !title ) {
        showCreateTripError( 'Title is required' );
        if ( titleInput ) titleInput.focus();
        return;
    }

    var description = descInput ? descInput.value.trim() : '';

    // Check if user wants to link the current GMM map
    var gmmMapId = null;
    if ( isOnUnlinkedGmmPage() && isLinkMapSelected() ) {
        gmmMapId = currentPageInfo.mapId;
    }

    // Show loading state
    if ( submitBtn ) {
        submitBtn.disabled = true;
        submitBtn.classList.add( 'tt-btn-loading' );
        submitBtn.textContent = 'Creating';
    }

    var logMsg = gmmMapId
        ? 'Creating trip with map link: ' + title
        : 'Creating trip: ' + title;
    addLocalDebugEntry( 'info', logMsg );

    var requestData = {
        title: title,
        description: description
    };
    if ( gmmMapId ) {
        requestData.gmm_map_id = gmmMapId;
    }

    TTMessaging.send( TT.MESSAGE.TYPE_CREATE_AND_ACTIVATE_TRIP, requestData )
    .then( function( response ) {
        if ( response && response.success ) {
            addLocalDebugEntry( 'info', 'Trip created: ' + response.data.currentTripUuid );
            hideCreateTripPanel();

            // If we linked a map, update local state and show success panel
            if ( gmmMapId ) {
                currentGmmLinkStatus = { isLinked: true, tripUuid: response.data.currentTripUuid };
                updateUIForCurrentPage();

                // Show success panel with reload prompt
                showLinkSuccessPanel( 'Trip Created for Map' );
            }

            loadTrips();
        } else {
            var errorMsg = response && response.error ? response.error : 'Failed to create trip';
            showCreateTripError( errorMsg );
            addLocalDebugEntry( 'error', 'Create trip failed: ' + errorMsg );
            // Reset button state
            if ( submitBtn ) {
                submitBtn.disabled = false;
                submitBtn.classList.remove( 'tt-btn-loading' );
                submitBtn.textContent = 'Create Trip';
            }
        }
    })
    .catch( function( error ) {
        showCreateTripError( 'Unable to create trip. Please try again.' );
        addLocalDebugEntry( 'error', 'Create trip error: ' + error.message );
        // Reset button state
        if ( submitBtn ) {
            submitBtn.disabled = false;
            submitBtn.classList.remove( 'tt-btn-loading' );
            submitBtn.textContent = 'Create Trip';
        }
    });
}

function loadAllTrips() {
    var listEl = document.getElementById( TT.DOM.ID_MORE_TRIPS_LIST );
    var loadingEl = document.getElementById( TT.DOM.ID_MORE_TRIPS_LOADING );
    var errorEl = document.getElementById( TT.DOM.ID_MORE_TRIPS_ERROR );

    if ( listEl ) listEl.innerHTML = '';
    if ( loadingEl ) loadingEl.classList.remove( TT.DOM.CLASS_HIDDEN );
    if ( errorEl ) errorEl.classList.add( TT.DOM.CLASS_HIDDEN );

    TTMessaging.send( TT.MESSAGE.TYPE_GET_ALL_TRIPS, {} )
        .then( function( response ) {
            if ( loadingEl ) loadingEl.classList.add( TT.DOM.CLASS_HIDDEN );

            if ( !response || !response.success ) {
                var errorMsg = response && response.error ? response.error : 'Failed to load trips';
                if ( errorEl ) {
                    errorEl.textContent = errorMsg;
                    errorEl.classList.remove( TT.DOM.CLASS_HIDDEN );
                }
                addLocalDebugEntry( 'error', 'Load all trips failed: ' + errorMsg );
                return;
            }

            renderAllTrips( response.data.trips );
        })
        .catch( function( error ) {
            if ( loadingEl ) loadingEl.classList.add( TT.DOM.CLASS_HIDDEN );
            if ( errorEl ) {
                errorEl.textContent = error.message;
                errorEl.classList.remove( TT.DOM.CLASS_HIDDEN );
            }
            addLocalDebugEntry( 'error', 'Load all trips error: ' + error.message );
        });
}

function renderAllTrips( trips ) {
    var listEl = document.getElementById( TT.DOM.ID_MORE_TRIPS_LIST );
    if ( !listEl ) {
        return;
    }

    listEl.innerHTML = '';

    if ( !trips || trips.length === 0 ) {
        var emptyDiv = document.createElement( 'div' );
        emptyDiv.className = 'tt-empty-message';
        emptyDiv.textContent = 'No trips found.';
        listEl.appendChild( emptyDiv );
        return;
    }

    trips.forEach( function( trip ) {
        var item = document.createElement( 'div' );
        item.className = 'tt-trip-item';

        var title = document.createElement( 'span' );
        title.className = 'tt-trip-item-title';
        title.textContent = trip.title;
        item.appendChild( title );

        item.addEventListener( 'click', function() {
            selectTripFromList( trip );
        });

        listEl.appendChild( item );
    });
}

function selectTripFromList( trip ) {
    // Use existing setCurrentTrip which adds to working set AND sets as current
    TTMessaging.send( TT.MESSAGE.TYPE_SET_CURRENT_TRIP, { trip: trip } )
        .then( function( response ) {
            if ( response && response.success ) {
                addLocalDebugEntry( 'info', 'Selected trip from list: ' + trip.title );
                hideMoreTripsPanel();
                loadTrips();
                // If trip has a linked GMM map, navigate to it
                if ( trip.gmm_map_id ) {
                    openGmmMap( trip.gmm_map_id );
                }
            } else {
                var errorMsg = response && response.error ? response.error : 'Unknown error';
                addLocalDebugEntry( 'error', 'Select trip failed: ' + errorMsg );
            }
        })
        .catch( function( error ) {
            addLocalDebugEntry( 'error', 'Select trip error: ' + error.message );
        });
}

// =============================================================================
// GMM Map Management
// =============================================================================

// Current trip for GMM operations
var currentTrip = null;

// Current page detection state
var currentPageInfo = null;      // Result from TTPageInfo.detectCurrentPage()
var currentGmmLinkStatus = null; // { isLinked, tripUuid } - only if on GMM page

/**
 * Detect current page and check GMM link status if applicable.
 * Called during popup initialization.
 */
function detectCurrentPage() {
    TTPageInfo.detectCurrentPage()
        .then( function( pageInfo ) {
            currentPageInfo = pageInfo;
            if ( pageInfo && pageInfo.site === 'gmm' ) {
                addLocalDebugEntry( 'info', 'On GMM page: ' + pageInfo.mapId );
                // Fetch map info from content script to get map title
                return fetchGmmMapInfo().then( function( mapInfo ) {
                    if ( mapInfo && mapInfo.mapTitle ) {
                        currentPageInfo.mapTitle = mapInfo.mapTitle;
                    }
                    return checkGmmMapLinkStatus( pageInfo.mapId );
                });
            }
            return null;
        })
        .then( function( linkStatus ) {
            currentGmmLinkStatus = linkStatus;
            if ( linkStatus ) {
                addLocalDebugEntry( 'info', 'GMM map link status: ' +
                    ( linkStatus.isLinked ? 'linked to ' + linkStatus.tripUuid : 'not linked' ) );
            }
            updateUIForCurrentPage();
        })
        .catch( function( error ) {
            addLocalDebugEntry( 'error', 'Page detection error: ' + error.message );
        });
}

/**
 * Fetch GMM map info from content script.
 * @returns {Promise<Object|null>} { mapId, url, mapTitle } or null on error.
 */
function fetchGmmMapInfo() {
    return TTMessaging.send( TT.MESSAGE.TYPE_GMM_GET_MAP_INFO, {} )
        .then( function( response ) {
            if ( response && response.success ) {
                return response.data;
            }
            return null;
        })
        .catch( function() {
            return null;
        });
}

/**
 * Check if a GMM map is linked to any trip.
 * @param {string} mapId - The GMM map ID.
 * @returns {Promise<Object>} { isLinked, tripUuid }
 */
function checkGmmMapLinkStatus( mapId ) {
    return TTMessaging.send( TT.MESSAGE.TYPE_IS_GMM_MAP_LINKED, { gmm_map_id: mapId } )
        .then( function( response ) {
            if ( response && response.success ) {
                return {
                    isLinked: response.data.isLinked,
                    tripUuid: response.data.tripUuid
                };
            }
            return { isLinked: false, tripUuid: null };
        })
        .catch( function() {
            return { isLinked: false, tripUuid: null };
        });
}

/**
 * Update UI elements based on current page context.
 * Shows/hides GMM-specific elements.
 */
function updateUIForCurrentPage() {
    // Show/hide "Link Map" action container based on unlinked GMM page
    var linkMapAction = document.getElementById( TT.DOM.ID_LINK_MAP_ACTION );
    if ( linkMapAction ) {
        var showLinkMap = currentPageInfo &&
                          currentPageInfo.site === 'gmm' &&
                          currentGmmLinkStatus &&
                          !currentGmmLinkStatus.isLinked;
        linkMapAction.classList.toggle( TT.DOM.CLASS_HIDDEN, !showLinkMap );
    }

    // Show/hide link choice in create trip form
    updateCreateTripLinkChoice();
}

/**
 * Check if we're on an unlinked GMM page.
 * @returns {boolean}
 */
function isOnUnlinkedGmmPage() {
    return currentPageInfo &&
           currentPageInfo.site === 'gmm' &&
           currentGmmLinkStatus &&
           !currentGmmLinkStatus.isLinked;
}

/**
 * Set up event listeners for GMM features.
 */
function setupGmmEventListeners() {
    // Currently no event listeners needed here
    // (create map dialog was removed - now handled via trip details panel)
}

/**
 * Open a GMM map in browser.
 * @param {string} mapId - The GMM map ID.
 */
function openGmmMap( mapId ) {
    TTMessaging.send( TT.MESSAGE.TYPE_GMM_OPEN_MAP, { mapId: mapId } )
        .then( function( response ) {
            if ( response && response.success ) {
                addLocalDebugEntry( 'info', 'Opened GMM map: ' + mapId );
                // Close popup after opening
                window.close();
            } else {
                var errorMsg = response && response.error ? response.error : 'Unknown error';
                addLocalDebugEntry( 'error', 'Open map failed: ' + errorMsg );
            }
        })
        .catch( function( error ) {
            addLocalDebugEntry( 'error', 'Open map error: ' + error.message );
        });
}

/**
 * Show the creating map progress dialog.
 * @param {string} message - Status message to display.
 */
function showCreatingMapDialog( message ) {
    var dialog = document.getElementById( TT.DOM.ID_CREATING_MAP_DIALOG );
    var statusEl = document.getElementById( TT.DOM.ID_CREATING_MAP_STATUS );

    if ( statusEl && message ) {
        statusEl.textContent = message;
    }

    if ( dialog ) {
        dialog.classList.remove( TT.DOM.CLASS_HIDDEN );
    }
}

/**
 * Hide the creating map progress dialog.
 */
function hideCreatingMapDialog() {
    var dialog = document.getElementById( TT.DOM.ID_CREATING_MAP_DIALOG );
    if ( dialog ) {
        dialog.classList.add( TT.DOM.CLASS_HIDDEN );
    }
}

// =============================================================================
// Link Map Panel and Create Trip Link Choice
// =============================================================================

/**
 * Update the link choice visibility in create trip form.
 * Shows choice only when on an unlinked GMM page.
 */
function updateCreateTripLinkChoice() {
    var linkChoiceEl = document.getElementById( TT.DOM.ID_CREATE_TRIP_LINK_CHOICE );
    if ( linkChoiceEl ) {
        var showChoice = isOnUnlinkedGmmPage();
        linkChoiceEl.classList.toggle( TT.DOM.CLASS_HIDDEN, !showChoice );
    }
}

/**
 * Set up event listeners for Link Map button and panel.
 */
function setupLinkMapEventListeners() {
    // Link Map button
    var linkMapBtn = document.getElementById( TT.DOM.ID_LINK_MAP_BTN );
    if ( linkMapBtn ) {
        linkMapBtn.addEventListener( 'click', function() {
            showLinkMapPanel();
        });
    }

    // Link Map panel back button
    var linkMapBackBtn = document.getElementById( TT.DOM.ID_LINK_MAP_BACK );
    if ( linkMapBackBtn ) {
        linkMapBackBtn.addEventListener( 'click', function() {
            hideLinkMapPanel();
        });
    }

    // Create trip link choice buttons
    var linkNoBtn = document.getElementById( TT.DOM.ID_CREATE_TRIP_LINK_NO );
    var linkYesBtn = document.getElementById( TT.DOM.ID_CREATE_TRIP_LINK_YES );

    if ( linkNoBtn ) {
        linkNoBtn.addEventListener( 'click', function() {
            selectLinkChoice( false );
        });
    }

    if ( linkYesBtn ) {
        linkYesBtn.addEventListener( 'click', function() {
            selectLinkChoice( true );
        });
    }
}

/**
 * Select link choice in create trip form.
 * @param {boolean} linkSelected - True to link, false to not link.
 */
function selectLinkChoice( linkSelected ) {
    var linkNoBtn = document.getElementById( TT.DOM.ID_CREATE_TRIP_LINK_NO );
    var linkYesBtn = document.getElementById( TT.DOM.ID_CREATE_TRIP_LINK_YES );

    if ( linkNoBtn && linkYesBtn ) {
        linkNoBtn.setAttribute( 'data-selected', !linkSelected );
        linkYesBtn.setAttribute( 'data-selected', linkSelected );
    }
}

/**
 * Check if user selected to link the map when creating trip.
 * @returns {boolean}
 */
function isLinkMapSelected() {
    var linkYesBtn = document.getElementById( TT.DOM.ID_CREATE_TRIP_LINK_YES );
    return linkYesBtn && linkYesBtn.getAttribute( 'data-selected' ) === 'true';
}

/**
 * Reset the link choice to default (No).
 */
function resetLinkChoice() {
    selectLinkChoice( false );
}

/**
 * Show the Link Map panel.
 */
function showLinkMapPanel() {
    var panel = document.getElementById( TT.DOM.ID_LINK_MAP_PANEL );
    if ( panel ) {
        panel.classList.remove( TT.DOM.CLASS_HIDDEN );
        requestAnimationFrame( function() {
            panel.classList.add( TT.DOM.CLASS_VISIBLE );
        });
    }

    loadUnlinkedTrips();
}

/**
 * Hide the Link Map panel.
 */
function hideLinkMapPanel() {
    var panel = document.getElementById( TT.DOM.ID_LINK_MAP_PANEL );
    if ( panel ) {
        panel.classList.remove( TT.DOM.CLASS_VISIBLE );
        panel.addEventListener( 'transitionend', function handler() {
            panel.classList.add( TT.DOM.CLASS_HIDDEN );
            panel.removeEventListener( 'transitionend', handler );
        });
    }
}

/**
 * Load trips that don't have maps linked (for Link Map panel).
 */
function loadUnlinkedTrips() {
    var listEl = document.getElementById( TT.DOM.ID_LINK_MAP_LIST );
    var loadingEl = document.getElementById( TT.DOM.ID_LINK_MAP_LOADING );
    var errorEl = document.getElementById( TT.DOM.ID_LINK_MAP_ERROR );
    var emptyEl = document.getElementById( TT.DOM.ID_LINK_MAP_EMPTY );

    if ( listEl ) listEl.innerHTML = '';
    if ( loadingEl ) loadingEl.classList.remove( TT.DOM.CLASS_HIDDEN );
    if ( errorEl ) errorEl.classList.add( TT.DOM.CLASS_HIDDEN );
    if ( emptyEl ) emptyEl.classList.add( TT.DOM.CLASS_HIDDEN );

    TTMessaging.send( TT.MESSAGE.TYPE_GET_ALL_TRIPS, {} )
        .then( function( response ) {
            if ( loadingEl ) loadingEl.classList.add( TT.DOM.CLASS_HIDDEN );

            if ( !response || !response.success ) {
                var errorMsg = response && response.error ? response.error : 'Failed to load trips';
                if ( errorEl ) {
                    errorEl.textContent = errorMsg;
                    errorEl.classList.remove( TT.DOM.CLASS_HIDDEN );
                }
                addLocalDebugEntry( 'error', 'Load unlinked trips failed: ' + errorMsg );
                return;
            }

            // Filter to only trips without gmm_map_id
            var unlinkedTrips = ( response.data.trips || [] ).filter( function( trip ) {
                return !trip.gmm_map_id;
            });

            renderUnlinkedTrips( unlinkedTrips );
        })
        .catch( function( error ) {
            if ( loadingEl ) loadingEl.classList.add( TT.DOM.CLASS_HIDDEN );
            if ( errorEl ) {
                errorEl.textContent = error.message;
                errorEl.classList.remove( TT.DOM.CLASS_HIDDEN );
            }
            addLocalDebugEntry( 'error', 'Load unlinked trips error: ' + error.message );
        });
}

/**
 * Render list of unlinked trips in the Link Map panel.
 * @param {Array} trips - Trips without gmm_map_id.
 */
function renderUnlinkedTrips( trips ) {
    var listEl = document.getElementById( TT.DOM.ID_LINK_MAP_LIST );
    var emptyEl = document.getElementById( TT.DOM.ID_LINK_MAP_EMPTY );

    if ( !listEl ) return;

    listEl.innerHTML = '';

    if ( !trips || trips.length === 0 ) {
        if ( emptyEl ) emptyEl.classList.remove( TT.DOM.CLASS_HIDDEN );
        return;
    }

    trips.forEach( function( trip ) {
        var item = document.createElement( 'div' );
        item.className = 'tt-trip-item';

        var title = document.createElement( 'span' );
        title.className = 'tt-trip-item-title';
        title.textContent = trip.title;
        item.appendChild( title );

        item.addEventListener( 'click', function() {
            handleLinkMapToTrip( trip );
        });

        listEl.appendChild( item );
    });
}

/**
 * Handle linking current map to a trip.
 * @param {Object} trip - The trip to link the map to.
 */
function handleLinkMapToTrip( trip ) {
    if ( !currentPageInfo || currentPageInfo.site !== 'gmm' || !currentPageInfo.mapId ) {
        addLocalDebugEntry( 'error', 'Cannot link: not on a GMM page' );
        return;
    }

    addLocalDebugEntry( 'info', 'Linking map to trip: ' + trip.title );

    TTMessaging.send( TT.MESSAGE.TYPE_GMM_LINK_MAP, {
        tripUuid: trip.uuid,
        gmmMapId: currentPageInfo.mapId
    })
    .then( function( response ) {
        if ( response && response.success ) {
            addLocalDebugEntry( 'info', 'Map linked to trip: ' + trip.title );
            hideLinkMapPanel();

            // Update local state
            currentGmmLinkStatus = { isLinked: true, tripUuid: trip.uuid };
            updateUIForCurrentPage();

            // Use the updated trip from response (has gmm_map_id set)
            var updatedTrip = response.data.trip;

            // Refresh trip display and set this as current trip
            TTMessaging.send( TT.MESSAGE.TYPE_SET_CURRENT_TRIP, { trip: updatedTrip } )
                .then( function( setResponse ) {
                    if ( setResponse && setResponse.success ) {
                        loadTrips();
                    }
                });

            // Show success panel with reload prompt
            showLinkSuccessPanel( 'Trip Linked to Map' );
        } else {
            var errorMsg = response && response.error ? response.error : 'Unknown error';
            addLocalDebugEntry( 'error', 'Link map failed: ' + errorMsg );
            alert( 'Failed to link map: ' + errorMsg );
        }
    })
    .catch( function( error ) {
        addLocalDebugEntry( 'error', 'Link map error: ' + error.message );
        alert( 'Failed to link map: ' + error.message );
    });
}

// =============================================================================
// Link Success Panel
// =============================================================================

/**
 * Set up event listeners for the link success panel.
 */
function setupLinkSuccessEventListeners() {
    var reloadBtn = document.getElementById( TT.DOM.ID_LINK_SUCCESS_RELOAD );
    if ( reloadBtn ) {
        reloadBtn.addEventListener( 'click', function() {
            // Reload the current tab and close popup
            chrome.tabs.query( { active: true, currentWindow: true }, function( tabs ) {
                if ( tabs && tabs.length > 0 ) {
                    chrome.tabs.reload( tabs[0].id );
                }
                window.close();
            });
        });
    }

    var dismissBtn = document.getElementById( TT.DOM.ID_LINK_SUCCESS_DISMISS );
    if ( dismissBtn ) {
        dismissBtn.addEventListener( 'click', function() {
            hideLinkSuccessPanel();
        });
    }
}

/**
 * Show the link success panel with a custom title.
 * @param {string} title - The success message title.
 */
function showLinkSuccessPanel( title ) {
    var panel = document.getElementById( TT.DOM.ID_LINK_SUCCESS_PANEL );
    var titleEl = document.getElementById( TT.DOM.ID_LINK_SUCCESS_TITLE );

    if ( titleEl && title ) {
        titleEl.textContent = title;
    }

    if ( panel ) {
        panel.classList.remove( TT.DOM.CLASS_HIDDEN );
    }
}

/**
 * Hide the link success panel.
 */
function hideLinkSuccessPanel() {
    var panel = document.getElementById( TT.DOM.ID_LINK_SUCCESS_PANEL );
    if ( panel ) {
        panel.classList.add( TT.DOM.CLASS_HIDDEN );
    }
}
