/*
 * Trip Tools Chrome Extension - Sync Infrastructure
 * Handles client-server data synchronization.
 */

var TTSync = TTSync || {};

/*
 * Registry of sync handlers by object type.
 * Feature code registers handlers like:
 *   TTSync.registerHandler(TT.SYNC.OBJECT_TYPE_TRIP, handleTripSync);
 */
TTSync.handlers = {};

TTSync.registerHandler = function( objectType, handler ) {
    TTSync.handlers[objectType] = handler;
};

/*
 * Process sync envelope from API response.
 * Called AFTER main response processing is complete.
 *
 * Sync envelope structure varies by object type:
 * - Trips: { updates: {...}, deleted: [...] } - full trip data
 * - Locations: { versions: {...}, deleted: [...] } - version-only pattern
 *
 * @param {Object} sync - The sync envelope from response
 * @returns {Promise} Resolves when sync processing complete
 */
TTSync.processEnvelope = function( sync ) {
    if ( !sync || !sync[TT.SYNC.FIELD_AS_OF] ) {
        return Promise.resolve();
    }

    var promises = [];
    for ( var objectType in sync ) {
        if ( objectType === TT.SYNC.FIELD_AS_OF ) {
            continue;
        }

        var handler = TTSync.handlers[objectType];
        var data = sync[objectType];

        if ( !handler ) {
            console.log( 'TTSync: no handler registered for ' + objectType );
            continue;
        }

        // Check for presence of sync data (updates for trips, versions for locations)
        var hasUpdates = data.hasOwnProperty( TT.SYNC.FIELD_UPDATES );
        var hasVersions = data.hasOwnProperty( TT.SYNC.FIELD_VERSIONS );
        if ( !hasUpdates && !hasVersions ) {
            // Sync data not applicable (e.g., anonymous user)
            continue;
        }

        promises.push( handler( data ) );
    }

    return Promise.all( promises )
        .then( function() {
            // Store timestamp for next request
            return TTStorage.set(
                TT.STORAGE.KEY_SYNC_AS_OF,
                sync[TT.SYNC.FIELD_AS_OF]
            );
        });
};

/*
 * Clear sync state. Used when disconnecting or forcing full refresh.
 *
 * @returns {Promise} Resolves when sync state is cleared
 */
TTSync.clearState = function() {
    return TTStorage.remove( TT.STORAGE.KEY_SYNC_AS_OF );
};

// =============================================================================
// Sync Handlers
// =============================================================================

/*
 * Trip sync handler.
 * Receives full trip data from server and applies via unified update system.
 * The TripDataUpdates structure routes to all internal data structures.
 *
 * @param {Object} data - Sync data with { updates: {...}, deleted: [...] }
 */
TTSync.registerHandler( TT.SYNC.OBJECT_TYPE_TRIP, function( data ) {
    // Build TripDataUpdates structure from sync envelope
    var tripDataUpdates = {
        updates: data[TT.SYNC.FIELD_UPDATES] || {},
        deleted: data[TT.SYNC.FIELD_DELETED] || []
    };
    return TTTrips.applyUpdates( tripDataUpdates );
} );

/*
 * Location sync handler.
 * Updates location sync metadata for the current trip.
 * Locations are scoped to trips - only syncs if a current trip is set.
 * Marks locations as stale when version changes or new locations detected.
 *
 * @param {Object} data - Sync data with { versions: {...}, deleted: [...] }
 */
TTSync.registerHandler( TT.SYNC.OBJECT_TYPE_LOCATION, function( data ) {
    var versions = data[TT.SYNC.FIELD_VERSIONS] || {};
    var deleted = data[TT.SYNC.FIELD_DELETED] || [];

    return TTStorage.get( TT.STORAGE.KEY_CURRENT_TRIP_UUID, null )
        .then( function( currentTripUuid ) {
            if ( !currentTripUuid ) {
                // No current trip - can't store location metadata
                return;
            }
            return TTLocations.syncMetadata( currentTripUuid, versions, deleted );
        });
});
