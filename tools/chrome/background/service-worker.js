/*
 * Trip Tools Chrome Extension - Background Service Worker
 * Handles extension lifecycle and message routing.
 */

importScripts( '../shared/constants.js' );
importScripts( '../shared/storage.js' );
importScripts( '../shared/messaging.js' );

var extensionStartTime = Date.now();

chrome.runtime.onInstalled.addListener( function( details ) {
    console.log( '[TT Background] Extension installed:', details.reason );
    initializeExtensionState();
});

function initializeExtensionState() {
    var initialState = {
        installedAt: Date.now(),
        version: TT.CONFIG.EXTENSION_VERSION
    };
    TTStorage.set( TT.STORAGE.KEY_EXTENSION_STATE, initialState );
    TTStorage.set( TT.STORAGE.KEY_DEBUG_LOG, [] );
    TTStorage.set( TT.STORAGE.KEY_SELECT_DECORATE_ENABLED, true );
    TTStorage.set( TT.STORAGE.KEY_MAP_INFO_LIST, [] );
    TTStorage.set( TT.STORAGE.KEY_DEBUG_MODE, false );
}

TTMessaging.listen( function( message, sender ) {
    logMessage( 'Received', message.type, message.data );

    switch ( message.type ) {
        case TT.MESSAGE.TYPE_PING:
            return handlePing();
        case TT.MESSAGE.TYPE_GET_STATE:
            return handleGetState();
        case TT.MESSAGE.TYPE_LOG:
            return handleLog( message.data );
        default:
            return TTMessaging.createResponse( false, {
                error: 'Unknown message type: ' + message.type
            });
    }
});

function handlePing() {
    var uptimeMs = Date.now() - extensionStartTime;
    return TTMessaging.createResponse( true, {
        type: TT.MESSAGE.TYPE_PONG,
        uptime: uptimeMs,
        version: TT.CONFIG.EXTENSION_VERSION
    });
}

function handleGetState() {
    var defaults = {};
    defaults[TT.STORAGE.KEY_EXTENSION_STATE] = {};
    defaults[TT.STORAGE.KEY_MAP_INFO_LIST] = [];
    defaults[TT.STORAGE.KEY_SELECT_DECORATE_ENABLED] = true;
    defaults[TT.STORAGE.KEY_DEBUG_MODE] = false;

    return TTStorage.getMultiple( defaults )
        .then( function( state ) {
            return TTMessaging.createResponse( true, state );
        });
}

function handleLog( data ) {
    var level = data.level || 'info';
    var message = data.message || '';
    return addDebugLogEntry( level, message );
}

function addDebugLogEntry( level, message ) {
    return TTStorage.get( TT.STORAGE.KEY_DEBUG_LOG, [] )
        .then( function( log ) {
            var entry = {
                timestamp: Date.now(),
                level: level,
                message: message
            };
            log.unshift( entry );
            if ( log.length > TT.CONFIG.DEBUG_LOG_MAX_ENTRIES ) {
                log = log.slice( 0, TT.CONFIG.DEBUG_LOG_MAX_ENTRIES );
            }
            return TTStorage.set( TT.STORAGE.KEY_DEBUG_LOG, log );
        })
        .then( function() {
            return TTMessaging.createResponse( true, {} );
        });
}

function logMessage( direction, type, data ) {
    console.log( '[TT Background] ' + direction + ': ' + type, data );
}
