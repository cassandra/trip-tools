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
 * the least recently accessed trip if needed.
 * @param {Object} trip - Trip object with uuid, title, version.
 * @param {Object} [options] - Optional settings.
 * @param {string} [options.lastAccessedAt] - Custom lastAccessedAt timestamp (ISO string).
 *     If not provided, uses current time.
 * @returns {Promise<void>}
 */
TTTrips.addToWorkingSet = function( trip, options ) {
    options = options || {};
    var accessTime = options.lastAccessedAt || new Date().toISOString();

    return TTTrips.getWorkingSet()
        .then( function( workingSet ) {
            // Remove if already present (will be re-added with new timestamp)
            workingSet = workingSet.filter( function( t ) {
                return t.uuid !== trip.uuid;
            });

            // Create entry
            var entry = {
                uuid: trip.uuid,
                title: trip.title,
                version: trip.version,
                lastAccessedAt: accessTime
            };

            // Find insertion point to maintain descending order by lastAccessedAt
            var insertIndex = 0;
            for ( var i = 0; i < workingSet.length; i++ ) {
                if ( workingSet[i].lastAccessedAt > accessTime ) {
                    insertIndex = i + 1;
                } else {
                    break;
                }
            }

            // Insert at correct position
            workingSet.splice( insertIndex, 0, entry );

            // Enforce max size by removing least recently accessed (end of list)
            if ( workingSet.length > TTTrips.MAX_WORKING_SET_SIZE ) {
                workingSet = workingSet.slice( 0, TTTrips.MAX_WORKING_SET_SIZE );
            }

            return TTTrips.setWorkingSet( workingSet );
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
                return {
                    uuid: trip.uuid,
                    title: trip.title,
                    version: trip.version,
                    lastAccessedAt: now
                };
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
 * Validate the working set against trip versions from sync.
 * Removes trips that are no longer accessible (not in versions map).
 * Updates version numbers for trips that have changed.
 * @param {Object} versions - Map of uuid -> version from sync envelope.
 * @returns {Promise<void>}
 */
TTTrips.validateWorkingSet = function( versions ) {
    var activeUuidBeforeValidation;

    return TTTrips.getActiveTripUuid()
        .then( function( activeUuid ) {
            activeUuidBeforeValidation = activeUuid;
            return TTTrips.getWorkingSet();
        })
        .then( function( workingSet ) {
            // Filter to only trips that are still accessible
            var validatedSet = workingSet.filter( function( trip ) {
                return versions.hasOwnProperty( trip.uuid );
            });

            // Update versions for remaining trips
            validatedSet = validatedSet.map( function( trip ) {
                return {
                    uuid: trip.uuid,
                    title: trip.title,
                    version: versions[trip.uuid],
                    lastAccessedAt: trip.lastAccessedAt
                };
            });

            return TTTrips.setWorkingSet( validatedSet )
                .then( function() {
                    return validatedSet;
                });
        })
        .then( function( validatedSet ) {
            // Clear active trip if it was removed from working set
            if ( activeUuidBeforeValidation ) {
                var stillExists = validatedSet.some( function( trip ) {
                    return trip.uuid === activeUuidBeforeValidation;
                });

                if ( !stillExists ) {
                    // Active trip was removed - clear or set to first available
                    if ( validatedSet.length > 0 ) {
                        return TTTrips.setActiveTripUuid( validatedSet[0].uuid );
                    }
                    return TTTrips.setActiveTripUuid( null );
                }
            }
        });
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
