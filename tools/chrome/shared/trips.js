/*
 * Trip Tools Chrome Extension - Trips Module
 * Manages the working set of trips and active trip selection.
 * Depends on: constants.js, storage.js, api.js
 */

var TTTrips = TTTrips || {};

/**
 * Maximum number of trips in the working set.
 * @constant {number}
 */
TTTrips.MAX_WORKING_SET_SIZE = 4;

// =============================================================================
// Working Set Storage
// =============================================================================

/**
 * Get the working set of trips from storage.
 * @returns {Promise<Array>} Array of trip objects with uuid, title, version, lastAccessedAt.
 */
TTTrips.getWorkingSet = function() {
    return TTStorage.get( TT.STORAGE.KEY_WORKING_SET_TRIPS, [] );
};

/**
 * Store the working set of trips.
 * @param {Array} trips - Array of trip objects.
 * @returns {Promise<void>}
 */
TTTrips.setWorkingSet = function( trips ) {
    return TTStorage.set( TT.STORAGE.KEY_WORKING_SET_TRIPS, trips );
};

/**
 * Get the active trip UUID.
 * @returns {Promise<string|null>} The active trip UUID or null.
 */
TTTrips.getActiveTripUuid = function() {
    return TTStorage.get( TT.STORAGE.KEY_ACTIVE_TRIP_UUID, null );
};

/**
 * Set the active trip UUID.
 * @param {string|null} uuid - The trip UUID or null to clear.
 * @returns {Promise<void>}
 */
TTTrips.setActiveTripUuid = function( uuid ) {
    if ( uuid ) {
        return TTStorage.set( TT.STORAGE.KEY_ACTIVE_TRIP_UUID, uuid );
    }
    return TTStorage.remove( TT.STORAGE.KEY_ACTIVE_TRIP_UUID );
};

// =============================================================================
// Working Set Management
// =============================================================================

/**
 * Add a trip to the working set.
 * Updates lastAccessedAt and enforces MAX_WORKING_SET_SIZE by removing
 * the least recently accessed trip if needed (but never the active trip).
 * @param {Object} trip - Trip object with uuid, title, version.
 * @param {Object} [options] - Optional settings.
 * @param {string} [options.lastAccessedAt] - Custom lastAccessedAt timestamp (ISO string).
 *     If not provided, uses current time.
 * @returns {Promise<void>}
 */
TTTrips.addToWorkingSet = function( trip, options ) {
    options = options || {};
    var accessTime = options.lastAccessedAt || new Date().toISOString();

    return TTTrips.getActiveTripUuid()
        .then( function( activeUuid ) {
            return TTTrips.getWorkingSet()
                .then( function( workingSet ) {
                    // Remove if already present (will be re-added with new timestamp)
                    workingSet = workingSet.filter( function( t ) {
                        return t.uuid !== trip.uuid;
                    });

                    // Create entry - preserve all fields from trip, set lastAccessedAt
                    var entry = Object.assign( {}, trip, {
                        lastAccessedAt: accessTime
                    });

                    // Add new entry
                    workingSet.push( entry );

                    // Sort by lastAccessedAt descending (most recent first)
                    workingSet.sort( function( a, b ) {
                        return b.lastAccessedAt.localeCompare( a.lastAccessedAt );
                    });

                    // Enforce max size by removing from end (but never active trip)
                    while ( workingSet.length > TTTrips.MAX_WORKING_SET_SIZE ) {
                        // Find last trip that isn't active
                        for ( var j = workingSet.length - 1; j >= 0; j-- ) {
                            if ( workingSet[j].uuid !== activeUuid ) {
                                workingSet.splice( j, 1 );
                                break;
                            }
                        }
                        // Safety: if somehow all are active (shouldn't happen), just slice
                        if ( workingSet.length > TTTrips.MAX_WORKING_SET_SIZE ) {
                            workingSet = workingSet.slice( 0, TTTrips.MAX_WORKING_SET_SIZE );
                            break;
                        }
                    }

                    return TTTrips.setWorkingSet( workingSet );
                });
        });
};

/**
 * Set a trip as active.
 * Adds to working set and sets as active trip.
 * @param {Object} trip - Trip object with uuid, title, version.
 * @returns {Promise<void>}
 */
TTTrips.setActiveTrip = function( trip ) {
    return TTTrips.addToWorkingSet( trip )
        .then( function() {
            return TTTrips.setActiveTripUuid( trip.uuid );
        });
};

/**
 * Get the active trip object from working set.
 * @returns {Promise<Object|null>} The active trip or null.
 */
