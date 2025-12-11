/*
 * Trip Tools Chrome Extension - GMM Location Sync
 * Handles location synchronization between GMM and Trip Tools server.
 */

( function() {
    'use strict';

    var TT_SYNC_DIALOG_CLASS = 'tt-sync-dialog';

    // Distance threshold for coordinate validation (meters)
    var COORDINATE_DISTANCE_THRESHOLD_M = 1000;

    // Issue types for post-sync reconciliation
    var ISSUE_TYPE = {
        NO_SUBCATEGORY: 'no_subcategory',
        UNKNOWN_SUBCATEGORY: 'unknown_subcategory',
        NO_RESULTS: 'no_results',
        MULTIPLE_RESULTS: 'multiple_results',
        COORDINATE_MISMATCH: 'coordinate_mismatch'
    };

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

    /**
     * Perform the sync operation: fetch data, compare, show dialog, execute.
     * @param {Object} data - Sync request data (tripUuid, tripTitle, mapId).
     * @returns {Promise<Object>} Result of sync operation.
     */
    function performSync( data ) {
        console.log( '[TT GMM Sync] Fetching locations for comparison...' );

        return Promise.all( [
            fetchServerLocations( data.tripUuid ),
            getGmmLocations()
        ])
        .then( function( results ) {
            var serverLocations = results[0];
            var gmmLocations = results[1];

            console.log( '[TT GMM Sync] Server locations:', serverLocations.length );
            console.log( '[TT GMM Sync] GMM locations:', gmmLocations.length );

            var diff = compareLocations( serverLocations, gmmLocations );

            console.log( '[TT GMM Sync] Diff results:', {
                serverOnly: diff.serverOnly.length,
                gmmOnly: diff.gmmOnly.length,
                inBoth: diff.inBoth.length
            });

            return showSyncDialog( data, diff );
        })
        .then( function( dialogResult ) {
            if ( dialogResult.cancelled ) {
                console.log( '[TT GMM Sync] Sync cancelled by user' );
                return { cancelled: true };
            }

            console.log( '[TT GMM Sync] Executing sync with decisions:', dialogResult.decisions );
            return executeSyncDecisions( data.tripUuid, dialogResult.decisions );
        })
        .then( function( results ) {
            if ( results.cancelled ) {
                return results;
            }

            // Show results dialog
            return showSyncResultsDialog( results );
        });
    }

    /**
     * Execute sync decisions from the dialog.
     * @param {string} tripUuid - Trip UUID.
     * @param {Object} decisions - Map of itemId to { action, source, location }.
     * @returns {Promise<Object>} Sync results.
     */
    function executeSyncDecisions( tripUuid, decisions ) {
        var gmmToServerKeep = [];
        var gmmToDiscard = [];
        var serverToGmmKeep = [];
        var serverToDiscard = [];

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
            }
        });

        console.log( '[TT GMM Sync] GMM->Server (keep):', gmmToServerKeep.length );
        console.log( '[TT GMM Sync] GMM (discard):', gmmToDiscard.length );
        console.log( '[TT GMM Sync] Server->GMM (keep):', serverToGmmKeep.length );
        console.log( '[TT GMM Sync] Server (discard):', serverToDiscard.length );

        // Execute syncs sequentially (need to click each location)
        var syncPromise = Promise.resolve();
        var results = {
            addedToServer: [],
            addedToGmm: [],
            deletedFromServer: [],
            deletedFromGmm: [],
            errors: [],
            issues: [] // Categorized issues for post-sync reconciliation
        };

        // GMM -> Server (keep): add to server
        gmmToServerKeep.forEach( function( gmmLoc ) {
            syncPromise = syncPromise.then( function() {
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
                return syncServerLocationToGmm( serverLoc, results.issues )
                    .then( function( syncResult ) {
                        if ( syncResult.success ) {
                            results.addedToGmm.push( { server: serverLoc, gmm: syncResult.gmm } );
                        }
                        // Issues are already added to results.issues by syncServerLocationToGmm
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

        return syncPromise.then( function() {
            console.log( '[TT GMM Sync] Sync complete:', results );
            return results;
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
     * Handles edge cases by adding issues to the issues array:
     * - NO_SUBCATEGORY: Location has no subcategory_slug
     * - UNKNOWN_SUBCATEGORY: Subcategory not found in config
     * - NO_RESULTS: Search returned no results
     * - MULTIPLE_RESULTS: Search returned multiple results
     * - COORDINATE_MISMATCH: GMM location is too far from server coordinates
     *
     * @param {Object} serverLoc - Server location object.
     * @param {Array} issues - Array to push issues into.
     * @returns {Promise<Object>} Result { success: boolean, gmm?: Object }.
     */
    function syncServerLocationToGmm( serverLoc, issues ) {
        console.log( '[TT GMM Sync] Syncing server location to GMM:', serverLoc.title );

        // Check for subcategory
        if ( !serverLoc.subcategory_slug ) {
            console.log( '[TT GMM Sync] No subcategory for:', serverLoc.title );
            issues.push({
                type: ISSUE_TYPE.NO_SUBCATEGORY,
                location: serverLoc,
                message: 'Location has no subcategory assigned'
            });
            return Promise.resolve( { success: false } );
        }

        var styleOptions;

        // Get styling info from category
        return getStyleOptionsForLocation( serverLoc )
            .then( function( options ) {
                styleOptions = options;
                console.log( '[TT GMM Sync] Style options:', styleOptions );

                // Search and add to GMM
                return TTGmmAdapter.searchAndAddLocation( serverLoc.title, styleOptions );
            })
            .then( function( result ) {
                console.log( '[TT GMM Sync] Search result:', result );

                // Check for multiple results or no results
                if ( !result || !result.gmmId ) {
                    console.log( '[TT GMM Sync] No results for:', serverLoc.title );
                    issues.push({
                        type: ISSUE_TYPE.NO_RESULTS,
                        location: serverLoc,
                        message: 'Search returned no results'
                    });
                    return { success: false };
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
                        console.log( '[TT GMM Sync] Coordinate mismatch for:', serverLoc.title,
                            '- distance:', Math.round( distance ), 'm' );
                        issues.push({
                            type: ISSUE_TYPE.COORDINATE_MISMATCH,
                            location: serverLoc,
                            gmmResult: result,
                            distance: Math.round( distance ),
                            message: 'GMM result is ' + Math.round( distance ) + 'm away (threshold: ' +
                                COORDINATE_DISTANCE_THRESHOLD_M + 'm)'
                        });
                        return { success: false };
                    }
                }

                // Success - update server location with gmm_id
                return updateServerLocationGmmId( serverLoc.uuid, result.gmmId )
                    .then( function() {
                        return TTGmmAdapter.closeInfoWindow();
                    })
                    .then( function() {
                        return { success: true, gmm: result };
                    });
            })
            .catch( function( error ) {
                // Handle "Unknown subcategory" error specifically
                if ( error.message && error.message.indexOf( 'Unknown subcategory' ) !== -1 ) {
                    issues.push({
                        type: ISSUE_TYPE.UNKNOWN_SUBCATEGORY,
                        location: serverLoc,
                        message: error.message
                    });
                    return { success: false };
                }

                // Handle "multiple results" error (from searchAndAddLocation)
                if ( error.message && error.message.indexOf( 'multiple' ) !== -1 ) {
                    issues.push({
                        type: ISSUE_TYPE.MULTIPLE_RESULTS,
                        location: serverLoc,
                        message: 'Multiple search results found'
                    });
                    return { success: false };
                }

                // Re-throw unexpected errors
                throw error;
            });
    }

    /**
     * Get GMM style options for a server location based on its category.
     * @param {Object} serverLoc - Server location with subcategory_slug.
     * @returns {Promise<Object>} Style options { layerTitle, colorRgb, iconCode }.
     */
    function getStyleOptionsForLocation( serverLoc ) {
        return getLocationCategories()
            .then( function( categories ) {
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
                            iconCode: subcategory.icon_code || category.icon_code
                        };
                    }
                }

                // Subcategory not found in config
                return Promise.reject( new Error( 'Unknown subcategory: ' + serverLoc.subcategory_slug ) );
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
     * Compare server and GMM locations to find differences.
     * Uses gmm_id (server) and fl_id (GMM) for matching.
     * @param {Array} serverLocations - Locations from server.
     * @param {Array} gmmLocations - Locations from GMM DOM.
     * @returns {Object} Diff result with serverOnly, gmmOnly, inBoth arrays.
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

        var serverOnly = [];
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
                serverOnly.push( serverLoc );
            }
        });

        // Check for GMM-only locations
        var gmmOnly = [];
        gmmLocations.forEach( function( gmmLoc ) {
            if ( gmmLoc.fl_id && !serverGmmIdSet[gmmLoc.fl_id] ) {
                gmmOnly.push( gmmLoc );
            }
        });

        return {
            serverOnly: serverOnly,
            gmmOnly: gmmOnly,
            inBoth: inBoth
        };
    }

    /**
     * Show the sync dialog with diff results.
     * Shows per-location KEEP/DISCARD toggles for differences.
     * @param {Object} data - Sync request data (tripUuid, tripTitle, etc.).
     * @param {Object} diff - Diff results from compareLocations.
     * @returns {Promise<Object>} Result of sync operation.
     */
    function showSyncDialog( data, diff ) {
        return new Promise( function( resolve ) {
            // Remove any existing dialog
            var existingDialog = document.querySelector( '.' + TT_SYNC_DIALOG_CLASS );
            if ( existingDialog ) {
                existingDialog.remove();
            }

            // Track sync decisions - all default to KEEP
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

            var hasDifferences = diff.serverOnly.length > 0 || diff.gmmOnly.length > 0;

            if ( hasDifferences ) {
                // Differences section
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

            if ( hasDifferences ) {
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
                text: hasDifferences ? 'Cancel' : 'Close'
            });
            closeBtn.addEventListener( 'click', function() {
                dialog.remove();
                resolve( { cancelled: true } );
            });
            buttonContainer.appendChild( closeBtn );

            if ( hasDifferences ) {
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
            console.log( '[TT GMM Sync] Sync dialog displayed' );
        });
    }

    /**
     * Show sync results dialog after sync completes.
     * Displays successes, errors, and issues requiring user attention.
     * @param {Object} results - Sync results object.
     * @returns {Promise<Object>} The results (passed through).
     */
    function showSyncResultsDialog( results ) {
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
            var header = TTDom.createElement( 'div', {
                className: 'tt-sync-header',
                text: 'Sync Complete'
            });
            dialog.appendChild( header );

            // Success counts section
            var successSection = TTDom.createElement( 'div', {
                className: 'tt-sync-section'
            });

            var hasSuccesses = results.addedToServer.length > 0 ||
                               results.addedToGmm.length > 0 ||
                               results.deletedFromServer.length > 0 ||
                               results.deletedFromGmm.length > 0;

            if ( hasSuccesses ) {
                var successHeader = TTDom.createElement( 'div', {
                    className: 'tt-sync-section-header',
                    text: 'Completed'
                });
                successSection.appendChild( successHeader );

                if ( results.addedToServer.length > 0 ) {
                    var row = createResultRow( 'Added to server', results.addedToServer.length, 'success' );
                    successSection.appendChild( row );
                }
                if ( results.addedToGmm.length > 0 ) {
                    var row = createResultRow( 'Added to GMM', results.addedToGmm.length, 'success' );
                    successSection.appendChild( row );
                }
                if ( results.deletedFromServer.length > 0 ) {
                    var row = createResultRow( 'Removed from server', results.deletedFromServer.length, 'success' );
                    successSection.appendChild( row );
                }
                if ( results.deletedFromGmm.length > 0 ) {
                    var row = createResultRow( 'Removed from GMM', results.deletedFromGmm.length, 'success' );
                    successSection.appendChild( row );
                }

                dialog.appendChild( successSection );
            }

            // Issues section (things requiring user attention)
            if ( results.issues && results.issues.length > 0 ) {
                var issuesSection = TTDom.createElement( 'div', {
                    className: 'tt-sync-section'
                });

                var issuesHeader = TTDom.createElement( 'div', {
                    className: 'tt-sync-section-header',
                    text: 'Needs Attention (' + results.issues.length + ')'
                });
                issuesSection.appendChild( issuesHeader );

                var issuesList = TTDom.createElement( 'div', {
                    className: 'tt-sync-location-list'
                });

                results.issues.forEach( function( issue ) {
                    var issueItem = createIssueItem( issue );
                    issuesList.appendChild( issueItem );
                });

                issuesSection.appendChild( issuesList );
                dialog.appendChild( issuesSection );
            }

            // Errors section
            if ( results.errors && results.errors.length > 0 ) {
                var errorsSection = TTDom.createElement( 'div', {
                    className: 'tt-sync-section'
                });

                var errorsHeader = TTDom.createElement( 'div', {
                    className: 'tt-sync-section-header',
                    text: 'Errors (' + results.errors.length + ')'
                });
                errorsSection.appendChild( errorsHeader );

                results.errors.forEach( function( err ) {
                    var errorRow = TTDom.createElement( 'div', {
                        className: 'tt-sync-diff-row'
                    });
                    var label = TTDom.createElement( 'span', {
                        className: 'tt-sync-diff-label',
                        text: err.location ? err.location.title : 'Unknown'
                    });
                    var value = TTDom.createElement( 'span', {
                        className: 'tt-error',
                        text: err.error
                    });
                    errorRow.appendChild( label );
                    errorRow.appendChild( value );
                    errorsSection.appendChild( errorRow );
                });

                dialog.appendChild( errorsSection );
            }

            // No activity message
            if ( !hasSuccesses && ( !results.issues || results.issues.length === 0 ) &&
                 ( !results.errors || results.errors.length === 0 ) ) {
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
            console.log( '[TT GMM Sync] Results dialog displayed' );
        });
    }

    /**
     * Create a result row for the results dialog.
     * @param {string} label - Row label.
     * @param {number} count - Count value.
     * @param {string} type - Row type ('success' or 'error').
     * @returns {Element} The row element.
     */
    function createResultRow( label, count, type ) {
        var row = TTDom.createElement( 'div', {
            className: 'tt-sync-diff-row' + ( type === 'success' ? ' tt-sync-row-success' : '' )
        });
        var labelEl = TTDom.createElement( 'span', {
            className: 'tt-sync-diff-label',
            text: label
        });
        var valueEl = TTDom.createElement( 'span', {
            className: 'tt-sync-diff-value',
            text: String( count )
        });
        row.appendChild( labelEl );
        row.appendChild( valueEl );
        return row;
    }

    /**
     * Create an issue item for the results dialog.
     * @param {Object} issue - Issue object with type, location, message.
     * @returns {Element} The issue item element.
     */
    function createIssueItem( issue ) {
        var item = TTDom.createElement( 'div', {
            className: 'tt-sync-location-item'
        });

        var info = TTDom.createElement( 'div', {
            className: 'tt-sync-location-info'
        });

        var titleEl = TTDom.createElement( 'div', {
            className: 'tt-sync-location-title',
            text: issue.location ? issue.location.title : 'Unknown'
        });
        info.appendChild( titleEl );

        var issueTypeLabels = {};
        issueTypeLabels[ISSUE_TYPE.NO_SUBCATEGORY] = 'No category';
        issueTypeLabels[ISSUE_TYPE.UNKNOWN_SUBCATEGORY] = 'Unknown category';
        issueTypeLabels[ISSUE_TYPE.NO_RESULTS] = 'Not found in search';
        issueTypeLabels[ISSUE_TYPE.MULTIPLE_RESULTS] = 'Multiple matches';
        issueTypeLabels[ISSUE_TYPE.COORDINATE_MISMATCH] = 'Location mismatch';

        var typeLabel = issueTypeLabels[issue.type] || issue.type;

        var sourceEl = TTDom.createElement( 'div', {
            className: 'tt-sync-location-source',
            text: typeLabel
        });
        info.appendChild( sourceEl );

        item.appendChild( info );

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
