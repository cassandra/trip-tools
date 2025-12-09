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
        if ( handler ) {
            var versions = data[TT.SYNC.FIELD_VERSIONS] || {};
            var deleted = data[TT.SYNC.FIELD_DELETED] || [];
            promises.push( handler( versions, deleted ) );
        } else {
            console.log( 'TTSync: no handler registered for ' + objectType );
        }
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
 */
TTSync.registerHandler( TT.SYNC.OBJECT_TYPE_TRIP, function( versions, deleted ) {
    return TTTrips.validateWorkingSet( versions );
});
