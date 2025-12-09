/*
 * Trip Tools Chrome Extension - Background Service Worker
 * Handles extension lifecycle and message routing.
 */

importScripts( '../shared/constants.js' );
importScripts( '../shared/storage.js' );
importScripts( '../shared/messaging.js' );
importScripts( '../shared/auth.js' );
importScripts( '../shared/api.js' );
importScripts( '../shared/trips.js' );
importScripts( '../shared/sync.js' );

var extensionStartTime = Date.now();
var lastAuthValidation = 0;
var connectionStartTime = null;  // Time of last successful server contact (null = never or disrupted)

chrome.runtime.onInstalled.addListener( function( details ) {
    console.log( '[TT Background] Extension installed:', details.reason );
    initializeExtensionState();
});

function initializeExtensionState() {
    var initialState = {
        installedAt: Date.now(),
        version: TT.CONFIG.EXTENSION_VERSION
    };
    TTStorage.set( TT.STORAGE.KEY_EXTENSION_STATE, initialState );
    TTStorage.set( TT.STORAGE.KEY_DEBUG_LOG, [] );
    TTStorage.set( TT.STORAGE.KEY_SELECT_DECORATE_ENABLED, true );
    TTStorage.set( TT.STORAGE.KEY_MAP_INFO_LIST, [] );
    TTStorage.set( TT.STORAGE.KEY_DEBUG_MODE, false );
}

TTMessaging.listen( function( message, sender ) {
    logMessage( 'Received', message.type, message.data );

    switch ( message.type ) {
        case TT.MESSAGE.TYPE_PING:
            return handlePing();
        case TT.MESSAGE.TYPE_GET_STATE:
            return handleGetState();
        case TT.MESSAGE.TYPE_LOG:
            return handleLog( message.data );
        case TT.MESSAGE.TYPE_TOKEN_RECEIVED:
            return handleTokenReceived( message.data );
        case TT.MESSAGE.TYPE_AUTH_STATUS_REQUEST:
            return handleAuthStatusRequest( sender );
        case TT.MESSAGE.TYPE_DISCONNECT:
            return handleDisconnect();
        case TT.MESSAGE.TYPE_GET_TRIPS:
            return handleGetTrips();
        case TT.MESSAGE.TYPE_SET_ACTIVE_TRIP:
            return handleSetActiveTrip( message.data );
        default:
            return TTMessaging.createResponse( false, {
                error: 'Unknown message type: ' + message.type
            });
    }
});

function handlePing() {
    var connectionUptimeMs = connectionStartTime ? Date.now() - connectionStartTime : 0;
    return TTMessaging.createResponse( true, {
        type: TT.MESSAGE.TYPE_PONG,
        uptime: connectionUptimeMs,
        version: TT.CONFIG.EXTENSION_VERSION
    });
}

function handleGetState() {
    var defaults = {};
    defaults[TT.STORAGE.KEY_EXTENSION_STATE] = {};
    defaults[TT.STORAGE.KEY_MAP_INFO_LIST] = [];
    defaults[TT.STORAGE.KEY_SELECT_DECORATE_ENABLED] = true;
    defaults[TT.STORAGE.KEY_DEBUG_MODE] = false;

    return TTStorage.getMultiple( defaults )
        .then( function( state ) {
            return TTMessaging.createResponse( true, state );
        });
}

function handleLog( data ) {
    var level = data.level || 'info';
    var message = data.message || '';
    return addDebugLogEntry( level, message );
}

function addDebugLogEntry( level, message ) {
    return TTStorage.get( TT.STORAGE.KEY_DEBUG_LOG, [] )
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
            return TTMessaging.createResponse( true, {} );
        });
}

function logMessage( direction, type, data ) {
    console.log( '[TT Background] ' + direction + ': ' + type, data );
}

/**
 * Handle token received from content script or options page.
 * Validates token, stores it, and updates auth state.
 */
