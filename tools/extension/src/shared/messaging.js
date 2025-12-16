/*
 * Trip Tools Chrome Extension - Messaging Utilities
 * Message bus for popup <-> background <-> content script communication.
 */

var TTMessaging = TTMessaging || {};

TTMessaging.send = function( type, data ) {
    return new Promise( function( resolve, reject ) {
        var message = {
            type: type,
            data: data || {},
            timestamp: Date.now()
        };
        chrome.runtime.sendMessage( message, function( response ) {
            if ( chrome.runtime.lastError ) {
                reject( chrome.runtime.lastError );
                return;
            }
            resolve( response );
        });
    });
};

TTMessaging.sendToTab = function( tabId, type, data ) {
    return new Promise( function( resolve, reject ) {
        var message = {
            type: type,
            data: data || {},
            timestamp: Date.now()
        };
        chrome.tabs.sendMessage( tabId, message, function( response ) {
            if ( chrome.runtime.lastError ) {
                reject( chrome.runtime.lastError );
                return;
            }
            resolve( response );
        });
    });
};

TTMessaging.listen = function( handler ) {
    chrome.runtime.onMessage.addListener( function( message, sender, sendResponse ) {
        var result = handler( message, sender );
        if ( result instanceof Promise ) {
            result.then( sendResponse ).catch( function( error ) {
                sendResponse({ error: error.message });
            });
            return true;
        }
        if ( result !== undefined ) {
            sendResponse( result );
        }
        return false;
    });
};

TTMessaging.ping = function() {
    return TTMessaging.send( TT.MESSAGE.TYPE_PING, {} );
};

TTMessaging.createResponse = function( success, data ) {
    return {
        success: success,
        data: data || {},
        timestamp: Date.now()
    };
};
