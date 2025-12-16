/**
 * Page Info Module
 *
 * Provides pluggable URL parsing for detecting site-specific page context.
 * Separates URL fetching from site-specific parsing to allow reuse across
 * different extension contexts (popup, content scripts, service worker).
 */
var TTPageInfo = TTPageInfo || {};

/**
 * Site parsers registry. Each parser takes a URL and returns site-specific info or null.
 * @type {Object.<string, Function>}
 */
TTPageInfo.parsers = {};

/**
 * Register a site parser.
 * @param {string} siteKey - Unique site identifier (e.g., 'gmm')
 * @param {Function} parser - Function(url) => { site, ...siteData } or null
 */
TTPageInfo.registerParser = function( siteKey, parser ) {
    TTPageInfo.parsers[ siteKey ] = parser;
};

/**
 * Get current tab URL (only works in popup or service worker context).
 * @returns {Promise<string|null>}
 */
TTPageInfo.getCurrentTabUrl = function() {
    return new Promise( function( resolve ) {
        chrome.tabs.query( { active: true, currentWindow: true }, function( tabs ) {
            resolve( tabs && tabs.length && tabs[ 0 ].url ? tabs[ 0 ].url : null );
        });
    });
};

/**
 * Parse URL through all registered parsers.
 * @param {string} url - URL to parse
 * @returns {Object|null} First matching parser result or null
 */
TTPageInfo.parseUrl = function( url ) {
    if ( !url ) return null;
    for ( var key in TTPageInfo.parsers ) {
        if ( TTPageInfo.parsers.hasOwnProperty( key ) ) {
            var result = TTPageInfo.parsers[ key ]( url );
            if ( result ) return result;
        }
    }
    return null;
};

/**
 * Detect current page info by getting current tab URL and parsing it.
 * Only works in popup or service worker context.
 * @returns {Promise<Object|null>}
 */
TTPageInfo.detectCurrentPage = function() {
    return TTPageInfo.getCurrentTabUrl()
        .then( function( url ) {
            return TTPageInfo.parseUrl( url );
        });
};

// =============================================================================
// GMM Parser
// =============================================================================

TTPageInfo.registerParser( 'gmm', function( url ) {
    try {
        var urlObj = new URL( url );
        // Match GMM pages: google.com/maps/d/...
        if ( !urlObj.hostname.includes( 'google.com' ) ||
             !urlObj.pathname.includes( '/maps/d' ) ) {
            return null;
        }
        var mapId = urlObj.searchParams.get( 'mid' );
        if ( !mapId ) return null;

        return {
            site: 'gmm',
            mapId: mapId,
            isEditPage: urlObj.pathname.includes( '/edit' )
        };
    } catch ( e ) {
        return null;
    }
});
