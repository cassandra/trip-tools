/*
 * Trip Tools Chrome Extension - GMM Location Sync
 * Handles location synchronization between GMM and Trip Tools server.
 */

( function() {
    'use strict';

    var TT_SYNC_DIALOG_CLASS = 'tt-sync-dialog';

    // Distance threshold for coordinate validation (meters)
    var COORDINATE_DISTANCE_THRESHOLD_M = 1000;

    // Cancellation state for sync execute phase
    var _executeStopRequested = false;

    // Warning types for post-sync review
    var WARNING_TYPE = {
        NO_CATEGORY: 'no_category',
        UNKNOWN_CATEGORY: 'unknown_category',
        MULTIPLE_RESULTS: 'multiple_results',
        COORDINATE_MISMATCH: 'coordinate_mismatch',
        LAYER_LIMIT: 'layer_limit'
    };

    // Error types for sync failures
    var ERROR_TYPE = {
        NO_RESULTS: 'no_results',
        NO_DIALOG: 'no_dialog',
        TOO_MANY_RESULTS: 'too_many_results'
    };

    // Human-readable warning messages
    var WARNING_MESSAGES = {};
    WARNING_MESSAGES[WARNING_TYPE.NO_CATEGORY] = "Added to 'Other' layer - move to correct layer";
    WARNING_MESSAGES[WARNING_TYPE.UNKNOWN_CATEGORY] = "Unknown category - added to 'Other' layer";
    WARNING_MESSAGES[WARNING_TYPE.MULTIPLE_RESULTS] = "Multiple matches found - verify location is correct";
    WARNING_MESSAGES[WARNING_TYPE.COORDINATE_MISMATCH] = "Location may not match - verify location is correct";
    WARNING_MESSAGES[WARNING_TYPE.LAYER_LIMIT] = "Could not create 'Other' layer - added to first layer";

    // Human-readable error messages
    var ERROR_MESSAGES = {};
    ERROR_MESSAGES[ERROR_TYPE.NO_RESULTS] = "No search results found";
    ERROR_MESSAGES[ERROR_TYPE.NO_DIALOG] = "Multiple matches found, none selected";
    ERROR_MESSAGES[ERROR_TYPE.TOO_MANY_RESULTS] = "Too many matches - search manually";

    /**
     * Calculate distance between two points using Haversine formula.
     * @param {number} lat1 - Latitude of first point.
     * @param {number} lon1 - Longitude of first point.
     * @param {number} lat2 - Latitude of second point.
     * @param {number} lon2 - Longitude of second point.
     * @returns {number} Distance in meters.
     */
    function calculateDistanceMeters( lat1, lon1, lat2, lon2 ) {
        var R = 6371000; // Earth's radius in meters
        var dLat = ( lat2 - lat1 ) * Math.PI / 180;
        var dLon = ( lon2 - lon1 ) * Math.PI / 180;
        var a = Math.sin( dLat / 2 ) * Math.sin( dLat / 2 ) +
                Math.cos( lat1 * Math.PI / 180 ) * Math.cos( lat2 * Math.PI / 180 ) *
                Math.sin( dLon / 2 ) * Math.sin( dLon / 2 );
        var c = 2 * Math.atan2( Math.sqrt( a ), Math.sqrt( 1 - a ) );
        return R * c;
    }

    /**
     * Initialize sync functionality.
     * Sets up message listener for sync requests.
     */
    function initSync() {
        console.log( '[TT GMM Sync] Initializing sync module' );
        chrome.runtime.onMessage.addListener( handleSyncMessage );
    }

    /**
     * Handle incoming sync messages from background/popup.
     * @param {Object} message - The message object.
     * @param {Object} sender - Message sender info.
     * @param {Function} sendResponse - Response callback.
     * @returns {boolean} True to indicate async response.
     */
    function handleSyncMessage( message, sender, sendResponse ) {
        if ( message.type === TT.MESSAGE.TYPE_GMM_SYNC_LOCATIONS ) {
            console.log( '[TT GMM Sync] Received sync request:', message.data );
            performSync( message.data )
                .then( function( result ) {
                    sendResponse( { success: true, data: result } );
                })
                .catch( function( error ) {
                    sendResponse( { success: false, error: error.message } );
                });
            return true; // Async response
        }
        return false;
    }

    // Track if a sync is currently in progress to prevent duplicate requests
    var _syncInProgress = false;

    /**
     * Perform the sync operation: fetch data, compare, show dialog, execute.
     * @param {Object} data - Sync request data (tripUuid, tripTitle, mapId).
     * @returns {Promise<Object>} Result of sync operation.
     */
    function performSync( data ) {
        // Guard against duplicate sync requests (e.g., from service worker retries after page reload)
        if ( _syncInProgress ) {
            console.log( '[TT GMM Sync] Sync already in progress, ignoring duplicate request' );
            return Promise.resolve( { cancelled: true, reason: 'sync_in_progress' } );
        }

        _syncInProgress = true;
        console.log( '[TT Sync Compare] Fetching locations...' );

        return Promise.all( [
            fetchServerLocations( data.tripUuid ),
            getGmmLocations()
        ])
        .then( function( results ) {
            var serverLocations = results[0];
            var gmmLocations = results[1];

            console.log( '[TT Sync Compare] Server locations:', serverLocations.length );
            console.log( '[TT Sync Compare] GMM locations:', gmmLocations.length );

            var diff = compareLocations( serverLocations, gmmLocations );

            console.log( '[TT Sync Compare] Diff results:', {
                serverOnly: diff.serverOnly.length,
                gmmOnly: diff.gmmOnly.length,
                inBoth: diff.inBoth.length
            });

            return showSyncCompareDialog( data, diff );
        })
        .then( function( dialogResult ) {
            if ( dialogResult.cancelled ) {
                console.log( '[TT GMM Sync] Sync cancelled by user' );
                return { cancelled: true };
            }

            console.log( '[TT Sync Execute] Starting with decisions:', dialogResult.decisions );
            return executeSyncDecisions( data.tripUuid, dialogResult.decisions );
        })
        .then( function( results ) {
            if ( results.cancelled ) {
                return results;
            }

            // Show execute results dialog
            return showSyncExecuteResultsDialog( results );
        })
        .finally( function() {
            _syncInProgress = false;
        });
    }

    /**
     * Check if sync execute was stopped and throw if so.
     * @private
     */
    function checkExecuteStopped() {
        if ( _executeStopRequested ) {
            throw new Error( 'Sync execute stopped by user' );
        }
    }

    /**
     * Execute sync decisions from the dialog.
     * @param {string} tripUuid - Trip UUID.
     * @param {Object} decisions - Map of itemId to { action, source, location/server/gmm }.
     * @returns {Promise<Object>} Sync results with three-tier structure.
     */
    function executeSyncDecisions( tripUuid, decisions ) {
        var gmmToServerKeep = [];
        var gmmToDiscard = [];
        var serverToGmmKeep = [];
        var serverToDiscard = [];
        var matchesToLink = [];      // { server, gmm } - title matches to link
        var matchesToSeparate = [];  // { server, gmm } - title matches NOT to link

        // Categorize decisions
        Object.keys( decisions ).forEach( function( itemId ) {
            var decision = decisions[itemId];
            if ( decision.source === 'gmm' && decision.action === 'keep' ) {
                gmmToServerKeep.push( decision.location );
            } else if ( decision.source === 'gmm' && decision.action === 'discard' ) {
                gmmToDiscard.push( decision.location );
            } else if ( decision.source === 'server' && decision.action === 'keep' ) {
                serverToGmmKeep.push( decision.location );
            } else if ( decision.source === 'server' && decision.action === 'discard' ) {
                serverToDiscard.push( decision.location );
            } else if ( decision.source === 'match' && decision.action === 'link' ) {
                matchesToLink.push( { server: decision.server, gmm: decision.gmm } );
            } else if ( decision.source === 'match' && decision.action === 'dont_link' ) {
                matchesToSeparate.push( { server: decision.server, gmm: decision.gmm } );
            }
        });

        // For "don't link" matches, add both locations to their respective queues
        matchesToSeparate.forEach( function( match ) {
            serverToGmmKeep.push( match.server );
            gmmToServerKeep.push( match.gmm );
        });

        console.log( '[TT Sync Execute] GMM->Server (keep):', gmmToServerKeep.length );
        console.log( '[TT Sync Execute] GMM (discard):', gmmToDiscard.length );
        console.log( '[TT Sync Execute] Server->GMM (keep):', serverToGmmKeep.length );
        console.log( '[TT Sync Execute] Server (discard):', serverToDiscard.length );
        console.log( '[TT Sync Execute] Title matches to link:', matchesToLink.length );

        // Three-tier results structure
        var results = {
            // Successes: linked with no warnings
            addedToServer: [],      // { gmm, server } - GMM -> Server
            addedToGmm: [],         // { server, gmm } - Server -> GMM (no warnings)
            linkedByTitle: [],      // { server, gmm } - linked via title match (no GMM manipulation)
            deletedFromServer: [],  // Server locations discarded
            deletedFromGmm: [],     // GMM locations discarded

            // Warnings: linked but need review
            warnings: [],           // { server, gmm, warnings: [] } - Server -> GMM with warnings

            // Failures: could not link
            failures: [],           // { server, error, resultCount? }

            // Unexpected errors (catch-all)
            errors: [],             // { location, error }

            // Cancellation flag
            stopped: false
        };

        // Reset cancellation state and enter sync mode
        _executeStopRequested = false;
        TTSyncExecuteMode.enter({
            onStop: function() {
                console.log( '[TT Sync Execute] Stop requested' );
                _executeStopRequested = true;
            }
        });

        // Execute syncs sequentially (need to click each location)
        var syncPromise = Promise.resolve();

        // Title matches to link: just update gmm_id on server (no GMM manipulation)
        matchesToLink.forEach( function( match ) {
            syncPromise = syncPromise.then( function() {
                checkExecuteStopped();
                console.log( '[TT Sync Execute] Linking by title:', match.server.title );
                return updateServerLocationGmmId( match.server.uuid, match.gmm.fl_id )
                    .then( function() {
                        results.linkedByTitle.push( { server: match.server, gmm: match.gmm } );
                    })
                    .catch( function( error ) {
                        console.error( '[TT Sync Execute] Error linking by title:', match.server.title, error );
                        results.errors.push( { location: match.server, error: error.message } );
                    });
            });
        });

        // GMM -> Server (keep): add to server
        gmmToServerKeep.forEach( function( gmmLoc ) {
            syncPromise = syncPromise.then( function() {
                checkExecuteStopped();
                return syncGmmLocationToServer( tripUuid, gmmLoc )
                    .then( function( serverLoc ) {
                        results.addedToServer.push( { gmm: gmmLoc, server: serverLoc } );
                    })
                    .catch( function( error ) {
                        console.error( '[TT GMM Sync] Error syncing to server:', gmmLoc.title, error );
                        results.errors.push( { location: gmmLoc, error: error.message } );
                    });
            });
        });

        // GMM (discard): delete from GMM
        gmmToDiscard.forEach( function( gmmLoc ) {
            syncPromise = syncPromise.then( function() {
                checkExecuteStopped();
                return deleteGmmLocation( gmmLoc.fl_id )
                    .then( function() {
                        results.deletedFromGmm.push( gmmLoc );
                    })
                    .catch( function( error ) {
                        console.error( '[TT GMM Sync] Error deleting from GMM:', gmmLoc.title, error );
                        results.errors.push( { location: gmmLoc, error: error.message } );
                    });
            });
        });

        // Server -> GMM (keep): add to GMM
        serverToGmmKeep.forEach( function( serverLoc ) {
            syncPromise = syncPromise.then( function() {
                checkExecuteStopped();
                return syncServerLocationToGmm( serverLoc )
                    .then( function( syncResult ) {
                        if ( syncResult.success ) {
                            if ( syncResult.warnings && syncResult.warnings.length > 0 ) {
                                // Success with warnings - goes to warnings tier
                                results.warnings.push({
                                    server: serverLoc,
                                    gmm: syncResult.gmm,
                                    warnings: syncResult.warnings
                                });
                            } else {
                                // Clean success - goes to success tier
                                results.addedToGmm.push({
                                    server: serverLoc,
                                    gmm: syncResult.gmm
                                });
                            }
                        } else {
                            // Failure - goes to failures tier
                            results.failures.push({
                                server: serverLoc,
                                error: syncResult.error,
                                resultCount: syncResult.resultCount
                            });
                        }
                    })
                    .catch( function( error ) {
                        console.error( '[TT GMM Sync] Error syncing to GMM:', serverLoc.title, error );
                        results.errors.push( { location: serverLoc, error: error.message } );
                    });
            });
        });

        // Server (discard): delete from server
        serverToDiscard.forEach( function( serverLoc ) {
            syncPromise = syncPromise.then( function() {
                checkExecuteStopped();
                return deleteServerLocation( serverLoc.uuid )
                    .then( function() {
                        results.deletedFromServer.push( serverLoc );
                    })
                    .catch( function( error ) {
                        console.error( '[TT GMM Sync] Error deleting from server:', serverLoc.title, error );
                        results.errors.push( { location: serverLoc, error: error.message } );
                    });
            });
        });

        return syncPromise
            .then( function() {
                console.log( '[TT Sync Execute] Complete:', results );
                return results;
            })
            .catch( function( error ) {
                if ( error.message === 'Sync execute stopped by user' ) {
                    console.log( '[TT Sync Execute] Stopped by user' );
                    results.stopped = true;
                    return results;
                }
                throw error;
            })
            .finally( function() {
                // Always exit sync mode when done
                TTSyncExecuteMode.exit();
            });
    }

    /**
     * Delete a location from GMM.
     * @param {string} gmmId - GMM location ID (fl_id).
     * @returns {Promise<void>}
     */
    function deleteGmmLocation( gmmId ) {
        console.log( '[TT GMM Sync] Deleting GMM location:', gmmId );
        return TTGmmAdapter.deleteLocationById( gmmId )
            .then( function() {
                return TTGmmAdapter.closeInfoWindow();
            });
    }

    /**
     * Sync a server location to GMM.
     * Searches for the location by title and adds it to the map.
     *
     * Three-tier results:
     * - Success: Location added and linked (may have no warnings)
     * - Warning: Location added and linked, but needs user review
     * - Failure: Location could not be added
     *
     * @param {Object} serverLoc - Server location object.
     * @returns {Promise<Object>} Result:
     *   - Success: { success: true, gmm, warnings: [] }
     *   - Failure: { success: false, error: ERROR_TYPE, resultCount? }
     */
    function syncServerLocationToGmm( serverLoc ) {
        console.log( '[TT GMM Sync] Syncing server location to GMM:', serverLoc.title );

        var styleOptions;
        var accumulatedWarnings = [];

        // Get styling info from category (may add warnings for Other layer fallback)
        return getStyleOptionsForLocation( serverLoc )
            .then( function( options ) {
                styleOptions = options;

                // Collect any warnings from style options (no category, unknown category)
                if ( options.warnings && options.warnings.length > 0 ) {
                    accumulatedWarnings = accumulatedWarnings.concat( options.warnings );
                }

                console.log( '[TT GMM Sync] Style options:', styleOptions );

                // Add custom title to rename GMM location to server title
                styleOptions.customTitle = serverLoc.title;

                // Search and add to GMM
                return TTGmmAdapter.searchAndAddLocation( serverLoc.title, styleOptions );
            })
            .then( function( result ) {
                console.log( '[TT GMM Sync] Search result:', result );

                // Check for error results from searchAndAddLocation
                if ( result.error ) {
                    if ( result.error === 'no_results' ) {
                        console.log( '[TT GMM Sync] No results for:', serverLoc.title );
                        return { success: false, error: ERROR_TYPE.NO_RESULTS };
                    }
                    if ( result.error === 'no_dialog' ) {
                        console.log( '[TT GMM Sync] No dialog opened for:', serverLoc.title,
                            '- result count:', result.resultCount );
                        return {
                            success: false,
                            error: ERROR_TYPE.NO_DIALOG,
                            resultCount: result.resultCount
                        };
                    }
                    // Handle too many results error
                    if ( result.error === ERROR_TYPE.TOO_MANY_RESULTS ) {
                        console.log( '[TT GMM Sync] Too many results for:', serverLoc.title,
                            '- result count:', result.resultCount );
                        return {
                            success: false,
                            error: result.error,
                            resultCount: result.resultCount
                        };
                    }
                }

                // Check if we got a valid GMM result
                if ( !result || !result.gmmId ) {
                    console.log( '[TT GMM Sync] Unexpected: no gmmId for:', serverLoc.title );
                    return { success: false, error: ERROR_TYPE.NO_RESULTS };
                }

                // Check for multiple results warning from adapter
                if ( result.warning === 'multiple_results' ) {
                    var multiMsg = 'Multiple matches found (' + result.resultCount +
                        ' results) - verify location is correct';
                    accumulatedWarnings.push({
                        type: WARNING_TYPE.MULTIPLE_RESULTS,
                        message: multiMsg,
                        resultCount: result.resultCount
                    });
                }

                // Validate coordinates if server location has them
                if ( serverLoc.latitude && serverLoc.longitude && result.coordinates ) {
                    var distance = calculateDistanceMeters(
                        serverLoc.latitude,
                        serverLoc.longitude,
                        result.coordinates.latitude,
                        result.coordinates.longitude
                    );

                    console.log( '[TT GMM Sync] Distance check:', {
                        serverCoords: { lat: serverLoc.latitude, lon: serverLoc.longitude },
                        gmmCoords: result.coordinates,
                        distance: distance,
                        threshold: COORDINATE_DISTANCE_THRESHOLD_M
                    });

                    if ( distance > COORDINATE_DISTANCE_THRESHOLD_M ) {
                        var distanceKm = ( distance / 1000 ).toFixed( 1 );
                        console.log( '[TT GMM Sync] Coordinate mismatch for:', serverLoc.title,
                            '- distance:', distanceKm, 'km' );
                        accumulatedWarnings.push({
                            type: WARNING_TYPE.COORDINATE_MISMATCH,
                            message: 'Location is ' + distanceKm + 'km away - verify location is correct',
                            distance: Math.round( distance )
                        });
                    }
                }

                // Success - update server location with gmm_id
                return updateServerLocationGmmId( serverLoc.uuid, result.gmmId )
                    .then( function() {
                        return TTGmmAdapter.closeInfoWindow();
                    })
                    .then( function() {
                        return {
                            success: true,
                            gmm: result,
                            warnings: accumulatedWarnings
                        };
                    });
            });
    }

    /**
     * Get GMM style options for a server location based on its category.
     * Falls back to "Other" layer with warnings for missing/unknown categories.
     * @param {Object} serverLoc - Server location with subcategory_slug.
     * @returns {Promise<Object>} Style options { layerTitle, colorRgb, iconCode, warnings }.
     */
    function getStyleOptionsForLocation( serverLoc ) {
        return getLocationCategories()
            .then( function( categories ) {
                var warnings = [];

                // Check for missing subcategory
                if ( !serverLoc.subcategory_slug ) {
                    warnings.push({
                        type: WARNING_TYPE.NO_CATEGORY,
                        message: WARNING_MESSAGES[WARNING_TYPE.NO_CATEGORY]
                    });
                    return {
                        layerTitle: TT.CONFIG.GMM_OTHER_LAYER_NAME,
                        colorRgb: TT.CONFIG.GMM_OTHER_LAYER_COLOR,
                        iconCode: TT.CONFIG.GMM_OTHER_LAYER_ICON,
                        warnings: warnings
                    };
                }

                // Find the category and subcategory
                for ( var i = 0; i < categories.length; i++ ) {
                    var category = categories[i];
                    var subcategories = category.subcategories || [];
                    var subcategory = subcategories.find( function( s ) {
                        return s.slug === serverLoc.subcategory_slug;
                    });
                    if ( subcategory ) {
                        return {
                            layerTitle: category.name,
                            colorRgb: subcategory.color_code || category.color_code,
                            iconCode: subcategory.icon_code || category.icon_code,
                            warnings: warnings
                        };
                    }
                }

                // Unknown subcategory - use Other layer
                warnings.push({
                    type: WARNING_TYPE.UNKNOWN_CATEGORY,
                    message: "Unknown category '" + serverLoc.subcategory_slug + "' - added to 'Other' layer"
                });
                return {
                    layerTitle: TT.CONFIG.GMM_OTHER_LAYER_NAME,
                    colorRgb: TT.CONFIG.GMM_OTHER_LAYER_COLOR,
                    iconCode: TT.CONFIG.GMM_OTHER_LAYER_ICON,
                    warnings: warnings
                };
            });
    }

    /**
     * Get location categories from client config via background.
     * @returns {Promise<Array>} Array of category objects.
     */
    function getLocationCategories() {
        return new Promise( function( resolve, reject ) {
            chrome.runtime.sendMessage({
                type: TT.MESSAGE.TYPE_GET_LOCATION_CATEGORIES
            }, function( response ) {
                if ( chrome.runtime.lastError ) {
                    reject( new Error( chrome.runtime.lastError.message ) );
                    return;
                }
                if ( response && response.success ) {
                    resolve( response.data.location_categories || [] );
                } else {
                    reject( new Error( response ? response.error : 'No response' ) );
                }
            });
        });
    }

    /**
     * Update a server location's gmm_id.
     * @param {string} locationUuid - Location UUID.
     * @param {string} gmmId - GMM location ID to set.
     * @returns {Promise<void>}
     */
    function updateServerLocationGmmId( locationUuid, gmmId ) {
        return new Promise( function( resolve, reject ) {
            chrome.runtime.sendMessage({
                type: TT.MESSAGE.TYPE_UPDATE_LOCATION,
                data: {
                    uuid: locationUuid,
                    updates: {
                        gmm_id: gmmId
                    }
                }
            }, function( response ) {
                if ( chrome.runtime.lastError ) {
                    reject( new Error( chrome.runtime.lastError.message ) );
                    return;
                }
                if ( response && response.success ) {
                    resolve();
                } else {
                    var errorMsg = ( response && response.data && response.data.error )
                        ? response.data.error
                        : 'Failed to update location';
                    reject( new Error( errorMsg ) );
                }
            });
        });
    }

    /**
     * Sync a GMM location to the server.
     * Opens the location to get full details, then saves to server.
     * @param {string} tripUuid - Trip UUID.
     * @param {Object} gmmLoc - GMM location { fl_id, title, icon_code, layer_title }.
     * @returns {Promise<Object>} Created server location.
     */
    function syncGmmLocationToServer( tripUuid, gmmLoc ) {
        console.log( '[TT GMM Sync] Syncing GMM location to server:', gmmLoc.title );

        // Open the location to get coordinates
        return TTGmmAdapter.openLocationById( gmmLoc.fl_id )
            .then( function( locationInfo ) {
                // Build location data for server
                var locationData = {
                    gmm_id: gmmLoc.fl_id,
                    title: locationInfo.title || gmmLoc.title
                };

                // Add coordinates if available
                if ( locationInfo.coordinates ) {
                    locationData.latitude = locationInfo.coordinates.latitude;
                    locationData.longitude = locationInfo.coordinates.longitude;
                }

                // Map category from layer name and icon (stub for now)
                var categoryMapping = mapToCategory( gmmLoc.layer_title, gmmLoc.icon_code );
                if ( categoryMapping ) {
                    locationData.category_slug = categoryMapping.category_slug;
                    if ( categoryMapping.subcategory_slug ) {
                        locationData.subcategory_slug = categoryMapping.subcategory_slug;
                    }
                }

                console.log( '[TT GMM Sync] Saving location to server:', locationData );

                return saveLocationToServer( tripUuid, locationData )
                    .then( function( serverResult ) {
                        return TTGmmAdapter.closeInfoWindow()
                            .then( function() {
                                return serverResult;
                            });
                    });
            });
    }

    /**
     * Map layer name and icon code to category/subcategory.
     * @param {string} layerTitle - GMM layer title.
     * @param {string} iconCode - GMM icon code.
     * @returns {Object|null} { category_slug, subcategory_slug } or null.
     */
    function mapToCategory( layerTitle, iconCode ) {
        // TODO: Implement proper category mapping
        // For now, try to match layer title to category name
        // This is a stub that can be enhanced later
        console.log( '[TT GMM Sync] Category mapping for layer:', layerTitle, 'icon:', iconCode );
        return null;
    }

    /**
     * Save location to server via background script.
     * @param {string} tripUuid - Trip UUID.
     * @param {Object} locationData - Location data.
     * @returns {Promise<Object>} Server response.
     */
    function saveLocationToServer( tripUuid, locationData ) {
        return new Promise( function( resolve, reject ) {
            chrome.runtime.sendMessage({
                type: TT.MESSAGE.TYPE_SAVE_LOCATION,
                data: locationData
            }, function( response ) {
                if ( chrome.runtime.lastError ) {
                    reject( new Error( chrome.runtime.lastError.message ) );
                    return;
                }
                if ( response && response.success ) {
                    resolve( response.data );
                } else {
                    var errorMsg = ( response && response.data && response.data.error )
                        ? response.data.error
                        : 'Failed to save location';
                    reject( new Error( errorMsg ) );
                }
            });
        });
    }

    /**
     * Delete location from server via background script.
     * @param {string} locationUuid - Location UUID.
     * @returns {Promise<void>}
     */
    function deleteServerLocation( locationUuid ) {
        return new Promise( function( resolve, reject ) {
            chrome.runtime.sendMessage({
                type: TT.MESSAGE.TYPE_DELETE_LOCATION,
                data: { uuid: locationUuid }
            }, function( response ) {
                if ( chrome.runtime.lastError ) {
                    reject( new Error( chrome.runtime.lastError.message ) );
                    return;
                }
                if ( response && response.success ) {
                    resolve();
                } else {
                    var errorMsg = ( response && response.data && response.data.error )
                        ? response.data.error
                        : 'Failed to delete location';
                    reject( new Error( errorMsg ) );
                }
            });
        });
    }

    /**
     * Fetch all locations for a trip from the server.
     * @param {string} tripUuid - The trip UUID.
     * @returns {Promise<Array>} Array of location objects.
     */
    function fetchServerLocations( tripUuid ) {
        return new Promise( function( resolve, reject ) {
            chrome.runtime.sendMessage(
                {
                    type: TT.MESSAGE.TYPE_GET_TRIP_LOCATIONS,
                    data: { tripUuid: tripUuid }
                },
                function( response ) {
                    if ( chrome.runtime.lastError ) {
                        reject( new Error( chrome.runtime.lastError.message ) );
                        return;
                    }
                    if ( response && response.success ) {
                        resolve( response.data.locations || [] );
                    } else {
                        reject( new Error( response && response.data && response.data.error
                            ? response.data.error : 'Failed to fetch locations' ) );
                    }
                }
            );
        });
    }

    /**
     * Get locations from GMM DOM.
     * Reads all locations from all layers using TTGmmAdapter.
     * @returns {Promise<Array>} Array of GMM location objects with fl_id.
     */
    function getGmmLocations() {
        var locations = [];

        try {
            var layers = TTGmmAdapter.getLayers();
            console.log( '[TT GMM Sync] Found ' + layers.length + ' layers' );

            layers.forEach( function( layer ) {
                var layerLocations = TTGmmAdapter.getLocationsInLayer( layer );
                console.log( '[TT GMM Sync] Layer "' + layer.title + '": ' +
                    layerLocations.length + ' locations' );

                layerLocations.forEach( function( loc ) {
                    locations.push({
                        fl_id: loc.id,
                        title: loc.title,
                        icon_code: loc.iconCode,
                        layer_id: layer.id,
                        layer_title: layer.title
                    });
                });
            });

            console.log( '[TT GMM Sync] Total GMM locations: ' + locations.length );
        } catch ( error ) {
            console.error( '[TT GMM Sync] Error reading GMM locations:', error );
        }

        return Promise.resolve( locations );
    }

    /**
     * Normalize a title for comparison (trim whitespace, lowercase).
     * @param {string} title - The title to normalize.
     * @returns {string} Normalized title.
     */
    function normalizeTitle( title ) {
        return ( title || '' ).trim().toLowerCase();
    }

    /**
     * Compare server and GMM locations to find differences.
     * Uses gmm_id (server) and fl_id (GMM) for matching.
     * Also detects title matches among unlinked locations.
     * @param {Array} serverLocations - Locations from server.
     * @param {Array} gmmLocations - Locations from GMM DOM.
     * @returns {Object} Diff result with serverOnly, gmmOnly, inBoth, suggestedMatches arrays.
     */
    function compareLocations( serverLocations, gmmLocations ) {
        // Build lookup of GMM fl_ids
        var gmmIdSet = {};
        gmmLocations.forEach( function( loc ) {
            if ( loc.fl_id ) {
                gmmIdSet[loc.fl_id] = loc;
            }
        });

        // Build lookup of server gmm_ids
        var serverGmmIdSet = {};
        serverLocations.forEach( function( loc ) {
            if ( loc.gmm_id ) {
                serverGmmIdSet[loc.gmm_id] = loc;
            }
        });

        var serverOnlyInitial = [];
        var inBoth = [];

        // Check each server location
        serverLocations.forEach( function( serverLoc ) {
            if ( serverLoc.gmm_id && gmmIdSet[serverLoc.gmm_id] ) {
                // Found in both
                inBoth.push( {
                    server: serverLoc,
                    gmm: gmmIdSet[serverLoc.gmm_id]
                });
            } else {
                // Server only (no gmm_id or not found in GMM)
                serverOnlyInitial.push( serverLoc );
            }
        });

        // Check for GMM-only locations
        var gmmOnlyInitial = [];
        gmmLocations.forEach( function( gmmLoc ) {
            if ( gmmLoc.fl_id && !serverGmmIdSet[gmmLoc.fl_id] ) {
                gmmOnlyInitial.push( gmmLoc );
            }
        });

        // Find title matches among unlinked locations
        var suggestedMatches = [];
        var serverOnly = [];
        var gmmOnly = [];

        // Build normalized title lookup for GMM-only locations
        var gmmByNormalizedTitle = {};
        gmmOnlyInitial.forEach( function( gmmLoc ) {
            var normalized = normalizeTitle( gmmLoc.title );
            if ( !gmmByNormalizedTitle[normalized] ) {
                gmmByNormalizedTitle[normalized] = [];
            }
            gmmByNormalizedTitle[normalized].push( gmmLoc );
        });

        // Check each server-only location for title match
        serverOnlyInitial.forEach( function( serverLoc ) {
            var normalized = normalizeTitle( serverLoc.title );
            var gmmMatches = gmmByNormalizedTitle[normalized];

            if ( gmmMatches && gmmMatches.length > 0 ) {
                // Take first match, remove from available pool
                var gmmMatch = gmmMatches.shift();
                suggestedMatches.push( {
                    server: serverLoc,
                    gmm: gmmMatch
                });
            } else {
                serverOnly.push( serverLoc );
            }
        });

        // Remaining GMM locations (not matched by title)
        Object.keys( gmmByNormalizedTitle ).forEach( function( key ) {
            gmmByNormalizedTitle[key].forEach( function( gmmLoc ) {
                gmmOnly.push( gmmLoc );
            });
        });

        return {
            serverOnly: serverOnly,
            gmmOnly: gmmOnly,
            inBoth: inBoth,
            suggestedMatches: suggestedMatches
        };
    }

    /**
     * Show the sync compare dialog with diff results.
     * Shows per-location KEEP/DISCARD toggles for differences.
     * Shows Link/Don't Link toggles for suggested title matches.
     * @param {Object} data - Sync request data (tripUuid, tripTitle, etc.).
     * @param {Object} diff - Diff results from compareLocations.
     * @returns {Promise<Object>} Result of sync operation.
     */
    function showSyncCompareDialog( data, diff ) {
        return new Promise( function( resolve ) {
            // Remove any existing dialog
            var existingDialog = document.querySelector( '.' + TT_SYNC_DIALOG_CLASS );
            if ( existingDialog ) {
                existingDialog.remove();
            }

            // Track sync decisions - all default to KEEP/LINK
            var syncDecisions = {};

            // Create dialog container
            var dialog = TTDom.createElement( 'div', {
                className: TT_SYNC_DIALOG_CLASS
            });

            // Header
            var header = TTDom.createElement( 'div', {
                className: 'tt-sync-header',
                text: 'Sync Locations'
            });
            dialog.appendChild( header );

            // Trip info
            var tripInfo = TTDom.createElement( 'div', {
                className: 'tt-sync-trip-info',
                text: 'Trip: ' + ( data.tripTitle || 'Unknown' )
            });
            dialog.appendChild( tripInfo );

            var hasSuggestedMatches = diff.suggestedMatches && diff.suggestedMatches.length > 0;
            var hasDifferences = diff.serverOnly.length > 0 || diff.gmmOnly.length > 0;
            var hasAnyAction = hasSuggestedMatches || hasDifferences;

            // Suggested Matches section (shown first if present)
            if ( hasSuggestedMatches ) {
                var matchSection = TTDom.createElement( 'div', {
                    className: 'tt-sync-section tt-sync-section-suggested'
                });

                var matchHeader = TTDom.createElement( 'div', {
                    className: 'tt-sync-section-header',
                    text: 'Suggested Matches (' + diff.suggestedMatches.length + ')'
                });
                matchSection.appendChild( matchHeader );

                var matchList = TTDom.createElement( 'div', {
                    className: 'tt-sync-location-list'
                });

                diff.suggestedMatches.forEach( function( match ) {
                    var itemId = 'match_' + match.server.uuid;
                    syncDecisions[itemId] = {
                        action: 'link',
                        source: 'match',
                        server: match.server,
                        gmm: match.gmm
                    };
                    var item = createSuggestedMatchItem(
                        match.server.title,
                        itemId,
                        syncDecisions
                    );
                    matchList.appendChild( item );
                });

                matchSection.appendChild( matchList );
                dialog.appendChild( matchSection );
            }

            // Differences section
            if ( hasDifferences ) {
                var diffSection = TTDom.createElement( 'div', {
                    className: 'tt-sync-section'
                });

                var diffHeader = TTDom.createElement( 'div', {
                    className: 'tt-sync-section-header',
                    text: 'Differences'
                });
                diffSection.appendChild( diffHeader );

                // Location list
                var locationList = TTDom.createElement( 'div', {
                    className: 'tt-sync-location-list'
                });

                // Add server-only locations
                diff.serverOnly.forEach( function( loc ) {
                    var itemId = 'server_' + loc.uuid;
                    syncDecisions[itemId] = { action: 'keep', source: 'server', location: loc };
                    var item = createLocationItem( loc.title, 'Server only', 'server', itemId, syncDecisions );
                    locationList.appendChild( item );
                });

                // Add GMM-only locations
                diff.gmmOnly.forEach( function( loc ) {
                    var itemId = 'gmm_' + loc.fl_id;
                    syncDecisions[itemId] = { action: 'keep', source: 'gmm', location: loc };
                    var item = createLocationItem( loc.title, 'GMM only', 'gmm', itemId, syncDecisions );
                    locationList.appendChild( item );
                });

                diffSection.appendChild( locationList );
                dialog.appendChild( diffSection );
            }

            // Summary section (always shown)
            var summarySection = TTDom.createElement( 'div', {
                className: 'tt-sync-section'
            });

            if ( hasAnyAction ) {
                var summaryText = TTDom.createElement( 'div', {
                    className: 'tt-sync-summary'
                });
                var inSyncSpan = TTDom.createElement( 'span', {
                    className: 'tt-sync-summary-count',
                    text: diff.inBoth.length
                });
                summaryText.appendChild( inSyncSpan );
                summaryText.appendChild( document.createTextNode(
                    ' location' + ( diff.inBoth.length !== 1 ? 's' : '' ) + ' already in sync'
                ));
                summarySection.appendChild( summaryText );
            } else {
                var inSyncMessage = TTDom.createElement( 'div', {
                    className: 'tt-sync-in-sync-message',
                    text: 'All ' + diff.inBoth.length + ' locations are in sync!'
                });
                summarySection.appendChild( inSyncMessage );
            }

            dialog.appendChild( summarySection );

            // Button container
            var buttonContainer = TTDom.createElement( 'div', {
                className: 'tt-sync-buttons'
            });

            var closeBtn = TTDom.createElement( 'button', {
                className: 'tt-gmm-btn tt-cancel-btn',
                text: hasAnyAction ? 'Cancel' : 'Close'
            });
            closeBtn.addEventListener( 'click', function() {
                dialog.remove();
                resolve( { cancelled: true } );
            });
            buttonContainer.appendChild( closeBtn );

            if ( hasAnyAction ) {
                var syncBtn = TTDom.createElement( 'button', {
                    className: 'tt-gmm-btn tt-category-btn',
                    text: 'Apply Sync'
                });
                syncBtn.addEventListener( 'click', function() {
                    dialog.remove();
                    resolve( { cancelled: false, decisions: syncDecisions } );
                });
                buttonContainer.appendChild( syncBtn );
            }

            dialog.appendChild( buttonContainer );

            document.body.appendChild( dialog );
            console.log( '[TT Sync Compare] Dialog displayed' );
        });
    }

    /**
     * Create a suggested match item row with Link/Don't Link toggle.
     * @param {string} title - Location title (same in both places).
     * @param {string} itemId - Unique identifier for this item.
     * @param {Object} syncDecisions - Reference to decisions object.
     * @returns {Element} The location item element.
     */
    function createSuggestedMatchItem( title, itemId, syncDecisions ) {
        var item = TTDom.createElement( 'div', {
            className: 'tt-sync-location-item tt-sync-suggested-match'
        });

        // Location info
        var info = TTDom.createElement( 'div', {
            className: 'tt-sync-location-info'
        });

        var titleEl = TTDom.createElement( 'div', {
            className: 'tt-sync-location-title',
            text: title
        });
        info.appendChild( titleEl );

        var sourceEl = TTDom.createElement( 'div', {
            className: 'tt-sync-location-source tt-sync-location-source-match',
            text: 'Same name found in both places'
        });
        info.appendChild( sourceEl );

        item.appendChild( info );

        // Toggle buttons
        var toggle = TTDom.createElement( 'div', {
            className: 'tt-sync-toggle'
        });

        var linkBtn = TTDom.createElement( 'button', {
            className: 'tt-sync-toggle-btn tt-toggle-link',
            text: 'Link'
        });

        var dontLinkBtn = TTDom.createElement( 'button', {
            className: 'tt-sync-toggle-btn',
            text: "Don't Link"
        });

        linkBtn.addEventListener( 'click', function() {
            syncDecisions[itemId].action = 'link';
            linkBtn.classList.add( 'tt-toggle-link' );
            dontLinkBtn.classList.remove( 'tt-toggle-dont-link' );
        });

        dontLinkBtn.addEventListener( 'click', function() {
            syncDecisions[itemId].action = 'dont_link';
            dontLinkBtn.classList.add( 'tt-toggle-dont-link' );
            linkBtn.classList.remove( 'tt-toggle-link' );
        });

        toggle.appendChild( linkBtn );
        toggle.appendChild( dontLinkBtn );
        item.appendChild( toggle );

        return item;
    }

    /**
     * Show sync execute results dialog after sync completes.
     * Three-tier display: Synced (green), Needs Review (yellow), Failed (red).
     * @param {Object} results - Sync results object.
     * @returns {Promise<Object>} The results (passed through).
     */
    function showSyncExecuteResultsDialog( results ) {
        return new Promise( function( resolve ) {
            // Remove any existing dialog
            var existingDialog = document.querySelector( '.' + TT_SYNC_DIALOG_CLASS );
            if ( existingDialog ) {
                existingDialog.remove();
            }

            // Create dialog container
            var dialog = TTDom.createElement( 'div', {
                className: TT_SYNC_DIALOG_CLASS
            });

            // Header
            var headerText = results.stopped ? 'Sync Stopped' : 'Sync Complete';
            var header = TTDom.createElement( 'div', {
                className: 'tt-sync-header',
                text: headerText
            });
            dialog.appendChild( header );

            // If stopped, show a notice
            if ( results.stopped ) {
                var stoppedNotice = TTDom.createElement( 'div', {
                    className: 'tt-sync-stopped-notice',
                    text: 'Sync was stopped before completion. Partial results shown below.'
                });
                dialog.appendChild( stoppedNotice );
            }

            // Count clean successes (warnings shown separately)
            var linkedByTitleCount = results.linkedByTitle ? results.linkedByTitle.length : 0;
            var cleanSuccessCount = results.addedToServer.length + results.addedToGmm.length +
                              linkedByTitleCount +
                              results.deletedFromServer.length + results.deletedFromGmm.length;
            var hasCleanSuccesses = cleanSuccessCount > 0;
            var hasWarnings = results.warnings && results.warnings.length > 0;
            var hasFailures = results.failures && results.failures.length > 0;
            var hasErrors = results.errors && results.errors.length > 0;

            // ========== SYNCED SECTION (green) ==========
            if ( hasCleanSuccesses ) {
                var syncedSection = TTDom.createElement( 'div', {
                    className: 'tt-sync-section tt-sync-section-success'
                });

                var syncedHeader = TTDom.createElement( 'div', {
                    className: 'tt-sync-section-header tt-sync-header-success',
                    text: '\u2713 SYNCED (' + cleanSuccessCount + ')'
                });
                syncedSection.appendChild( syncedHeader );

                var syncedList = TTDom.createElement( 'div', {
                    className: 'tt-sync-location-list'
                });

                // GMM -> Server (ADDED)
                results.addedToServer.forEach( function( item ) {
                    var row = createSyncedRow( item.gmm.title, 'ADDED', false );
                    syncedList.appendChild( row );
                });

                // Server -> GMM without warnings (MATCHED)
                results.addedToGmm.forEach( function( item ) {
                    var googleTitle = item.gmm ? item.gmm.googleTitle : null;
                    var row = createSyncedRow( item.server.title, 'MATCHED', true, googleTitle );
                    syncedList.appendChild( row );
                });

                // Linked by title (LINKED)
                if ( results.linkedByTitle ) {
                    results.linkedByTitle.forEach( function( item ) {
                        var row = createSyncedRow( item.server.title, 'LINKED', false );
                        syncedList.appendChild( row );
                    });
                }

                // Deletions
                results.deletedFromServer.forEach( function( loc ) {
                    var row = createSyncedRow( loc.title, 'REMOVED', false );
                    syncedList.appendChild( row );
                });
                results.deletedFromGmm.forEach( function( loc ) {
                    var row = createSyncedRow( loc.title, 'REMOVED', false );
                    syncedList.appendChild( row );
                });

                syncedSection.appendChild( syncedList );
                dialog.appendChild( syncedSection );
            }

            // ========== WARNINGS SECTION (yellow) ==========
            if ( hasWarnings ) {
                var warningsSection = TTDom.createElement( 'div', {
                    className: 'tt-sync-section tt-sync-section-warning'
                });

                var warningsHeader = TTDom.createElement( 'div', {
                    className: 'tt-sync-section-header tt-sync-header-warning',
                    text: '\u26A0 NEEDS REVIEW (' + results.warnings.length + ')'
                });
                warningsSection.appendChild( warningsHeader );

                var warningsList = TTDom.createElement( 'div', {
                    className: 'tt-sync-location-list'
                });

                results.warnings.forEach( function( item ) {
                    var row = createWarningRow( item.server.title, item.warnings, item.gmm );
                    warningsList.appendChild( row );
                });

                warningsSection.appendChild( warningsList );
                dialog.appendChild( warningsSection );
            }

            // ========== FAILURES SECTION (red) ==========
            if ( hasFailures ) {
                var failuresSection = TTDom.createElement( 'div', {
                    className: 'tt-sync-section tt-sync-section-error'
                });

                var failuresHeader = TTDom.createElement( 'div', {
                    className: 'tt-sync-section-header tt-sync-header-error',
                    text: '\u2717 FAILED (' + results.failures.length + ')'
                });
                failuresSection.appendChild( failuresHeader );

                var failuresList = TTDom.createElement( 'div', {
                    className: 'tt-sync-location-list'
                });

                results.failures.forEach( function( item ) {
                    var row = createFailureRow( item.server.title, item.error, item.resultCount );
                    failuresList.appendChild( row );
                });

                failuresSection.appendChild( failuresList );
                dialog.appendChild( failuresSection );
            }

            // ========== ERRORS SECTION (unexpected errors) ==========
            if ( hasErrors ) {
                var errorsSection = TTDom.createElement( 'div', {
                    className: 'tt-sync-section tt-sync-section-error'
                });

                var errorsHeader = TTDom.createElement( 'div', {
                    className: 'tt-sync-section-header tt-sync-header-error',
                    text: '\u2717 ERRORS (' + results.errors.length + ')'
                });
                errorsSection.appendChild( errorsHeader );

                results.errors.forEach( function( err ) {
                    var errorRow = TTDom.createElement( 'div', {
                        className: 'tt-sync-result-row'
                    });
                    var label = TTDom.createElement( 'span', {
                        className: 'tt-sync-result-title',
                        text: err.location ? err.location.title : 'Unknown'
                    });
                    var value = TTDom.createElement( 'span', {
                        className: 'tt-sync-result-error-text',
                        text: err.error
                    });
                    errorRow.appendChild( label );
                    errorRow.appendChild( value );
                    errorsSection.appendChild( errorRow );
                });

                dialog.appendChild( errorsSection );
            }

            // No activity message
            if ( !hasCleanSuccesses && !hasWarnings && !hasFailures && !hasErrors ) {
                var noActivityMsg = TTDom.createElement( 'div', {
                    className: 'tt-sync-in-sync-message',
                    text: 'No changes were made.'
                });
                dialog.appendChild( noActivityMsg );
            }

            // Button container
            var buttonContainer = TTDom.createElement( 'div', {
                className: 'tt-sync-buttons'
            });

            var closeBtn = TTDom.createElement( 'button', {
                className: 'tt-gmm-btn tt-cancel-btn',
                text: 'Close'
            });
            closeBtn.addEventListener( 'click', function() {
                dialog.remove();
                resolve( results );
            });
            buttonContainer.appendChild( closeBtn );

            dialog.appendChild( buttonContainer );

            document.body.appendChild( dialog );
            console.log( '[TT Sync Execute] Results dialog displayed' );
        });
    }

    /**
     * Create a synced row for the results dialog (success tier).
     * @param {string} title - Location title (server title).
     * @param {string} status - Status label (ADDED, MATCHED, REMOVED).
     * @param {boolean} showUndoStub - Whether to show [Undo] stub button.
     * @param {string} [googleTitle] - The Google title that was matched to.
     * @returns {Element} The row element.
     */
    function createSyncedRow( title, status, showUndoStub, googleTitle ) {
        // If we have a googleTitle, use result-item container for multi-line display
        if ( googleTitle ) {
            var item = TTDom.createElement( 'div', {
                className: 'tt-sync-result-item'
            });

            var titleRow = TTDom.createElement( 'div', {
                className: 'tt-sync-result-row'
            });

            var titleEl = TTDom.createElement( 'span', {
                className: 'tt-sync-result-title',
                text: title
            });
            titleRow.appendChild( titleEl );

            var actionsEl = TTDom.createElement( 'div', {
                className: 'tt-sync-result-actions'
            });

            var statusEl = TTDom.createElement( 'span', {
                className: 'tt-sync-status tt-sync-status-' + status.toLowerCase(),
                text: status
            });
            actionsEl.appendChild( statusEl );

            if ( showUndoStub ) {
                var undoBtn = TTDom.createElement( 'button', {
                    className: 'tt-sync-action-btn',
                    text: 'Undo'
                });
                undoBtn.disabled = true;
                undoBtn.title = 'Coming soon';
                actionsEl.appendChild( undoBtn );
            }

            titleRow.appendChild( actionsEl );
            item.appendChild( titleRow );

            // Add "Matched to" line
            var matchedEl = TTDom.createElement( 'div', {
                className: 'tt-sync-item-message tt-sync-item-matched',
                text: "Matched to '" + googleTitle + "'"
            });
            item.appendChild( matchedEl );

            return item;
        }

        // Simple single-line row for non-matched items
        var row = TTDom.createElement( 'div', {
            className: 'tt-sync-result-row'
        });

        var titleEl = TTDom.createElement( 'span', {
            className: 'tt-sync-result-title',
            text: title
        });
        row.appendChild( titleEl );

        var actionsEl = TTDom.createElement( 'div', {
            className: 'tt-sync-result-actions'
        });

        var statusEl = TTDom.createElement( 'span', {
            className: 'tt-sync-status tt-sync-status-' + status.toLowerCase(),
            text: status
        });
        actionsEl.appendChild( statusEl );

        if ( showUndoStub ) {
            var undoBtn = TTDom.createElement( 'button', {
                className: 'tt-sync-action-btn',
                text: 'Undo'
            });
            undoBtn.disabled = true;
            undoBtn.title = 'Coming soon';
            actionsEl.appendChild( undoBtn );
        }

        row.appendChild( actionsEl );
        return row;
    }

    /**
     * Create a warning row for the results dialog (warning tier).
     * @param {string} title - Location title (server title).
     * @param {Array} warnings - Array of warning objects.
     * @param {Object} gmm - GMM location info (for potential undo and googleTitle).
     * @returns {Element} The row element.
     */
    function createWarningRow( title, warnings, gmm ) {
        var item = TTDom.createElement( 'div', {
            className: 'tt-sync-result-item'
        });

        // Title row with Undo button
        var titleRow = TTDom.createElement( 'div', {
            className: 'tt-sync-result-row'
        });

        var titleEl = TTDom.createElement( 'span', {
            className: 'tt-sync-result-title',
            text: title
        });
        titleRow.appendChild( titleEl );

        var actionsEl = TTDom.createElement( 'div', {
            className: 'tt-sync-result-actions'
        });

        var undoBtn = TTDom.createElement( 'button', {
            className: 'tt-sync-action-btn',
            text: 'Undo'
        });
        undoBtn.disabled = true;
        undoBtn.title = 'Coming soon';
        actionsEl.appendChild( undoBtn );

        titleRow.appendChild( actionsEl );
        item.appendChild( titleRow );

        // "Matched to" line (always show for warnings since they are matched)
        if ( gmm && gmm.googleTitle ) {
            var matchedEl = TTDom.createElement( 'div', {
                className: 'tt-sync-item-message tt-sync-item-matched',
                text: "Matched to '" + gmm.googleTitle + "'"
            });
            item.appendChild( matchedEl );
        }

        // Warning messages
        warnings.forEach( function( warning ) {
            var msgEl = TTDom.createElement( 'div', {
                className: 'tt-sync-item-message tt-sync-item-message-warning',
                text: warning.message
            });
            item.appendChild( msgEl );
        });

        return item;
    }

    /**
     * Create a failure row for the results dialog (failure tier).
     * @param {string} title - Location title.
     * @param {string} error - Error type.
     * @param {number} resultCount - Optional search result count.
     * @returns {Element} The row element.
     */
    function createFailureRow( title, error, resultCount ) {
        var item = TTDom.createElement( 'div', {
            className: 'tt-sync-result-item'
        });

        // Title row with Fix button
        var titleRow = TTDom.createElement( 'div', {
            className: 'tt-sync-result-row'
        });

        var titleEl = TTDom.createElement( 'span', {
            className: 'tt-sync-result-title',
            text: title
        });
        titleRow.appendChild( titleEl );

        var actionsEl = TTDom.createElement( 'div', {
            className: 'tt-sync-result-actions'
        });

        var fixBtn = TTDom.createElement( 'button', {
            className: 'tt-sync-action-btn',
            text: 'Fix'
        });
        fixBtn.disabled = true;
        fixBtn.title = 'Coming soon';
        actionsEl.appendChild( fixBtn );

        titleRow.appendChild( actionsEl );
        item.appendChild( titleRow );

        // Error message
        var errorMsg = ERROR_MESSAGES[error] || error;
        if ( resultCount && resultCount > 1 ) {
            if ( error === ERROR_TYPE.NO_DIALOG ) {
                errorMsg = 'Multiple matches found (' + resultCount + ' results)';
            } else if ( error === ERROR_TYPE.TOO_MANY_RESULTS ) {
                errorMsg = 'Too many matches (' + resultCount + ' results) - search manually';
            }
        } else if ( resultCount === 1 && error === ERROR_TYPE.NO_DIALOG ) {
            errorMsg = 'Result found but could not add - try manually';
        }

        var msgEl = TTDom.createElement( 'div', {
            className: 'tt-sync-item-message tt-sync-item-message-error',
            text: errorMsg
        });
        item.appendChild( msgEl );

        return item;
    }

    /**
     * Create a location item row with KEEP/DISCARD toggle.
     * @param {string} title - Location title.
     * @param {string} sourceText - Source description (e.g., "Server only").
     * @param {string} sourceType - Source type ('server' or 'gmm').
     * @param {string} itemId - Unique identifier for this item.
     * @param {Object} syncDecisions - Reference to decisions object.
     * @returns {Element} The location item element.
     */
    function createLocationItem( title, sourceText, sourceType, itemId, syncDecisions ) {
        var item = TTDom.createElement( 'div', {
            className: 'tt-sync-location-item'
        });

        // Location info
        var info = TTDom.createElement( 'div', {
            className: 'tt-sync-location-info'
        });

        var titleEl = TTDom.createElement( 'div', {
            className: 'tt-sync-location-title',
            text: title
        });
        info.appendChild( titleEl );

        var sourceEl = TTDom.createElement( 'div', {
            className: 'tt-sync-location-source tt-sync-location-source-' + sourceType,
            text: sourceText
        });
        info.appendChild( sourceEl );

        item.appendChild( info );

        // Toggle buttons
        var toggle = TTDom.createElement( 'div', {
            className: 'tt-sync-toggle'
        });

        var keepBtn = TTDom.createElement( 'button', {
            className: 'tt-sync-toggle-btn tt-toggle-keep',
            text: 'Keep'
        });

        var discardBtn = TTDom.createElement( 'button', {
            className: 'tt-sync-toggle-btn',
            text: 'Discard'
        });

        keepBtn.addEventListener( 'click', function() {
            syncDecisions[itemId].action = 'keep';
            keepBtn.classList.add( 'tt-toggle-keep' );
            discardBtn.classList.remove( 'tt-toggle-discard' );
        });

        discardBtn.addEventListener( 'click', function() {
            syncDecisions[itemId].action = 'discard';
            discardBtn.classList.add( 'tt-toggle-discard' );
            keepBtn.classList.remove( 'tt-toggle-keep' );
        });

        toggle.appendChild( keepBtn );
        toggle.appendChild( discardBtn );
        item.appendChild( toggle );

        return item;
    }

    // Initialize on load
    initSync();

})();