function handleTokenReceived( data ) {
    var token = data.token;

    // Validate token format (security: never log the token value)
    if ( !TTAuth.isValidTokenFormat( token ) ) {
        return Promise.resolve( TTMessaging.createResponse( false, {
            error: TT.STRINGS.AUTH_ERROR_INVALID_FORMAT
        }));
    }

    // Create abort controller for timeout
    var controller = new AbortController();
    var timeoutId = setTimeout( function() {
        controller.abort();
    }, TT.CONFIG.AUTH_VALIDATION_TIMEOUT_MS );

    // Store token first
    return TTAuth.setApiToken( token )
        .then( function() {
            // Validate token by calling /api/v1/me/ with timeout
            return TTApi.validateTokenWithSignal( token, controller.signal );
        })
        .then( function( userInfo ) {
            clearTimeout( timeoutId );
            return userInfo;
        })
        .then( function( userInfo ) {
            // Token is valid - store user email and update state
            connectionStartTime = Date.now();
            lastAuthValidation = 0;  // Reset debounce on auth state change
            return TTAuth.setUserEmail( userInfo.email )
                .then( function() {
                    return TTAuth.setAuthState( TT.AUTH.STATE_AUTHORIZED );
                })
                .then( function() {
                    // Log success (without revealing token)
                    return addDebugLogEntry( 'info', 'Authorization successful: ' + userInfo.email );
                })
                .then( function() {
                    broadcastAuthStateChange( true, userInfo.email );
                    return TTMessaging.createResponse( true, {
                        authorized: true,
                        email: userInfo.email
                    });
                });
        })
        .catch( function( error ) {
            clearTimeout( timeoutId );
            // Token validation failed - clear it
            connectionStartTime = null;
            lastAuthValidation = 0;  // Reset debounce on auth state change
            return TTAuth.clearApiToken()
                .then( function() {
                    return TTAuth.setAuthState( TT.AUTH.STATE_NOT_AUTHORIZED );
                })
                .then( function() {
                    return addDebugLogEntry( 'error', 'Authorization failed: ' + error.message );
                })
                .then( function() {
                    return TTMessaging.createResponse( false, {
                        error: error.message
                    });
                });
        });
}

/**
 * Handle auth status request.
 * Validates token with server with differentiated debouncing:
 * - Options page: Always validates fresh (no debounce)
 * - Popup: Uses 1-minute debounce
 *
 * @param {Object} sender - Chrome message sender with url property
 */
function handleAuthStatusRequest( sender ) {
    // Determine debounce based on sender
    // Options page always validates fresh, popup uses 1-minute debounce
    var isOptionsPage = sender && sender.url && sender.url.includes( '/options/' );
    var debounceMs = isOptionsPage ? 0 : TT.CONFIG.AUTH_VALIDATION_DEBOUNCE_POPUP_MS;

    return TTAuth.getAuthState()
        .then( function( state ) {
            if ( state !== TT.AUTH.STATE_AUTHORIZED ) {
                return TTMessaging.createResponse( true, {
                    authorized: false,
                    serverStatus: null
                });
            }

            // Check debounce - return cached state if recent validation
            // But still verify we're actually authorized (state could have changed)
            var now = Date.now();
            if ( debounceMs > 0 && ( now - lastAuthValidation < debounceMs ) ) {
                return TTAuth.getAuthState()
                    .then( function( currentState ) {
                        if ( currentState !== TT.AUTH.STATE_AUTHORIZED ) {
                            // State changed (e.g., 401 cleared auth) - don't use cached result
                            return TTMessaging.createResponse( true, {
                                authorized: false,
                                serverStatus: null
                            });
                        }
                        return TTAuth.getUserEmail()
                            .then( function( email ) {
                                return TTMessaging.createResponse( true, {
                                    authorized: true,
                                    email: email,
                                    serverStatus: TT.AUTH.STATUS_ONLINE,
                                    cached: true
                                });
                            });
                    });
            }

            lastAuthValidation = now;

            // Validate with server
            return validateAuthWithServer();
        });
}

/**
 * Validate token with server, handling various error states.
 * Uses the extension status endpoint which also processes sync data.
 */
function validateAuthWithServer() {
    return TTAuth.getApiToken()
        .then( function( token ) {
            if ( !token ) {
                return TTMessaging.createResponse( true, {
                    authorized: false,
                    serverStatus: null
                });
            }

            // Create abort controller for timeout
            var controller = new AbortController();
            var timeoutId = setTimeout( function() {
                controller.abort();
            }, TT.CONFIG.AUTH_VALIDATION_TIMEOUT_MS );

            // Use extension status endpoint - processes sync envelope automatically
            return TTApi.getExtensionStatus( token, controller.signal )
                .then( function( data ) {
                    clearTimeout( timeoutId );
                    // Start uptime counter if not already running
                    if ( !connectionStartTime ) {
                        connectionStartTime = Date.now();
                    }
                    // Sync envelope already processed by TTApi.getExtensionStatus()
                    return TTMessaging.createResponse( true, {
                        authorized: true,
                        email: data.email,
                        serverStatus: TT.AUTH.STATUS_ONLINE
                    });
                })
                .catch( function( error ) {
                    clearTimeout( timeoutId );
                    return handleValidationError( error );
                });
        });
}

/**
 * Handle validation errors with distinct states.
 * Any error resets the uptime counter since connection is disrupted.
 */
