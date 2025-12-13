/*
 * Trip Tools Chrome Extension - Locations Module
 * Manages location sync metadata storage per trip.
 * Depends on: constants.js, storage.js
 *
 * Location sync metadata is stored per trip with structure:
 * { "gmm_feature_id": { uuid: "...", version: 1, stale: false }, ... }
 *
 * This allows the extension to:
 * - Look up TT location UUID by GMM feature ID
 * - Track version changes for staleness detection
 * - Know when a location needs to be refreshed from server
 */

var TTLocations = TTLocations || {};

// =============================================================================
// Storage Key Helpers
// =============================================================================

/**
 * Get storage key for a trip's location sync metadata.
 * @param {string} tripUuid - The trip UUID.
 * @returns {string} Storage key.
 */
TTLocations._getStorageKey = function( tripUuid ) {
    return TT.STORAGE.KEY_LOCATION_SYNC_PREFIX + tripUuid;
};

// =============================================================================
// Sync Metadata Storage
// =============================================================================

/**
 * Get location sync metadata for a trip.
 * @param {string} tripUuid - The trip UUID.
 * @returns {Promise<Object>} Map of gmm_id -> { uuid, version, stale }.
 */
TTLocations.getSyncMetadata = function( tripUuid ) {
    return TTStorage.get( TTLocations._getStorageKey( tripUuid ), {} );
};

/**
 * Store location sync metadata for a trip.
 * @param {string} tripUuid - The trip UUID.
 * @param {Object} metadata - Map of gmm_id -> { uuid, version, stale }.
 * @returns {Promise<void>}
 */
TTLocations.setSyncMetadata = function( tripUuid, metadata ) {
    return TTStorage.set( TTLocations._getStorageKey( tripUuid ), metadata );
};

/**
 * Clear location sync metadata for a trip.
 * @param {string} tripUuid - The trip UUID.
 * @returns {Promise<void>}
 */
TTLocations.clearSyncMetadata = function( tripUuid ) {
    return TTStorage.remove( TTLocations._getStorageKey( tripUuid ) );
};

// =============================================================================
// Sync Operations
// =============================================================================

/**
 * Update metadata from a location returned by the server.
 * Called after create or update operations.
 * @param {string} tripUuid - The trip UUID.
 * @param {Object} location - Location object with uuid, gmm_id, version.
 * @returns {Promise<void>}
 */
TTLocations.updateMetadataFromLocation = function( tripUuid, location ) {
    if ( !location.gmm_id ) {
        // Location has no GMM ID - nothing to track
        return Promise.resolve();
    }

    return TTLocations.getSyncMetadata( tripUuid )
        .then( function( metadata ) {
            metadata[location.gmm_id] = {
                uuid: location.uuid,
                version: location.version,
                stale: false
            };
            return TTLocations.setSyncMetadata( tripUuid, metadata );
        });
};

/**
 * Remove metadata entry by GMM feature ID.
 * Called after local delete (when we delete a GMM feature).
 * @param {string} tripUuid - The trip UUID.
 * @param {string} gmmId - The GMM feature ID.
 * @returns {Promise<void>}
 */
TTLocations.removeMetadataByGmmId = function( tripUuid, gmmId ) {
    return TTLocations.getSyncMetadata( tripUuid )
        .then( function( metadata ) {
            if ( metadata.hasOwnProperty( gmmId ) ) {
                delete metadata[gmmId];
                return TTLocations.setSyncMetadata( tripUuid, metadata );
            }
        });
};

/**
 * Remove metadata entry by location UUID.
 * Called after server delete notification.
 * @param {string} tripUuid - The trip UUID.
 * @param {string} locationUuid - The location UUID.
 * @returns {Promise<void>}
 */
TTLocations.removeMetadataByUuid = function( tripUuid, locationUuid ) {
    return TTLocations.getSyncMetadata( tripUuid )
        .then( function( metadata ) {
            // Find and remove entry with this UUID
            var gmmIdToRemove = null;
            for ( var gmmId in metadata ) {
                if ( metadata[gmmId].uuid === locationUuid ) {
                    gmmIdToRemove = gmmId;
                    break;
                }
            }
            if ( gmmIdToRemove ) {
                delete metadata[gmmIdToRemove];
                return TTLocations.setSyncMetadata( tripUuid, metadata );
            }
        });
};

/**
 * Process sync envelope for locations.
 * Updates local metadata based on server version changes.
 *
 * For locations in sync envelope:
 * - Not in local metadata: Add as stale (new from server)
 * - In local with different version: Mark as stale (changed on server)
 * - In local with same version: Keep as-is
 * - In local but not in sync: Remove (deleted on server)
 *
 * @param {string} tripUuid - The trip UUID.
 * @param {Object} versions - Map of uuid -> { version, gmm_id } from sync envelope.
 * @param {Array} deleted - Array of deleted location UUIDs.
 * @returns {Promise<void>}
 */
