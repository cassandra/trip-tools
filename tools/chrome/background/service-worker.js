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
importScripts( '../shared/locations.js' );
importScripts( '../shared/sync.js' );
importScripts( '../shared/client-config.js' );

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
        case TT.MESSAGE.TYPE_GET_ALL_TRIPS:
            return handleGetAllTrips();
        case TT.MESSAGE.TYPE_GMM_CREATE_MAP:
            return handleGmmCreateMap( message.data );
        case TT.MESSAGE.TYPE_GMM_OPEN_MAP:
            return handleGmmOpenMap( message.data );
        case TT.MESSAGE.TYPE_GMM_LINK_MAP:
            return handleGmmLinkMap( message.data );
        case TT.MESSAGE.TYPE_GMM_UNLINK_MAP:
            return handleGmmUnlinkMap( message.data );
        case TT.MESSAGE.TYPE_SAVE_LOCATION:
            return handleSaveLocation( message.data );
        case TT.MESSAGE.TYPE_GET_LOCATION:
            return handleGetLocation( message.data );
        case TT.MESSAGE.TYPE_GET_LOCATION_CATEGORIES:
            return handleGetLocationCategories();
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
            // Clear location sync metadata
            return TTLocations.clearAll();
        })
        .then( function() {
            // Clear client config state
            return TTClientConfig.clearAll();
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

/**
 * Handle request to get all trips from server.
 * Returns the full list of trips (not just working set).
 */
function handleGetAllTrips() {
    return TTTrips.fetchTripsFromServer()
        .then( function( trips ) {
            return TTMessaging.createResponse( true, { trips: trips });
        })
        .catch( function( error ) {
            return TTMessaging.createResponse( false, null, error.message );
        });
}

// =============================================================================
// GMM Map Handlers
// =============================================================================

/**
 * Build GMM home page URL.
 * @returns {string}
 */
function buildGmmHomeUrl() {
    return 'https://' + TT.URL.GMM_DOMAIN + TT.URL.GMM_HOME_PATH;
}

/**
 * Build GMM edit page URL for a map.
 * @param {string} mapId - The GMM map ID.
 * @returns {string}
 */
function buildGmmEditUrl( mapId ) {
    return 'https://' + TT.URL.GMM_DOMAIN + TT.URL.GMM_EDIT_PATH + '?' +
           TT.URL.GMM_MAP_ID_PARAM + '=' + encodeURIComponent( mapId );
}

/**
 * Find existing GMM tab matching a URL pattern.
 * @param {string} urlPattern - URL pattern to match.
 * @returns {Promise<chrome.tabs.Tab|null>}
 */
function findGmmTab( urlPattern ) {
    return new Promise( function( resolve ) {
        chrome.tabs.query( { url: urlPattern }, function( tabs ) {
            resolve( tabs && tabs.length > 0 ? tabs[0] : null );
        });
    });
}

/**
 * Wait for tab to complete loading.
 * @param {number} tabId - The tab ID.
 * @param {number} timeoutMs - Maximum wait time.
 * @returns {Promise<void>}
 */
function waitForTabLoad( tabId, timeoutMs ) {
    return new Promise( function( resolve, reject ) {
        var timeoutId = setTimeout( function() {
            chrome.tabs.onUpdated.removeListener( listener );
            reject( new Error( 'Tab load timeout' ) );
        }, timeoutMs );

        function listener( updatedTabId, changeInfo ) {
            if ( updatedTabId === tabId && changeInfo.status === 'complete' ) {
                clearTimeout( timeoutId );
                chrome.tabs.onUpdated.removeListener( listener );
                resolve();
            }
        }

        chrome.tabs.onUpdated.addListener( listener );
    });
}

/**
 * Send message to content script and wait for response.
 * Retries if content script not ready.
 * @param {number} tabId - The tab ID.
 * @param {Object} message - The message to send.
 * @param {number} maxRetries - Maximum retry attempts.
 * @param {number} retryDelayMs - Delay between retries.
 * @returns {Promise<Object>}
 */
function sendMessageToTab( tabId, message, maxRetries, retryDelayMs ) {
    maxRetries = maxRetries || 5;
    retryDelayMs = retryDelayMs || 500;

    function attempt( retriesLeft ) {
        return new Promise( function( resolve, reject ) {
            chrome.tabs.sendMessage( tabId, message, function( response ) {
                if ( chrome.runtime.lastError ) {
                    if ( retriesLeft > 0 ) {
                        setTimeout( function() {
                            attempt( retriesLeft - 1 ).then( resolve ).catch( reject );
                        }, retryDelayMs );
                    } else {
                        reject( new Error( chrome.runtime.lastError.message ) );
                    }
                    return;
                }
                resolve( response );
            });
        });
    }

    return attempt( maxRetries );
}

/**
 * Handle create GMM map request.
 * Orchestrates: navigate to GMM home → click create → wait for edit page →
 * rename map → extract map ID → PATCH trip.
 * @param {Object} data - { tripUuid, tripTitle }
 */
function handleGmmCreateMap( data ) {
    if ( !data || !data.tripUuid || !data.tripTitle ) {
        return Promise.resolve( TTMessaging.createResponse( false, {
            error: 'tripUuid and tripTitle are required'
        }));
    }

    var tripUuid = data.tripUuid;
    var tripTitle = data.tripTitle;
    var tripDescription = '';
    var tabId = null;
    var mapId = null;

    console.log( '[TT Background] Creating GMM map for trip:', tripTitle );

    // Get trip description from working set
    return TTTrips.getWorkingSet()
        .then( function( workingSet ) {
            var trip = workingSet.find( function( t ) {
                return t.uuid === tripUuid;
            });
            if ( trip && trip.description ) {
                tripDescription = trip.description;
            }

            // Step 1: Find or create GMM home tab
            return findGmmTab( 'https://www.google.com/maps/d/*' );
        })
        .then( function( existingTab ) {
            if ( existingTab ) {
                // Use existing tab, navigate to home
                tabId = existingTab.id;
                return chrome.tabs.update( tabId, { url: buildGmmHomeUrl(), active: true } );
            } else {
                // Create new tab
                return chrome.tabs.create( { url: buildGmmHomeUrl(), active: true } )
                    .then( function( tab ) {
                        tabId = tab.id;
                        return tab;
                    });
            }
        })
        .then( function() {
            // Wait for home page to load
            return waitForTabLoad( tabId, 15000 );
        })
        .then( function() {
            // Give content script time to initialize
            return new Promise( function( resolve ) {
                setTimeout( resolve, 1000 );
            });
        })
        .then( function() {
            // Step 2: Tell content script to click create button
            return sendMessageToTab( tabId, {
                type: TT.MESSAGE.TYPE_GMM_CREATE_MAP
            });
        })
        .then( function( response ) {
            if ( !response || !response.success ) {
                throw new Error( response && response.error || 'Failed to click create button' );
            }

            // Step 3: Wait for navigation to edit page
            // The click will cause GMM to redirect to the new map's edit page
            return waitForTabLoad( tabId, 15000 );
        })
        .then( function() {
            // Give edit page time to fully load
            return new Promise( function( resolve ) {
                setTimeout( resolve, 2000 );
            });
        })
        .then( function() {
            // Step 4: Get map info from edit page (extract mid from URL)
            return sendMessageToTab( tabId, {
                type: TT.MESSAGE.TYPE_GMM_GET_MAP_INFO
            });
        })
        .then( function( response ) {
            if ( !response || !response.success || !response.data || !response.data.mapId ) {
                throw new Error( 'Failed to get map ID from new map' );
            }
            mapId = response.data.mapId;
            console.log( '[TT Background] New map created with ID:', mapId );

            // Step 5: Set map title and description
            return sendMessageToTab( tabId, {
                type: TT.MESSAGE.TYPE_GMM_RENAME_MAP,
                data: { title: tripTitle, description: tripDescription }
            });
        })
        .then( function( response ) {
            if ( !response || !response.success ) {
                // Rename failed but map was created - log warning but continue
                console.warn( '[TT Background] Failed to rename map:', response && response.error );
            }

            // Step 6: PATCH trip with gmm_map_id
            return TTApi.updateTrip( tripUuid, { gmm_map_id: mapId } );
        })
        .then( function( updatedTrip ) {
            console.log( '[TT Background] Trip linked to map:', mapId );

            // Update local trip cache
            return TTTrips.updateTripInWorkingSet( tripUuid, { gmm_map_id: mapId } )
                .then( function() {
                    return TTMessaging.createResponse( true, {
                        mapId: mapId,
                        trip: updatedTrip
                    });
                });
        })
        .catch( function( error ) {
            console.error( '[TT Background] GMM create map failed:', error );
            return TTMessaging.createResponse( false, {
                error: error.message
            });
        });
}

/**
 * Handle open GMM map request.
 * Navigates to existing GMM tab or creates new one.
 * @param {Object} data - { mapId }
 */
function handleGmmOpenMap( data ) {
    if ( !data || !data.mapId ) {
        return Promise.resolve( TTMessaging.createResponse( false, {
            error: 'mapId is required'
        }));
    }

    var mapId = data.mapId;
    var editUrl = buildGmmEditUrl( mapId );

    // Look for tab with this specific map open
    return findGmmTab( editUrl + '*' )
        .then( function( existingTab ) {
            if ( existingTab ) {
                // Switch to existing tab
                return chrome.tabs.update( existingTab.id, { active: true } )
                    .then( function() {
                        return chrome.windows.update( existingTab.windowId, { focused: true } );
                    })
                    .then( function() {
                        return TTMessaging.createResponse( true, {
                            tabId: existingTab.id,
                            existing: true
                        });
                    });
            } else {
                // Create new tab
                return chrome.tabs.create( { url: editUrl, active: true } )
                    .then( function( tab ) {
                        return TTMessaging.createResponse( true, {
                            tabId: tab.id,
                            existing: false
                        });
                    });
            }
        })
        .catch( function( error ) {
            return TTMessaging.createResponse( false, {
                error: error.message
            });
        });
}

/**
 * Handle link GMM map request.
 * PATCHes trip with gmm_map_id.
 * @param {Object} data - { tripUuid, mapId }
 */
function handleGmmLinkMap( data ) {
    if ( !data || !data.tripUuid || !data.mapId ) {
        return Promise.resolve( TTMessaging.createResponse( false, {
            error: 'tripUuid and mapId are required'
        }));
    }

    var tripUuid = data.tripUuid;
    var mapId = data.mapId;

    return TTApi.updateTrip( tripUuid, { gmm_map_id: mapId } )
        .then( function( updatedTrip ) {
            // Update local trip cache
            return TTTrips.updateTripInWorkingSet( tripUuid, { gmm_map_id: mapId } )
                .then( function() {
                    return TTMessaging.createResponse( true, {
                        trip: updatedTrip
                    });
                });
        })
        .catch( function( error ) {
            return TTMessaging.createResponse( false, {
                error: error.message
            });
        });
}

/**
 * Handle unlink GMM map request.
 * Clears gmm_map_id from trip via PATCH.
 * @param {Object} data - { tripUuid }
 */
function handleGmmUnlinkMap( data ) {
    if ( !data || !data.tripUuid ) {
        return Promise.resolve( TTMessaging.createResponse( false, {
            error: 'tripUuid is required'
        }));
    }

    var tripUuid = data.tripUuid;

    return TTApi.updateTrip( tripUuid, { gmm_map_id: null } )
        .then( function() {
            // Update local trip cache
            return TTTrips.updateTripInWorkingSet( tripUuid, { gmm_map_id: null } );
        })
        .then( function() {
            console.log( '[TT Background] Unlinked map from trip:', tripUuid );
            return TTMessaging.createResponse( true );
        })
        .catch( function( error ) {
            return TTMessaging.createResponse( false, {
                error: error.message
            });
        });
}

// =============================================================================
// Location Handlers
// =============================================================================

/**
 * Handle save location request from GMM content script.
 * Creates location on server and updates local sync metadata.
 * @param {Object} data - { gmm_id, title, latitude, longitude, category_slug, subcategory_slug }
 */
function handleSaveLocation( data ) {
    if ( !data || !data.gmm_id || !data.title ) {
        return Promise.resolve( TTMessaging.createResponse( false, {
            error: 'gmm_id and title are required'
        }));
    }

    var tripUuid;

    return TTStorage.get( TT.STORAGE.KEY_ACTIVE_TRIP_UUID, null )
        .then( function( activeTripUuid ) {
            if ( !activeTripUuid ) {
                throw new Error( 'No active trip selected' );
            }
            tripUuid = activeTripUuid;

            var locationData = {
                trip_uuid: tripUuid,
                gmm_id: data.gmm_id,
                title: data.title,
                subcategory_slug: data.subcategory_slug || null
            };

            // Include coordinates if available
            if ( data.latitude !== undefined && data.longitude !== undefined ) {
                locationData.latitude = data.latitude;
                locationData.longitude = data.longitude;
            }

            return TTApi.createLocation( locationData );
        })
        .then( function( location ) {
            console.log( '[TT Background] Location saved:', location.uuid );

            // Update local sync metadata
            return TTLocations.updateMetadataFromLocation( tripUuid, location )
                .then( function() {
                    return TTMessaging.createResponse( true, location );
                });
        })
        .catch( function( error ) {
            console.error( '[TT Background] Save location failed:', error );
            return TTMessaging.createResponse( false, {
                error: error.message || 'Failed to save location'
            });
        });
}

/**
 * Handle get location request from content script.
 * Looks up UUID by gmm_id, then fetches location from server.
 * @param {Object} data - { gmm_id }
 * @returns {Promise<Object>} Response with location data or notFound flag.
 */
function handleGetLocation( data ) {
    if ( !data || !data.gmm_id ) {
        return Promise.resolve( TTMessaging.createResponse( false, {
            error: 'gmm_id is required'
        }));
    }

    return TTStorage.get( TT.STORAGE.KEY_ACTIVE_TRIP_UUID, null )
        .then( function( tripUuid ) {
            if ( !tripUuid ) {
                return TTMessaging.createResponse( false, {
                    error: 'No active trip selected',
                    notFound: true
                });
            }

            return TTLocations.getUuidByGmmId( tripUuid, data.gmm_id )
                .then( function( locationUuid ) {
                    if ( !locationUuid ) {
                        return TTMessaging.createResponse( false, {
                            notFound: true
                        });
                    }

                    return TTApi.getLocation( locationUuid )
                        .then( function( location ) {
                            return TTMessaging.createResponse( true, location );
                        });
                });
        })
        .catch( function( error ) {
            console.error( '[TT Background] Get location failed:', error );
            return TTMessaging.createResponse( false, {
                error: error.message || 'Failed to get location'
            });
        });
}

/**
 * Handle get location categories request from content script.
 * Refreshes config if stale/missing, then returns categories.
 * @returns {Promise<Object>} Response with categories array.
 */
function handleGetLocationCategories() {
    return TTClientConfig.refreshIfStale()
        .then( function( config ) {
            var categories = ( config && config.location_categories ) || [];
            return TTMessaging.createResponse( true, categories );
        })
        .catch( function( error ) {
            console.error( '[TT Background] Get categories failed:', error );
            return TTMessaging.createResponse( false, {
                error: error.message || 'Failed to get categories'
            });
        });
}
