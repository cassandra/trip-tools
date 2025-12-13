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
// Pinned Trip Management
// =============================================================================

/**
 * Get the pinned trip UUID.
 * @returns {Promise<string|null>} The pinned trip UUID or null if in auto mode.
 */
TTTrips.getPinnedTripUuid = function() {
    return TTStorage.get( TT.STORAGE.KEY_PINNED_TRIP_UUID, null );
};

/**
 * Set the pinned trip UUID.
 * @param {string|null} uuid - The trip UUID to pin, or null to unpin (return to auto mode).
 * @returns {Promise<void>}
 */
TTTrips.setPinnedTripUuid = function( uuid ) {
    if ( uuid ) {
        return TTStorage.set( TT.STORAGE.KEY_PINNED_TRIP_UUID, uuid );
    }
    return TTStorage.remove( TT.STORAGE.KEY_PINNED_TRIP_UUID );
};

/**
 * Get the timestamp when the current trip was pinned.
 * @returns {Promise<string|null>} ISO timestamp or null if not pinned.
 */
TTTrips.getPinTimestamp = function() {
    return TTStorage.get( TT.STORAGE.KEY_PIN_TIMESTAMP, null );
};

/**
 * Set the pin timestamp.
 * @param {string|null} timestamp - ISO timestamp or null to clear.
 * @returns {Promise<void>}
 */
TTTrips.setPinTimestamp = function( timestamp ) {
    if ( timestamp ) {
        return TTStorage.set( TT.STORAGE.KEY_PIN_TIMESTAMP, timestamp );
    }
    return TTStorage.remove( TT.STORAGE.KEY_PIN_TIMESTAMP );
};

/**
 * Check if the pinned trip is stale (pinned more than threshold days ago).
 * @returns {Promise<boolean>} True if pin is stale, false if not pinned or not stale.
 */
TTTrips.isPinStale = function() {
    return TTTrips.getPinTimestamp()
        .then( function( timestamp ) {
            if ( !timestamp ) {
                return false;
            }
            var pinnedAt = new Date( timestamp ).getTime();
            var age = Date.now() - pinnedAt;
            var thresholdMs = TT.CONFIG.PIN_STALE_THRESHOLD_DAYS * 24 * 60 * 60 * 1000;
            return age > thresholdMs;
        });
};

/**
 * Reset the pin timestamp to now (used when user dismisses stale warning).
 * @returns {Promise<void>}
 */
TTTrips.resetPinTimestamp = function() {
    return TTTrips.setPinTimestamp( new Date().toISOString() );
};

/**
 * Get the current trip UUID.
 * Returns pinned trip if one is set, otherwise returns most recent in working set.
 * @returns {Promise<string|null>} The current trip UUID or null.
 */
TTTrips.getCurrentTripUuid = function() {
    return TTTrips.getPinnedTripUuid()
        .then( function( pinnedUuid ) {
            if ( pinnedUuid ) {
                return pinnedUuid;
            }
            // Auto mode: return most recent from working set
            return TTTrips.getWorkingSet()
                .then( function( workingSet ) {
                    if ( workingSet.length > 0 ) {
                        return workingSet[0].uuid;
                    }
                    return null;
                });
        });
};

/**
 * Get the current trip object.
 * Returns pinned trip if one is set, otherwise returns most recent in working set.
 * @returns {Promise<Object|null>} The current trip or null.
 */
TTTrips.getCurrentTrip = function() {
    var currentUuid;
    return TTTrips.getCurrentTripUuid()
        .then( function( uuid ) {
            if ( !uuid ) {
                return null;
            }
            currentUuid = uuid;
            return TTTrips.getWorkingSet();
        })
        .then( function( workingSet ) {
            if ( !workingSet ) {
                return null;
            }
            return workingSet.find( function( t ) {
                return t.uuid === currentUuid;
            }) || null;
        });
};

// =============================================================================
// Working Set Management
// =============================================================================

/**
 * Add a trip to the working set.
 * Updates lastAccessedAt and enforces MAX_WORKING_SET_SIZE by removing
 * the least recently accessed trip if needed (but never the active or pinned trip).
 * @param {Object} trip - Trip object with uuid, title, version.
 * @param {Object} [options] - Optional settings.
 * @param {string} [options.lastAccessedAt] - Custom lastAccessedAt timestamp (ISO string).
 *     If not provided, uses current time.
 * @returns {Promise<void>}
 */
