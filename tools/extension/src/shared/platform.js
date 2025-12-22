/*
 * Trip Tools Chrome Extension - Platform Detection
 * Utilities for detecting browser, OS, and runtime environment.
 * No dependencies - safe to use in any context including content scripts.
 */

var TTPlatform = TTPlatform || {};

/**
 * Detect the current browser from user agent.
 * Order matters: check specific browsers before generic Chrome.
 * @returns {string} Browser name (Chrome, Firefox, Edge, Brave, Opera, Vivaldi).
 */
TTPlatform.detectBrowser = function() {
    var ua = navigator.userAgent;
    if ( ua.indexOf( 'Vivaldi' ) !== -1 ) {
        return 'Vivaldi';
    }
    if ( ua.indexOf( 'Edg/' ) !== -1 ) {
        return 'Edge';
    }
    if ( ua.indexOf( 'Brave' ) !== -1 ) {
        return 'Brave';
    }
    if ( ua.indexOf( 'OPR/' ) !== -1 || ua.indexOf( 'Opera' ) !== -1 ) {
        return 'Opera';
    }
    if ( ua.indexOf( 'Firefox' ) !== -1 ) {
        return 'Firefox';
    }
    return 'Chrome';
};

/**
 * Detect the current operating system.
 * @returns {string} OS name (Windows, macOS, Linux, Chrome OS, Unknown).
 */
TTPlatform.detectOS = function() {
    // Try navigator.userAgentData first (modern browsers)
    if ( navigator.userAgentData && navigator.userAgentData.platform ) {
        return navigator.userAgentData.platform;
    }

    // Fallback to navigator.platform
    if ( navigator.platform ) {
        var p = navigator.platform.toLowerCase();
        if ( p.indexOf( 'win' ) !== -1 ) {
            return 'Windows';
        }
        if ( p.indexOf( 'mac' ) !== -1 ) {
            return 'macOS';
        }
        if ( p.indexOf( 'linux' ) !== -1 ) {
            return 'Linux';
        }
        if ( p.indexOf( 'cros' ) !== -1 ) {
            return 'Chrome OS';
        }
    }

    return 'Unknown';
};

/**
 * Get complete platform information.
 * @returns {Object} Platform info with os and browser properties.
 */
TTPlatform.getInfo = function() {
    return {
        os: TTPlatform.detectOS(),
        browser: TTPlatform.detectBrowser()
    };
};

/**
 * Extract normalized origin from a URL string.
 * Handles trailing slashes, paths, case differences, and default ports.
 * Returns the original string if parsing fails.
 * @param {string} url - The URL to extract origin from.
 * @returns {string} The normalized origin (protocol + host + port).
 */
TTPlatform.getOriginFromUrl = function( url ) {
    try {
        var parsed = new URL( url );
        return parsed.origin;
    } catch ( e ) {
        return url;
    }
};