TTTrips.getActiveTrip = function() {
    var activeUuid;
    return TTTrips.getActiveTripUuid()
        .then( function( uuid ) {
            if ( !uuid ) {
                return null;
            }
            activeUuid = uuid;
            return TTTrips.getWorkingSet();
        })
        .then( function( workingSet ) {
            if ( !workingSet ) {
                return null;
            }
            return workingSet.find( function( t ) {
                return t.uuid === activeUuid;
            }) || null;
        });
};

// =============================================================================
// Server Interaction
// =============================================================================

/**
 * Fetch trips from the server.
 * @returns {Promise<Array>} Array of trip objects from server.
 */
TTTrips.fetchTripsFromServer = function() {
    return TTApi.get( TT.CONFIG.API_TRIPS_ENDPOINT )
        .then( function( response ) {
            return TTApi.processResponse( response );
        });
};

/**
 * Fetch a single trip by UUID.
 * @param {string} uuid - The trip UUID.
 * @returns {Promise<Object>} Trip object with uuid, title, version, created_datetime.
 */
TTTrips.fetchTripByUuid = function( uuid ) {
    return TTApi.get( TT.CONFIG.API_TRIPS_ENDPOINT + uuid + '/' )
        .then( function( response ) {
            return TTApi.processResponse( response );
        });
};

/**
 * Refresh stale trips in the working set.
 * Fetches details for any trip with stale=true flag.
 * Called by handleGetTrips() before returning data.
 * @returns {Promise<void>}
 */
TTTrips.refreshStaleTrips = function() {
    return TTTrips.getWorkingSet()
        .then( function( workingSet ) {
            // Find stale trips
            var staleTrips = workingSet.filter( function( trip ) {
                return trip.stale === true;
            });

            if ( staleTrips.length === 0 ) {
                return Promise.resolve();
            }

            // Fetch details for all stale trips in parallel
            var fetchPromises = staleTrips.map( function( trip ) {
                return TTTrips.fetchTripByUuid( trip.uuid )
                    .then( function( details ) {
                        return {
                            uuid: trip.uuid,
                            details: details,
                            originalTrip: trip
                        };
                    })
                    .catch( function( error ) {
                        console.log( '[TTTrips] Failed to refresh trip ' + trip.uuid + ':', error );
                        return {
                            uuid: trip.uuid,
                            details: null,
                            originalTrip: trip
                        };
                    });
            });

            return Promise.all( fetchPromises )
                .then( function( results ) {
                    return Promise.all([
                        TTTrips.getWorkingSet(),
                        TTTrips.getActiveTripUuid()
                    ]).then( function( data ) {
                        var currentSet = data[0];
                        var activeUuid = data[1];

                        // Update working set with fetched details
                        var updatedSet = currentSet.map( function( trip ) {
                            var result = results.find( function( r ) {
                                return r.uuid === trip.uuid;
                            });

                            if ( !result || !result.details ) {
                                // Not a stale trip or fetch failed - keep as-is
                                return trip;
                            }

                            // Merge server data with local state:
                            // - Start with all server fields
                            // - Preserve local lastAccessedAt
                            // - Remove stale flag (now fresh)
                            var merged = Object.assign( {}, result.details, {
                                lastAccessedAt: trip.lastAccessedAt
                            });
                            delete merged.stale;
                            return merged;
                        });

                        // Re-sort by lastAccessedAt descending
                        updatedSet.sort( function( a, b ) {
                            return b.lastAccessedAt.localeCompare( a.lastAccessedAt );
                        });

                        // Enforce max size, but never evict active trip
                        while ( updatedSet.length > TTTrips.MAX_WORKING_SET_SIZE ) {
                            var removed = false;
                            for ( var j = updatedSet.length - 1; j >= 0; j-- ) {
                                if ( updatedSet[j].uuid !== activeUuid ) {
                                    updatedSet.splice( j, 1 );
                                    removed = true;
                                    break;
                                }
                            }
                            if ( !removed ) {
                                updatedSet = updatedSet.slice( 0, TTTrips.MAX_WORKING_SET_SIZE );
                                break;
                            }
                        }

                        return TTTrips.setWorkingSet( updatedSet );
                    });
                });
        });
};

/**
 * Merge server trips into the working set.
 * For trips not already in the working set, adds them using their
 * created_datetime as lastAccessedAt. This allows LRU eviction to
 * naturally determine which trips belong in the working set.
 * @param {Array} serverTrips - Array of trips from server with created_datetime.
 * @returns {Promise<void>}
 */