TTLocations.syncMetadata = function( tripUuid, versions, deleted ) {
    if ( !tripUuid ) {
        return Promise.resolve();
    }

    return TTLocations.getSyncMetadata( tripUuid )
        .then( function( metadata ) {
            // Build reverse lookup: uuid -> gmm_id
            var uuidToGmmId = {};
            for ( var gmmId in metadata ) {
                uuidToGmmId[metadata[gmmId].uuid] = gmmId;
            }

            // Process deleted locations
            if ( deleted && deleted.length > 0 ) {
                deleted.forEach( function( locationUuid ) {
                    var gmmId = uuidToGmmId[locationUuid];
                    if ( gmmId && metadata.hasOwnProperty( gmmId ) ) {
                        delete metadata[gmmId];
                    }
                });
            }

            // Process version updates
            if ( versions ) {
                for ( var locationUuid in versions ) {
                    var serverData = versions[locationUuid];
                    var serverVersion = serverData.version;
                    var serverGmmId = serverData.gmm_id;

                    // Skip locations without gmm_id (can't track them by GMM feature)
                    if ( !serverGmmId ) {
                        continue;
                    }

                    var existingGmmId = uuidToGmmId[locationUuid];

                    if ( existingGmmId ) {
                        // Location exists locally
                        if ( existingGmmId !== serverGmmId ) {
                            // GMM ID changed (rare but possible) - update key
                            delete metadata[existingGmmId];
                            metadata[serverGmmId] = {
                                uuid: locationUuid,
                                version: serverVersion,
                                stale: true
                            };
                        } else if ( metadata[existingGmmId].version !== serverVersion ) {
                            // Version changed - mark stale
                            metadata[existingGmmId].version = serverVersion;
                            metadata[existingGmmId].stale = true;
                        }
                        // Same version - keep as-is
                    } else {
                        // New location from server - add as stale
                        metadata[serverGmmId] = {
                            uuid: locationUuid,
                            version: serverVersion,
                            stale: true
                        };
                    }
                }
            }

            return TTLocations.setSyncMetadata( tripUuid, metadata );
        });
};

// =============================================================================
// Lookup Helpers
// =============================================================================

/**
 * Look up TT location UUID by GMM feature ID.
 * @param {string} tripUuid - The trip UUID.
 * @param {string} gmmId - The GMM feature ID.
 * @returns {Promise<string|null>} Location UUID or null if not found.
 */
TTLocations.getUuidByGmmId = function( tripUuid, gmmId ) {
    return TTLocations.getSyncMetadata( tripUuid )
        .then( function( metadata ) {
            if ( metadata.hasOwnProperty( gmmId ) ) {
                return metadata[gmmId].uuid;
            }
            return null;
        });
};

/**
 * Check if a location is stale (needs refresh from server).
 * @param {string} tripUuid - The trip UUID.
 * @param {string} gmmId - The GMM feature ID.
 * @returns {Promise<boolean>} True if stale or not found.
 */
TTLocations.isStale = function( tripUuid, gmmId ) {
    return TTLocations.getSyncMetadata( tripUuid )
        .then( function( metadata ) {
            if ( metadata.hasOwnProperty( gmmId ) ) {
                return metadata[gmmId].stale === true;
            }
            // Not found = treat as stale (needs to be created)
            return true;
        });
};

/**
 * Mark a location as no longer stale.
 * Called after refreshing location data from server.
 * @param {string} tripUuid - The trip UUID.
 * @param {string} gmmId - The GMM feature ID.
 * @returns {Promise<void>}
 */
TTLocations.markFresh = function( tripUuid, gmmId ) {
    return TTLocations.getSyncMetadata( tripUuid )
        .then( function( metadata ) {
            if ( metadata.hasOwnProperty( gmmId ) ) {
                metadata[gmmId].stale = false;
                return TTLocations.setSyncMetadata( tripUuid, metadata );
            }
        });
};

// =============================================================================
// Cleanup
// =============================================================================

/**
 * Clear all location sync data.
 * Used when disconnecting from the server.
 * @returns {Promise<void>}
 */
TTLocations.clearAll = function() {
    // Get all storage keys and filter for location sync keys
    return new Promise( function( resolve ) {
        chrome.storage.local.get( null, function( items ) {
            var keysToRemove = Object.keys( items ).filter( function( key ) {
                return key.startsWith( TT.STORAGE.KEY_LOCATION_SYNC_PREFIX );
            });

            if ( keysToRemove.length === 0 ) {
                resolve();
                return;
            }

            chrome.storage.local.remove( keysToRemove, function() {
                resolve();
            });
        });
    });
};
