/*
 * Trip Tools Chrome Extension - Text Utilities
 * Reusable text parsing and pattern matching for content scripts.
 * No DOM dependencies - pure text/string operations.
 */

var TTText = TTText || {};

/**
 * Phone number patterns for detection.
 * Matches international (+1...) and US formats.
 */
TTText.PHONE_PATTERNS = [
    /^\+\d[\d\s\-().]{7,}$/,                    // International: +1 303-736-8419
    /^\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}$/     // US: (303) 555-1234
];

/**
 * Check if text looks like a phone number.
 * @param {string} text - Text to check.
 * @returns {boolean}
 */
TTText.isPhoneNumber = function( text ) {
    if ( !text ) return false;
    var trimmed = text.trim();
    return TTText.PHONE_PATTERNS.some( function( pattern ) {
        return pattern.test( trimmed );
    });
};

/**
 * Check if text looks like a street address.
 * Heuristic: contains comma, has digits, and has state abbreviation or zip code.
 * @param {string} text - Text to check.
 * @returns {boolean}
 */
TTText.isStreetAddress = function( text ) {
    if ( !text ) return false;
    var trimmed = text.trim();

    // Must have comma (separating city/state)
    if ( !trimmed.includes( ',' ) ) return false;

    // Must have digits (street number or zip)
    if ( !/\d/.test( trimmed ) ) return false;

    // Should have US state abbreviation or 5-digit zip
    var hasStateAbbrev = /\b[A-Z]{2}\b/.test( trimmed );
    var hasZipCode = /\b\d{5}(-\d{4})?\b/.test( trimmed );

    return hasStateAbbrev || hasZipCode;
};

/**
 * Check if text looks like a URL.
 * @param {string} text - Text to check.
 * @returns {boolean}
 */
TTText.isUrl = function( text ) {
    if ( !text ) return false;
    var trimmed = text.trim();
    return /^https?:\/\//i.test( trimmed );
};

/**
 * Extract URL from anchor element, filtering out unwanted domains.
 * @param {Element} anchor - Anchor element.
 * @param {Array<string>} excludeDomains - Domains to exclude (e.g., ['maps.google.com']).
 * @returns {string|null} - URL or null if excluded/invalid.
 */
TTText.extractUrlFromAnchor = function( anchor, excludeDomains ) {
    if ( !anchor || !anchor.href ) return null;

    excludeDomains = excludeDomains || [];
    var href = anchor.href;

    for ( var i = 0; i < excludeDomains.length; i++ ) {
        if ( href.includes( excludeDomains[i] ) ) {
            return null;
        }
    }

    return href;
};