TTTrips.mergeServerTrips = function( serverTrips ) {
    if ( !serverTrips || serverTrips.length === 0 ) {
        return Promise.resolve();
    }

    return TTTrips.getWorkingSet()
        .then( function( workingSet ) {
            // Build set of UUIDs already in working set
            var existingUuids = {};
            workingSet.forEach( function( trip ) {
                existingUuids[trip.uuid] = true;
            });

            // Find trips not in working set
            var newTrips = serverTrips.filter( function( trip ) {
                return !existingUuids[trip.uuid];
            });

            if ( newTrips.length === 0 ) {
                return Promise.resolve();
            }

            // Add each new trip using created_datetime as lastAccessedAt
            // Process sequentially to maintain correct ordering
            return newTrips.reduce( function( promise, trip ) {
                return promise.then( function() {
                    return TTTrips.addToWorkingSet( trip, {
                        lastAccessedAt: trip.created_datetime
                    });
                });
            }, Promise.resolve() );
        });
};

/**
 * Seed the working set from server trips.
 * Only seeds if working set is empty.
 * Takes the most recent trips (by created_datetime, already sorted by server).
 * @param {Array} serverTrips - Array of trips from server.
 * @returns {Promise<void>}
 */
TTTrips.seedWorkingSet = function( serverTrips ) {
    return TTTrips.getWorkingSet()
        .then( function( workingSet ) {
            // Only seed if empty
            if ( workingSet.length > 0 ) {
                return;
            }

            if ( !serverTrips || serverTrips.length === 0 ) {
                return;
            }

            // Take up to MAX_WORKING_SET_SIZE trips
            var toSeed = serverTrips.slice( 0, TTTrips.MAX_WORKING_SET_SIZE );
            var now = new Date().toISOString();

            var newWorkingSet = toSeed.map( function( trip ) {
                // Preserve all fields from server, set lastAccessedAt
                return Object.assign( {}, trip, {
                    lastAccessedAt: now
                });
            });

            return TTTrips.setWorkingSet( newWorkingSet )
                .then( function() {
                    // Set first trip as active if no active trip
                    return TTTrips.getActiveTripUuid();
                })
                .then( function( activeUuid ) {
                    if ( !activeUuid && newWorkingSet.length > 0 ) {
                        return TTTrips.setActiveTripUuid( newWorkingSet[0].uuid );
                    }
                });
        });
};

/**
 * Sync working set with server trip versions.
 * Called by sync handler. Does NOT make API calls - only updates local state.
 *
 * For each trip in sync envelope:
 * - Not in working set: Add as stale stub (needs detail fetch)
 * - In working set with different version: Mark as stale (needs refresh)
 * - In working set with same version: Keep as-is
 * - In deleted array: Remove from working set
 *
 * @param {Object} versions - Map of uuid -> {version, gmm_map_id, title, created} from sync envelope.
 * @param {Array} deleted - Array of deleted trip UUIDs.
 * @returns {Promise<void>}
 */
