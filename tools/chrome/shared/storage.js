/*
 * Trip Tools Chrome Extension - Storage Utilities
 * Promise-based wrapper around chrome.storage.local.
 *
 * Storage Access Patterns:
 *
 * For shared state (trips, auth, sync metadata, etc.):
 *   - Access through service worker via message passing
 *   - Centralizes validation, coordination, and business logic
 *   - Easier to test and maintain
 *
 * For module-local state (e.g., UI preferences, dismissed dialogs):
 *   - Direct chrome.storage access from the owning module is acceptable
 *   - Only when the data is used exclusively by that one module
 *   - No coordination with other modules needed
 */

var TTStorage = TTStorage || {};

TTStorage.get = function( key, defaultValue ) {
    return new Promise( function( resolve, reject ) {
        var query = {};
        query[key] = defaultValue;
        chrome.storage.local.get( query, function( result ) {
            if ( chrome.runtime.lastError ) {
                reject( chrome.runtime.lastError );
                return;
            }
            resolve( result[key] );
        });
    });
};

TTStorage.set = function( key, value ) {
    return new Promise( function( resolve, reject ) {
        var data = {};
        data[key] = value;
        chrome.storage.local.set( data, function() {
            if ( chrome.runtime.lastError ) {
                reject( chrome.runtime.lastError );
                return;
            }
            resolve();
        });
    });
};

TTStorage.getMultiple = function( keysWithDefaults ) {
    return new Promise( function( resolve, reject ) {
        chrome.storage.local.get( keysWithDefaults, function( result ) {
            if ( chrome.runtime.lastError ) {
                reject( chrome.runtime.lastError );
                return;
            }
            resolve( result );
        });
    });
};

TTStorage.remove = function( key ) {
    return new Promise( function( resolve, reject ) {
        chrome.storage.local.remove( key, function() {
            if ( chrome.runtime.lastError ) {
                reject( chrome.runtime.lastError );
                return;
            }
            resolve();
        });
    });
};

TTStorage.addChangeListener = function( callback ) {
    chrome.storage.onChanged.addListener( function( changes, namespace ) {
        if ( namespace === 'local' ) {
            callback( changes );
        }
    });
};