TTTrips.addToWorkingSet = function( trip, options ) {
    options = options || {};
    var accessTime = options.lastAccessedAt || new Date().toISOString();

    return Promise.all([
        TTTrips.getActiveTripUuid(),
        TTTrips.getPinnedTripUuid()
    ]).then( function( results ) {
        var activeUuid = results[0];
        var pinnedUuid = results[1];

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

                // Enforce max size by removing from end (but never active or pinned trip)
                while ( workingSet.length > TTTrips.MAX_WORKING_SET_SIZE ) {
                    // Find last trip that isn't active or pinned
                    var removed = false;
                    for ( var j = workingSet.length - 1; j >= 0; j-- ) {
                        var uuid = workingSet[j].uuid;
                        if ( uuid !== activeUuid && uuid !== pinnedUuid ) {
                            workingSet.splice( j, 1 );
                            removed = true;
                            break;
                        }
                    }
                    // Safety: if somehow all are protected (shouldn't happen), just slice
                    if ( !removed ) {
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

// =============================================================================
// Trip Data Updates (Unified Update Structure)
// =============================================================================
//
// TripDataUpdates is the unified structure for trip updates from any source
// (server sync, internal operations like create/link/unlink).
//
// Structure:
//   {
//       updates: {
//           'trip-uuid-1': { uuid: '...', title: '...', gmm_map_id: '...', ... },
//           'trip-uuid-2': { uuid: '...', title: '...', gmm_map_id: null, ... }
//       },
//       deleted: ['trip-uuid-3', 'trip-uuid-4']
//   }
//
// Field semantics within each trip object:
//   - field: value → set to this value
//   - field: null → explicitly cleared/deleted
//   - field absent → no information, preserve existing value

/**
 * @typedef {Object} TripDataUpdates
 * @property {Object<string, Object>} updates - Map of trip UUID to trip data.
 * @property {Array<string>} deleted - Array of deleted trip UUIDs.
 */

/**
 * Apply trip updates to all internal data structures.
 * Central dispatcher for both server sync and internal operations.
 * Each internal structure handler understands the TripDataUpdates format
 * and extracts the fields it cares about.
 *
 * @param {TripDataUpdates} tripDataUpdates - The updates to apply.
 * @returns {Promise<void>}
 */
TTTrips.applyUpdates = function( tripDataUpdates ) {
    return Promise.all([
        TTTrips._applyUpdatesToWorkingSet( tripDataUpdates ),
        TTTrips._applyUpdatesToGmmMapIndex( tripDataUpdates )
    ]);
};

/**
 * Convenience function for updating a single trip.
 * Wraps the trip data in a TripDataUpdates structure and applies it.
 *
 * @param {Object} tripData - Trip object with uuid and fields to update.
 * @returns {Promise<void>}
 */
TTTrips.applyTripUpdate = function( tripData ) {
    if ( !tripData || !tripData.uuid ) {
        return Promise.reject( new Error( 'tripData must include uuid' ) );
    }

    var tripDataUpdates = {
        updates: {},
        deleted: []
    };
    tripDataUpdates.updates[tripData.uuid] = tripData;

    return TTTrips.applyUpdates( tripDataUpdates );
};

/**
 * Apply trip updates to the working set.
 * Internal handler for applyUpdates().
 *
 * For trips in updates:
 *   - If in working set: merge fields (respecting null = clear, absent = preserve)
 *   - If not in working set: add with created_datetime as lastAccessedAt
 *
 * For trips in deleted:
 *   - Remove from working set
 *   - If active trip was deleted, select a new active trip
 *
 * @param {TripDataUpdates} tripDataUpdates - The updates to apply.
 * @returns {Promise<void>}
 * @private
 */
TTTrips._applyUpdatesToWorkingSet = function( tripDataUpdates ) {
    var updates = tripDataUpdates.updates || {};
    var deleted = tripDataUpdates.deleted || [];
    var activeUuidBeforeSync;
    var pinnedUuidBeforeSync;

    return Promise.all([
        TTTrips.getActiveTripUuid(),
        TTTrips.getPinnedTripUuid()
    ]).then( function( results ) {
        activeUuidBeforeSync = results[0];
        pinnedUuidBeforeSync = results[1];
        return TTTrips.getWorkingSet();
    })
        .then( function( workingSet ) {
            // Build map of existing trips by UUID
            var existingByUuid = {};
            workingSet.forEach( function( trip ) {
                existingByUuid[trip.uuid] = trip;
            });

            // Process existing trips: merge updates if present
            var updatedSet = [];
            workingSet.forEach( function( trip ) {
                if ( updates.hasOwnProperty( trip.uuid ) ) {
                    // Merge server data with existing trip
                    // Field semantics: present value = set, null = clear, absent = preserve
                    var serverData = updates[trip.uuid];
                    var merged = Object.assign( {}, trip );

                    for ( var key in serverData ) {
                        if ( serverData.hasOwnProperty( key ) ) {
                            // Set the value (including null for explicit clear)
                            merged[key] = serverData[key];
                        }
                    }

                    updatedSet.push( merged );
                } else {
                    // Trip not in updates - keep as-is
                    updatedSet.push( trip );
                }
            });

            // Add new trips not in working set
            for ( var uuid in updates ) {
                if ( !existingByUuid[uuid] ) {
                    var tripData = updates[uuid];
                    // New trip - add with created_datetime as lastAccessedAt
                    var newTrip = Object.assign( {}, tripData, {
                        lastAccessedAt: tripData.created_datetime || new Date().toISOString()
                    });
                    updatedSet.push( newTrip );
                }
            }

            // Remove deleted trips
            deleted.forEach( function( uuid ) {
                updatedSet = updatedSet.filter( function( trip ) {
                    return trip.uuid !== uuid;
                });
            });

            // Sort by lastAccessedAt descending (most recent first)
            updatedSet.sort( function( a, b ) {
                return ( b.lastAccessedAt || '' ).localeCompare( a.lastAccessedAt || '' );
            });

            // Enforce max size, but never evict active or pinned trip
            while ( updatedSet.length > TTTrips.MAX_WORKING_SET_SIZE ) {
                var removed = false;
                for ( var j = updatedSet.length - 1; j >= 0; j-- ) {
                    var uuid = updatedSet[j].uuid;
                    if ( uuid !== activeUuidBeforeSync && uuid !== pinnedUuidBeforeSync ) {
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

            return TTTrips.setWorkingSet( updatedSet )
                .then( function() {
                    return updatedSet;
                });
        })
        .then( function( updatedSet ) {
            // Handle active trip if it was deleted
            if ( activeUuidBeforeSync ) {
                var stillExists = updatedSet.some( function( trip ) {
                    return trip.uuid === activeUuidBeforeSync;
                });

                if ( !stillExists ) {
                    // Active trip was deleted - select first available
                    if ( updatedSet.length > 0 ) {
                        return TTTrips.setActiveTripUuid( updatedSet[0].uuid );
                    }
                    return TTTrips.setActiveTripUuid( null );
                }
            }
        });
};

/**
 * Apply trip updates to the GMM map index.
 * Internal handler for applyUpdates().
 *
 * Extracts gmm_map_id from each trip and updates the index.
 * Field semantics:
 *   - gmm_map_id: value → set mapping
 *   - gmm_map_id: null → remove mapping
 *   - gmm_map_id absent → preserve existing mapping
 *
 * @param {TripDataUpdates} tripDataUpdates - The updates to apply.
 * @returns {Promise<void>}
 * @private
 */
TTTrips._applyUpdatesToGmmMapIndex = function( tripDataUpdates ) {
    var updates = tripDataUpdates.updates || {};
    var deleted = tripDataUpdates.deleted || [];

    return TTTrips.getGmmMapIndex()
        .then( function( index ) {
            var changed = false;

            // Handle deletions - scan by value since index keyed by gmm_map_id
            if ( deleted.length > 0 ) {
                var deletedSet = {};
                deleted.forEach( function( uuid ) { deletedSet[uuid] = true; });

                for ( var gmmMapId in index ) {
                    if ( deletedSet[index[gmmMapId]] ) {
                        delete index[gmmMapId];
                        changed = true;
                    }
                }
            }

            // Apply updates
            for ( var uuid in updates ) {
                var tripData = updates[uuid];

                // Only process if gmm_map_id is present in the update
                if ( !tripData.hasOwnProperty( 'gmm_map_id' ) ) {
                    continue;
                }

                var newGmmMapId = tripData.gmm_map_id;

                // Fast path: if mapping already correct, skip
                if ( newGmmMapId && index[newGmmMapId] === uuid ) {
                    continue;
                }

                // Remove any existing mapping for this trip UUID
                for ( var existingMapId in index ) {
                    if ( index[existingMapId] === uuid ) {
                        delete index[existingMapId];
                        changed = true;
                        break;
                    }
                }

                // Add new mapping if gmm_map_id has a value (not null)
                if ( newGmmMapId ) {
                    index[newGmmMapId] = uuid;
                    changed = true;
                }
            }

            // Persist to storage only if something changed
            if ( changed ) {
                return TTStorage.set( TT.STORAGE.KEY_GMM_MAP_INDEX, {
                    fetchedAt: new Date().toISOString(),
                    index: index
                });
            }
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