function handleValidationError( error ) {
    // Any error disrupts the connection - reset uptime
    connectionStartTime = null;

    // 401 - Token revoked
    if ( error.status === 401 ) {
        lastAuthValidation = 0;  // Reset debounce on auth state change
        return TTAuth.disconnect()
            .then( function() {
                return addDebugLogEntry( 'info', 'Token revoked by server' );
            })
            .then( function() {
                broadcastAuthStateChange( false, null );
                return TTMessaging.createResponse( true, {
                    authorized: false,
                    serverStatus: null
                });
            });
    }

    // Determine error type
    var serverStatus;
    if ( error.name === 'AbortError' ) {
        serverStatus = TT.AUTH.STATUS_TIMEOUT;
    } else if ( error.status === 429 ) {
        serverStatus = TT.AUTH.STATUS_RATE_LIMITED;
    } else if ( error.status >= 500 ) {
        serverStatus = TT.AUTH.STATUS_SERVER_ERROR;
    } else {
        serverStatus = TT.AUTH.STATUS_OFFLINE;
    }

    // Keep cached auth, return with error status
    return TTAuth.getUserEmail()
        .then( function( email ) {
            return addDebugLogEntry( 'warn', 'Server validation failed: ' + serverStatus )
                .then( function() {
                    return TTMessaging.createResponse( true, {
                        authorized: true,
                        email: email,
                        serverStatus: serverStatus
                    });
                });
        });
}

/**
 * Handle disconnect request.
 * Deletes token on server, then clears local auth state.
 * Requires network connectivity - fails if offline.
 */
function handleDisconnect() {
    var storedToken;

    return TTAuth.getApiToken()
        .then( function( token ) {
            storedToken = token;
            if ( !token ) {
                // No token stored, just clear local state
                return Promise.resolve();
            }

            var lookupKey = TTAuth.getLookupKey( token );
            if ( !lookupKey ) {
                // Invalid token format, just clear local state
                return Promise.resolve();
            }

            // Delete token on server
            return TTApi.deleteToken( lookupKey );
        })
        .then( function() {
            // Clear local auth state
            connectionStartTime = null;
            lastAuthValidation = 0;  // Reset debounce on auth state change
            return TTAuth.disconnect();
        })
        .then( function() {
            // Clear trip state
            return TTTrips.clearAll();
        })
        .then( function() {
            // Clear sync state
            return TTSync.clearState();
        })
        .then( function() {
            return addDebugLogEntry( 'info', 'Disconnected from Trip Tools' );
        })
        .then( function() {
            broadcastAuthStateChange( false, null );
            return TTMessaging.createResponse( true, {} );
        })
        .catch( function( error ) {
            return addDebugLogEntry( 'error', 'Disconnect failed: ' + error.message )
                .then( function() {
                    return TTMessaging.createResponse( false, {
                        error: error.message
                    });
                });
        });
}

/**
 * Broadcast auth state change to all extension views (popup, options).
 */
function broadcastAuthStateChange( authorized, email ) {
    var message = {
        type: TT.MESSAGE.TYPE_AUTH_STATE_CHANGED,
        data: {
            authorized: authorized,
            email: email
        }
    };

    // Send to all extension pages (popup, options, etc.)
    chrome.runtime.sendMessage( message ).catch( function() {
        // Ignore errors - no listeners may be active
    });
}

// =============================================================================
// Trip Handlers
// =============================================================================

/**
 * Handle request to get trips.
 * Refreshes any stale trips, then returns the working set.
 * Sync happens during auth validation; this handles the deferred fetching.
 */
function handleGetTrips() {
    var workingSet;
    var activeTripUuid;

    // First refresh any stale trips (fetches details from server)
    return TTTrips.refreshStaleTrips()
        .then( function() {
            return TTTrips.getWorkingSet();
        })
        .then( function( trips ) {
            workingSet = trips;
            return TTTrips.getActiveTripUuid();
        })
        .then( function( uuid ) {
            activeTripUuid = uuid;
            return TTMessaging.createResponse( true, {
                workingSet: workingSet,
                activeTripUuid: activeTripUuid
            });
        })
        .catch( function( error ) {
            return TTMessaging.createResponse( false, {
                error: error.message
            });
        });
}

/**
 * Handle request to set active trip.
 * Adds trip to working set and sets as active.
 * @param {Object} data - Object with trip property.
 */
function handleSetActiveTrip( data ) {
    var trip = data.trip;

    if ( !trip || !trip.uuid ) {
        return Promise.resolve( TTMessaging.createResponse( false, {
            error: 'Trip with uuid required'
        }));
    }

    return TTTrips.setActiveTrip( trip )
        .then( function() {
            return TTTrips.getWorkingSet();
        })
        .then( function( workingSet ) {
            return TTMessaging.createResponse( true, {
                workingSet: workingSet,
                activeTripUuid: trip.uuid
            });
        })
        .catch( function( error ) {
            return TTMessaging.createResponse( false, {
                error: error.message
            });
        });
}
