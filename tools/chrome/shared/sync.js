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

        // Skip if no handler or if data has no versions field
        // (empty object means sync not applicable for this context)
        if ( !handler ) {
            console.log( 'TTSync: no handler registered for ' + objectType );
            continue;
        }

        if ( !data.hasOwnProperty( TT.SYNC.FIELD_VERSIONS ) ) {
            // Sync data not applicable (e.g., anonymous user)
            continue;
        }

        var versions = data[TT.SYNC.FIELD_VERSIONS];
        var deleted = data[TT.SYNC.FIELD_DELETED] || [];
        promises.push( handler( versions, deleted ) );
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
 * Validates working set against current trip versions.
 * Trips use presence-based deletion detection (not in versions = no access).
 * Marks trips as stale when version changes or new trips detected.
 * Actual detail fetching happens in handleGetTrips().
 */
TTSync.registerHandler( TT.SYNC.OBJECT_TYPE_TRIP, function( versions, deleted ) {
    return TTTrips.syncWorkingSet( versions );
});

/*
 * Location sync handler.
 * Updates location sync metadata for the active trip.
 * Locations are scoped to trips - only syncs if an active trip is set.
 * Marks locations as stale when version changes or new locations detected.
 */
TTSync.registerHandler( TT.SYNC.OBJECT_TYPE_LOCATION, function( versions, deleted ) {
    return TTStorage.get( TT.STORAGE.KEY_ACTIVE_TRIP_UUID, null )
        .then( function( activeTripUuid ) {
            if ( !activeTripUuid ) {
                // No active trip - can't store location metadata
                return;
            }
            return TTLocations.syncMetadata( activeTripUuid, versions, deleted );
        });
});