TTTrips.syncWorkingSet = function( versions, deleted ) {
    if ( !versions ) {
        versions = {};
    }

    var activeUuidBeforeSync;

    return TTTrips.getActiveTripUuid()
        .then( function( activeUuid ) {
            activeUuidBeforeSync = activeUuid;
            return TTTrips.getWorkingSet();
        })
        .then( function( workingSet ) {
            // Build map of existing trips by UUID
            var existingByUuid = {};
            workingSet.forEach( function( trip ) {
                existingByUuid[trip.uuid] = trip;
            });

            // Process existing trips: update if changed, keep otherwise
            // Note: With delta sync, versions only contains *changed* trips.
            // Trips not in versions are unchanged (not deleted).
            // Deletions are handled via the deleted array below.
            var updatedSet = [];
            workingSet.forEach( function( trip ) {
                if ( !versions.hasOwnProperty( trip.uuid ) ) {
                    // Trip not in delta - unchanged, keep as-is
                    updatedSet.push( trip );
                    return;
                }

                var serverData = versions[trip.uuid];
                var serverVersion = serverData.version;
                if ( trip.version !== serverVersion ) {
                    // Version changed - update metadata and mark as stale
                    var updated = Object.assign( {}, trip, {
                        version: serverVersion,
                        title: serverData.title,
                        gmm_map_id: serverData.gmm_map_id,
                        stale: true
                    });
                    updatedSet.push( updated );
                } else {
                    // Version matches - keep as-is (preserve stale flag if present)
                    updatedSet.push( trip );
                }
            });

            // Add stale stubs for new trips not in working set
            var serverUuids = Object.keys( versions );
            serverUuids.forEach( function( uuid ) {
                if ( !existingByUuid[uuid] ) {
                    var serverData = versions[uuid];
                    // New trip - add as stale stub with metadata from sync
                    updatedSet.push({
                        uuid: uuid,
                        title: serverData.title,
                        gmm_map_id: serverData.gmm_map_id,
                        version: serverData.version,
                        lastAccessedAt: serverData.created,
                        stale: true
                    });
                }
            });

            // Remove explicitly deleted trips
            deleted = deleted || [];
            deleted.forEach( function( uuid ) {
                updatedSet = updatedSet.filter( function( trip ) {
                    return trip.uuid !== uuid;
                });
            });

            // Sort by lastAccessedAt descending (most recent first)
            updatedSet.sort( function( a, b ) {
                return b.lastAccessedAt.localeCompare( a.lastAccessedAt );
            });

            // Enforce max size, but never evict active trip
            while ( updatedSet.length > TTTrips.MAX_WORKING_SET_SIZE ) {
                // Find last trip that isn't active
                var removed = false;
                for ( var j = updatedSet.length - 1; j >= 0; j-- ) {
                    if ( updatedSet[j].uuid !== activeUuidBeforeSync ) {
                        updatedSet.splice( j, 1 );
                        removed = true;
                        break;
                    }
                }
                // Safety: if all trips are active (shouldn't happen), just slice
                if ( !removed ) {
                    updatedSet = updatedSet.slice( 0, TTTrips.MAX_WORKING_SET_SIZE );
                    break;
                }
            }

            return TTTrips.setWorkingSet( updatedSet )
                .then( function() {
                    return updatedSet;
                });
        })
        .then( function( updatedSet ) {
            // Handle active trip if it was removed (deleted on server)
            if ( activeUuidBeforeSync ) {
                var stillExists = updatedSet.some( function( trip ) {
                    return trip.uuid === activeUuidBeforeSync;
                });

                if ( !stillExists ) {
                    // Active trip was deleted - set to first non-stale, or first available
                    var firstNonStale = updatedSet.find( function( trip ) {
                        return !trip.stale;
                    });
                    if ( firstNonStale ) {
                        return TTTrips.setActiveTripUuid( firstNonStale.uuid );
                    }
                    if ( updatedSet.length > 0 ) {
                        return TTTrips.setActiveTripUuid( updatedSet[0].uuid );
                    }
                    return TTTrips.setActiveTripUuid( null );
                }
            }
        });
};

// =============================================================================
// Trip Updates
// =============================================================================

/**
 * Update a trip in the working set with new data.
 * Used when trip is updated (e.g., gmm_map_id is set).
 * @param {string} uuid - The trip UUID.
 * @param {Object} updates - Object with fields to update (e.g., { gmm_map_id: '...' }).
 * @returns {Promise<void>}
 */
TTTrips.updateTripInWorkingSet = function( uuid, updates ) {
    return TTTrips.getWorkingSet()
        .then( function( workingSet ) {
            var updatedSet = workingSet.map( function( trip ) {
                if ( trip.uuid === uuid ) {
                    return Object.assign( {}, trip, updates );
                }
                return trip;
            });
            return TTTrips.setWorkingSet( updatedSet );
        });
};

// =============================================================================
// GMM Map Index (3-Layer Cache)
// =============================================================================
//
// Maps gmm_map_id -> trip_uuid for routing GMM operations to the correct trip.
//
// Uses lazy initialization: the index is built on first lookup rather than at
// service worker startup. This avoids potential timing issues with network
// calls during SW initialization and ensures we only fetch when actually needed.
//
// 3-Layer cache hierarchy:
//   L1: Memory (_gmmMapIndex) - Fast, lost on SW restart
//   L2: Storage (tt_gmmMapIndex) - Persists across restarts, 1-hour TTL
//   L3: API (TripCollectionView) - Source of truth, fetched when L2 stale/missing

// L1: In-memory cache (fast, lost on SW restart)
var _gmmMapIndex = null;

/**
 * Get GMM map index, using 3-layer cache: Memory → Storage → API.
 * Populates higher layers on cache miss.
 * @returns {Promise<Object>} The index mapping gmm_map_id -> trip_uuid.
 */
TTTrips.getGmmMapIndex = function() {
    // L1: Check memory
    if ( _gmmMapIndex ) {
        return Promise.resolve( _gmmMapIndex );
    }

    // L2: Check storage
    return TTStorage.get( TT.STORAGE.KEY_GMM_MAP_INDEX, null )
        .then( function( data ) {
            if ( data && data.index && !TTTrips._isGmmMapIndexStale( data ) ) {
                // Populate L1 from L2
                _gmmMapIndex = data.index;
                return _gmmMapIndex;
            }

            // L3: Fetch from API
            return TTTrips._fetchAndCacheGmmMapIndex();
        });
};

