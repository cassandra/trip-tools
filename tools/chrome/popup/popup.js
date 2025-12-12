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
        var header = document.querySelector( '.' + TT.DOM.CLASS_POPUP_HEADER );
        if ( header ) {
            header.classList.add( TT.DOM.CLASS_DEV_MODE );
        }

        var headerIcon = document.getElementById( TT.DOM.ID_HEADER_ICON );
        if ( headerIcon ) {
            headerIcon.src = TT.CONFIG.ICON_DEV_48;
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

    var header = document.getElementById( TT.DOM.ID_QUICK_SETTINGS_HEADER );
    if ( header && TT.CONFIG.IS_DEVELOPMENT ) {
        header.classList.add( TT.DOM.CLASS_DEV_MODE );
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
            openAuthorizePage();
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

    var tripDetailsBtn = document.getElementById( TT.DOM.ID_TRIP_DETAILS_BTN );
    if ( tripDetailsBtn ) {
        tripDetailsBtn.addEventListener( 'click', function( e ) {
            e.stopPropagation();
            showTripDetailsPanel();
        });
    }

    var tripDetailsBackBtn = document.getElementById( TT.DOM.ID_TRIP_DETAILS_BACK );
    if ( tripDetailsBackBtn ) {
        tripDetailsBackBtn.addEventListener( 'click', function() {
            hideTripDetailsPanel();
        });
    }

    var syncLocationsBtn = document.getElementById( TT.DOM.ID_TRIP_DETAILS_SYNC_BTN );
    if ( syncLocationsBtn ) {
        syncLocationsBtn.addEventListener( 'click', handleSyncLocations );
    }

    var unlinkMapBtn = document.getElementById( TT.DOM.ID_TRIP_DETAILS_UNLINK_BTN );
    if ( unlinkMapBtn ) {
        unlinkMapBtn.addEventListener( 'click', handleUnlinkMap );
    }
}

function openAuthorizePage() {
    var defaultUrl = TT.CONFIG.IS_DEVELOPMENT
        ? TT.CONFIG.DEFAULT_SERVER_URL_DEV
        : TT.CONFIG.DEFAULT_SERVER_URL_PROD;

    TTStorage.get( TT.STORAGE.KEY_SERVER_URL, defaultUrl )
        .then( function( serverUrl ) {
            var authUrl = serverUrl + TT.CONFIG.EXTENSION_AUTHORIZE_PATH;
            chrome.tabs.create( { url: authUrl } );
        });
}

function openNewTripPage() {
    var defaultUrl = TT.CONFIG.IS_DEVELOPMENT
        ? TT.CONFIG.DEFAULT_SERVER_URL_DEV
        : TT.CONFIG.DEFAULT_SERVER_URL_PROD;

    TTStorage.get( TT.STORAGE.KEY_SERVER_URL, defaultUrl )
        .then( function( serverUrl ) {
            var createUrl = serverUrl + TT.CONFIG.TRIP_CREATE_PATH;
            chrome.tabs.create( { url: createUrl } );
        });
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
    // Clear trip UI
    var activeTripTitle = document.getElementById( TT.DOM.ID_ACTIVE_TRIP_TITLE );
    if ( activeTripTitle ) {
        activeTripTitle.textContent = '';
    }
    var otherTripsList = document.getElementById( TT.DOM.ID_OTHER_TRIPS_LIST );
    if ( otherTripsList ) {
        otherTripsList.innerHTML = '';
    }
}

function showTripLoading() {
    var loading = document.getElementById( TT.DOM.ID_TRIP_LOADING );
    var activeTrip = document.getElementById( TT.DOM.ID_ACTIVE_TRIP );
    var otherTrips = document.getElementById( TT.DOM.ID_OTHER_TRIPS );
    var empty = document.getElementById( TT.DOM.ID_TRIP_EMPTY );

    if ( loading ) loading.classList.remove( TT.DOM.CLASS_HIDDEN );
    if ( activeTrip ) activeTrip.classList.add( TT.DOM.CLASS_HIDDEN );
    if ( otherTrips ) otherTrips.classList.add( TT.DOM.CLASS_HIDDEN );
    if ( empty ) empty.classList.add( TT.DOM.CLASS_HIDDEN );
}

function showTripContent( hasActiveTrip, hasOtherTrips ) {
    var loading = document.getElementById( TT.DOM.ID_TRIP_LOADING );
    var activeTrip = document.getElementById( TT.DOM.ID_ACTIVE_TRIP );
    var otherTrips = document.getElementById( TT.DOM.ID_OTHER_TRIPS );
    var empty = document.getElementById( TT.DOM.ID_TRIP_EMPTY );

    if ( loading ) loading.classList.add( TT.DOM.CLASS_HIDDEN );
    if ( activeTrip ) {
        if ( hasActiveTrip ) {
            activeTrip.classList.remove( TT.DOM.CLASS_HIDDEN );
        } else {
            activeTrip.classList.add( TT.DOM.CLASS_HIDDEN );
        }
    }
    if ( otherTrips ) {
        if ( hasOtherTrips ) {
            otherTrips.classList.remove( TT.DOM.CLASS_HIDDEN );
        } else {
            otherTrips.classList.add( TT.DOM.CLASS_HIDDEN );
        }
    }
    if ( empty ) empty.classList.add( TT.DOM.CLASS_HIDDEN );
}

function showTripEmpty() {
    var loading = document.getElementById( TT.DOM.ID_TRIP_LOADING );
    var activeTrip = document.getElementById( TT.DOM.ID_ACTIVE_TRIP );
    var otherTrips = document.getElementById( TT.DOM.ID_OTHER_TRIPS );
    var empty = document.getElementById( TT.DOM.ID_TRIP_EMPTY );

    if ( loading ) loading.classList.add( TT.DOM.CLASS_HIDDEN );
    if ( activeTrip ) activeTrip.classList.add( TT.DOM.CLASS_HIDDEN );
    if ( otherTrips ) otherTrips.classList.add( TT.DOM.CLASS_HIDDEN );
    if ( empty ) empty.classList.remove( TT.DOM.CLASS_HIDDEN );
}

function loadTrips() {
    showTripLoading();

    TTMessaging.send( TT.MESSAGE.TYPE_GET_TRIPS, {} )
        .then( function( response ) {
            if ( response && response.success ) {
                renderTrips( response.data.workingSet, response.data.activeTripUuid );
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

function renderTrips( workingSet, activeTripUuid ) {
    if ( !workingSet || workingSet.length === 0 ) {
        showTripEmpty();
        return;
    }

    // Find active trip and other trips
    var activeTrip = null;
    var otherTrips = [];

    workingSet.forEach( function( trip ) {
        if ( trip.uuid === activeTripUuid ) {
            activeTrip = trip;
        } else {
            otherTrips.push( trip );
        }
    });

    // Render active trip display
    var activeTripTitle = document.getElementById( TT.DOM.ID_ACTIVE_TRIP_TITLE );
    if ( activeTripTitle && activeTrip ) {
        activeTripTitle.textContent = activeTrip.title || 'Loading...';
    }

    // Update GMM status for active trip
    if ( activeTrip ) {
        updateGmmStatus( activeTrip );
    }

    // Render other trips as switch buttons
    var otherTripsList = document.getElementById( TT.DOM.ID_OTHER_TRIPS_LIST );
    if ( otherTripsList ) {
        otherTripsList.innerHTML = '';

        otherTrips.forEach( function( trip ) {
            var button = document.createElement( 'button' );
            button.className = TT.DOM.CLASS_SWITCH_TRIP_BTN;
            button.textContent = trip.title || 'Loading...';

            // Click handler - switch trip (will eventually also navigate)
            button.addEventListener( 'click', function() {
                switchToTrip( trip );
            });

            otherTripsList.appendChild( button );
        });
    }

    showTripContent( activeTrip !== null, otherTrips.length > 0 );
}

function switchToTrip( trip ) {
    TTMessaging.send( TT.MESSAGE.TYPE_SET_ACTIVE_TRIP, { trip: trip } )
        .then( function( response ) {
            if ( response && response.success ) {
                addLocalDebugEntry( 'info', 'Switched to trip: ' + trip.title );
                // Re-render to show the switch
                renderTrips( response.data.workingSet, response.data.activeTripUuid );
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

    // Apply dev mode styling to panel header
    var header = panel.querySelector( '.tt-panel-header' );
    if ( header && TT.CONFIG.IS_DEVELOPMENT ) {
        header.classList.add( TT.DOM.CLASS_DEV_MODE );
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

function showTripDetailsPanel() {
    var panel = document.getElementById( TT.DOM.ID_TRIP_DETAILS_PANEL );
    if ( panel ) {
        populateTripDetails();
        panel.classList.remove( TT.DOM.CLASS_HIDDEN );
        requestAnimationFrame( function() {
            panel.classList.add( TT.DOM.CLASS_VISIBLE );
        });
    }

    // Apply dev mode styling to panel header
    var header = panel.querySelector( '.tt-panel-header' );
    if ( header && TT.CONFIG.IS_DEVELOPMENT ) {
        header.classList.add( TT.DOM.CLASS_DEV_MODE );
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

function populateTripDetails() {
    if ( !currentActiveTrip ) return;

    var titleEl = document.getElementById( TT.DOM.ID_TRIP_DETAILS_TITLE );
    var descEl = document.getElementById( TT.DOM.ID_TRIP_DETAILS_DESCRIPTION );
    var uuidEl = document.getElementById( TT.DOM.ID_TRIP_DETAILS_UUID );
    var gmmIdEl = document.getElementById( TT.DOM.ID_TRIP_DETAILS_GMM_ID );
    var gmmRow = document.getElementById( TT.DOM.ID_TRIP_DETAILS_GMM_ROW );
    var actionsEl = document.getElementById( TT.DOM.ID_TRIP_DETAILS_ACTIONS );

    if ( titleEl ) titleEl.textContent = currentActiveTrip.title;
    if ( descEl ) descEl.textContent = currentActiveTrip.description || '';
    if ( uuidEl ) uuidEl.textContent = currentActiveTrip.uuid;

    if ( currentActiveTrip.gmm_map_id ) {
        if ( gmmIdEl ) gmmIdEl.textContent = currentActiveTrip.gmm_map_id;
        if ( gmmRow ) gmmRow.classList.remove( TT.DOM.CLASS_HIDDEN );
        if ( actionsEl ) actionsEl.classList.remove( TT.DOM.CLASS_HIDDEN );
    } else {
        if ( gmmRow ) gmmRow.classList.add( TT.DOM.CLASS_HIDDEN );
        if ( actionsEl ) actionsEl.classList.add( TT.DOM.CLASS_HIDDEN );
    }
}

/**
 * Handle Sync Map button click.
 * Sends sync message to GMM content script if map is open.
 */
function handleSyncLocations() {
    if ( !currentActiveTrip ) {
        addLocalDebugEntry( 'warning', 'Sync: No active trip' );
        return;
    }

    if ( !currentActiveTrip.gmm_map_id ) {
        addLocalDebugEntry( 'warning', 'Sync: Trip has no linked map' );
        return;
    }

    addLocalDebugEntry( 'info', 'Sync Map requested for trip: ' + currentActiveTrip.title );

    TTMessaging.send( TT.MESSAGE.TYPE_GMM_SYNC_LOCATIONS, {
        tripUuid: currentActiveTrip.uuid,
        tripTitle: currentActiveTrip.title,
        mapId: currentActiveTrip.gmm_map_id
    })
    .then( function( response ) {
        if ( response && response.success ) {
            addLocalDebugEntry( 'info', 'Sync dialog opened' );
            window.close();
        } else if ( response && response.data && response.data.code === 'MAP_NOT_OPEN' ) {
            // Map tab not open - prompt user
            // eslint-disable-next-line no-alert
            if ( confirm( 'The map must be open to sync.\n\nOpen the map now?' ) ) {
                openGmmMap( currentActiveTrip.gmm_map_id );
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

function handleUnlinkMap() {
    if ( !currentActiveTrip || !currentActiveTrip.gmm_map_id ) return;

    // eslint-disable-next-line no-alert
    if ( !confirm( 'Unlink the Google My Maps map from this trip?' ) ) {
        return;
    }

    TTMessaging.send( TT.MESSAGE.TYPE_GMM_UNLINK_MAP, {
        tripUuid: currentActiveTrip.uuid
    })
    .then( function( response ) {
        if ( response && response.success ) {
            currentActiveTrip.gmm_map_id = null;
            populateTripDetails();
            updateGmmStatus( currentActiveTrip );
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
    // Use existing setActiveTrip which adds to working set AND sets active
    TTMessaging.send( TT.MESSAGE.TYPE_SET_ACTIVE_TRIP, { trip: trip } )
        .then( function( response ) {
            if ( response && response.success ) {
                addLocalDebugEntry( 'info', 'Selected trip from list: ' + trip.title );
                hideMoreTripsPanel();
                // Refresh main trip display
                renderTrips( response.data.workingSet, response.data.activeTripUuid );
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

// Current active trip for GMM operations
var currentActiveTrip = null;

/**
 * Update GMM status indicator for the active trip.
 * @param {Object} trip - The active trip with optional gmm_map_id.
 */
function updateGmmStatus( trip ) {
    var statusEl = document.getElementById( TT.DOM.ID_GMM_STATUS );
    if ( !statusEl ) {
        return;
    }

    // Store trip for later use
    currentActiveTrip = trip;

    var hasMap = trip && trip.gmm_map_id;

    if ( hasMap ) {
        statusEl.classList.add( TT.DOM.CLASS_GMM_LINKED );
        statusEl.classList.remove( TT.DOM.CLASS_GMM_UNLINKED );
        statusEl.title = 'Map linked - click to open';
    } else {
        statusEl.classList.remove( TT.DOM.CLASS_GMM_LINKED );
        statusEl.classList.add( TT.DOM.CLASS_GMM_UNLINKED );
        statusEl.title = 'No map - click to create';
    }
}

/**
 * Set up event listeners for GMM features.
 */
function setupGmmEventListeners() {
    // Active trip row click - open map or show create dialog
    var activeTripRow = document.getElementById( TT.DOM.ID_ACTIVE_TRIP_ROW );
    if ( activeTripRow ) {
        activeTripRow.addEventListener( 'click', handleActiveTripClick );
    }

    // Create map dialog buttons
    var cancelBtn = document.getElementById( TT.DOM.ID_CREATE_MAP_CANCEL );
    if ( cancelBtn ) {
        cancelBtn.addEventListener( 'click', hideCreateMapDialog );
    }

    var confirmBtn = document.getElementById( TT.DOM.ID_CREATE_MAP_CONFIRM );
    if ( confirmBtn ) {
        confirmBtn.addEventListener( 'click', confirmCreateMap );
    }
}

/**
 * Handle click on active trip row.
 * Opens existing map or shows create map dialog.
 */
function handleActiveTripClick() {
    if ( !currentActiveTrip ) {
        return;
    }

    if ( currentActiveTrip.gmm_map_id ) {
        // Has map - open it
        openGmmMap( currentActiveTrip.gmm_map_id );
    } else {
        // No map - show create dialog
        showCreateMapDialog( currentActiveTrip );
    }
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
 * Show the create map confirmation dialog.
 * @param {Object} trip - The trip to create a map for.
 */
function showCreateMapDialog( trip ) {
    var dialog = document.getElementById( TT.DOM.ID_CREATE_MAP_DIALOG );
    var titleEl = document.getElementById( TT.DOM.ID_CREATE_MAP_TRIP_TITLE );

    if ( titleEl ) {
        titleEl.textContent = trip.title || 'Untitled Trip';
    }

    if ( dialog ) {
        dialog.classList.remove( TT.DOM.CLASS_HIDDEN );
    }
}

/**
 * Hide the create map confirmation dialog.
 */
function hideCreateMapDialog() {
    var dialog = document.getElementById( TT.DOM.ID_CREATE_MAP_DIALOG );
    if ( dialog ) {
        dialog.classList.add( TT.DOM.CLASS_HIDDEN );
    }
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

/**
 * Confirm and start creating a new map.
 */
function confirmCreateMap() {
    if ( !currentActiveTrip ) {
        return;
    }

    hideCreateMapDialog();
    showCreatingMapDialog( 'Creating map in Google My Maps...' );

    TTMessaging.send( TT.MESSAGE.TYPE_GMM_CREATE_MAP, {
        tripUuid: currentActiveTrip.uuid,
        tripTitle: currentActiveTrip.title
    })
    .then( function( response ) {
        hideCreatingMapDialog();

        if ( response && response.success ) {
            addLocalDebugEntry( 'info', 'Created GMM map: ' + response.data.mapId );

            // Update local trip data and UI
            currentActiveTrip.gmm_map_id = response.data.mapId;
            updateGmmStatus( currentActiveTrip );

            // Close popup - user is now on the new map
            window.close();
        } else {
            var errorMsg = response && response.error ? response.error : 'Unknown error';
            addLocalDebugEntry( 'error', 'Create map failed: ' + errorMsg );
            alert( 'Failed to create map: ' + errorMsg );
        }
    })
    .catch( function( error ) {
        hideCreatingMapDialog();
        addLocalDebugEntry( 'error', 'Create map error: ' + error.message );
        alert( 'Failed to create map: ' + error.message );
    });
}