/**
 * Check if stored index is stale (older than TTL).
 * @param {Object} data - Stored index data with fetchedAt.
 * @returns {boolean} True if stale.
 */
TTTrips._isGmmMapIndexStale = function( data ) {
    if ( !data || !data.fetchedAt ) {
        return true;
    }
    var fetchedAt = new Date( data.fetchedAt ).getTime();
    var age = Date.now() - fetchedAt;
    return age > TT.CONFIG.GMM_MAP_INDEX_TTL_MS;
};

/**
 * Fetch trips from API and build/cache the GMM map index.
 * Populates both L1 (memory) and L2 (storage).
 * @returns {Promise<Object>} The index.
 */
TTTrips._fetchAndCacheGmmMapIndex = function() {
    return TTTrips.fetchTripsFromServer()
        .then( function( trips ) {
            var index = {};
            trips.forEach( function( trip ) {
                if ( trip.gmm_map_id ) {
                    index[trip.gmm_map_id] = trip.uuid;
                }
            });

            // Populate L1
            _gmmMapIndex = index;

            // Populate L2
            return TTStorage.set( TT.STORAGE.KEY_GMM_MAP_INDEX, {
                fetchedAt: new Date().toISOString(),
                index: index
            }).then( function() {
                return index;
            });
        });
};

/**
 * Look up trip UUID by GMM map ID.
 * Uses 3-layer cache for fast lookup.
 * @param {string} gmmMapId - The Google My Maps map ID.
 * @returns {Promise<string|null>} Trip UUID or null if not found.
 */
TTTrips.getTripUuidByGmmMapId = function( gmmMapId ) {
    return TTTrips.getGmmMapIndex()
        .then( function( index ) {
            return index[gmmMapId] || null;
        });
};

/**
 * Clear the GMM map index from all cache layers.
 * @returns {Promise<void>}
 */
TTTrips.clearGmmMapIndex = function() {
    _gmmMapIndex = null;
    return TTStorage.remove( TT.STORAGE.KEY_GMM_MAP_INDEX );
};

/**
 * Apply trip deltas to GMM map index.
 * Called by sync handler after working set sync.
 * Updates L1 (memory) and L2 (storage) with delta information.
 *
 * Optimized for the common case where gmm_map_id hasn't changed:
 * - Check if index[gmm_map_id] === uuid before doing any work
 * - Only scan for old entries when there's an actual change
 * - Only persist to storage if something changed
 *
 * @param {Object} versions - Map of uuid -> {version, gmm_map_id, title, created}
 * @param {Array} deleted - Array of deleted trip UUIDs
 * @returns {Promise<void>}
 */
TTTrips.applyGmmMapIndexDeltas = function( versions, deleted ) {
    // Get current index (will lazy-build if needed)
    return TTTrips.getGmmMapIndex()
        .then( function( index ) {
            var updated = false;

            // Handle deletions - must scan by value since index keyed by gmm_map_id
            if ( deleted && deleted.length > 0 ) {
                var deletedSet = {};
                deleted.forEach( function( uuid ) { deletedSet[uuid] = true; } );

                for ( var gmmMapId in index ) {
                    if ( deletedSet[index[gmmMapId]] ) {
                        delete index[gmmMapId];
                        updated = true;
                    }
                }
            }

            // Apply version updates
            for ( var uuid in versions ) {
                var tripData = versions[uuid];
                var gmmMapId = tripData.gmm_map_id;

                // Fast path: if mapping already correct, skip this trip entirely
                if ( gmmMapId && index[gmmMapId] === uuid ) {
                    continue;
                }

                // Slow path: mapping changed or was removed
                // Find and remove any existing entry for this trip UUID
                for ( var existingMapId in index ) {
                    if ( index[existingMapId] === uuid ) {
                        delete index[existingMapId];
                        updated = true;
                        break;
                    }
                }

                // Add new entry if trip has gmm_map_id
                if ( gmmMapId ) {
                    index[gmmMapId] = uuid;
                    updated = true;
                }
            }

            // Persist to L2 only if something changed
            if ( updated ) {
                return TTStorage.set( TT.STORAGE.KEY_GMM_MAP_INDEX, {
                    fetchedAt: new Date().toISOString(),
                    index: index
                } );
            }
        } );
};

// =============================================================================
// Cleanup
// =============================================================================

/**
 * Clear all trip state.
 * Used when disconnecting from the server.
 * @returns {Promise<void>}
 */
TTTrips.clearAll = function() {
    return Promise.all([
        TTTrips.setWorkingSet( [] ),
        TTTrips.setActiveTripUuid( null )
    ]);
};
