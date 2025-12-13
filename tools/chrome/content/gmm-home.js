/*
 * Trip Tools Chrome Extension - GMM Home Page Content Script
 * Injected into Google My Maps home page.
 * Handles map creation automation triggered from background/popup.
 * Decorates map cards that are linked to Trip Tools trips.
 * Depends on: constants.js, dom.js, site-adapter.js,
 *             gmm-home-selectors.js, gmm-home-adapter.js
 */

( function() {
    'use strict';

    // =========================================================================
    // Constants
    // =========================================================================

    var BADGE_CLASS = 'tt-linked-badge';
    var BADGE_ICON_CLASS = 'tt-linked-badge-icon';
    var DATA_MID_ATTR = 'data-mid';

    // =========================================================================
    // Initialization
    // =========================================================================

    function initialize() {
        console.log( '[TT GMM-Home] Content script loaded' );

        // Initialize adapter
        TTGmmHomeAdapter.initialize();

        // Set up message listener for commands from background
        chrome.runtime.onMessage.addListener( handleMessage );

        // Decorate linked map cards
        initializeBadgeDecoration();

        console.log( '[TT GMM-Home] Ready for commands' );
    }

    // =========================================================================
    // Message Handling
    // =========================================================================

    /**
     * Handle messages from background script or popup.
     * @param {Object} request - Message request.
     * @param {Object} sender - Message sender.
     * @param {Function} sendResponse - Response callback.
     * @returns {boolean} True if async response.
     */
    function handleMessage( request, sender, sendResponse ) {
        console.log( '[TT GMM-Home] Received message:', request.type );

        switch ( request.type ) {
            case TT.MESSAGE.TYPE_GMM_CREATE_MAP:
                handleCreateMap()
                    .then( function( result ) {
                        sendResponse({ success: true, data: result });
                    })
                    .catch( function( error ) {
                        sendResponse({ success: false, error: error.message });
                    });
                return true; // Async response

            case TT.MESSAGE.TYPE_PING:
                sendResponse({ success: true, page: 'gmm-home' });
                return false;

            default:
                return false;
        }
    }

    /**
     * Handle create map command.
     * Clicks the create button and waits briefly.
     * The page will navigate to the new map's edit page.
     * @returns {Promise<Object>}
     */
    function handleCreateMap() {
        console.log( '[TT GMM-Home] Creating new map...' );

        if ( !TTGmmHomeAdapter.isHomePage() ) {
            return Promise.reject( new Error( 'Not on GMM home page' ) );
        }

        return TTGmmHomeAdapter.clickCreateMap()
            .then( function() {
                console.log( '[TT GMM-Home] Create button clicked, page will navigate' );
                return { clicked: true };
            });
    }

    // =========================================================================
    // Badge Decoration
    // =========================================================================

    /**
     * Initialize badge decoration for linked maps.
     * Checks auth status, fetches trips, and decorates matching cards.
     */
    function initializeBadgeDecoration() {
        chrome.runtime.sendMessage(
            { type: TT.MESSAGE.TYPE_AUTH_STATUS_REQUEST },
            function( response ) {
                if ( response && response.success && response.data && response.data.authorized ) {
                    fetchTripsAndDecorate();
                }
            }
        );
    }

    /**
     * Fetch all trips and decorate matching map cards.
     */
    function fetchTripsAndDecorate() {
        chrome.runtime.sendMessage(
            { type: TT.MESSAGE.TYPE_GET_ALL_TRIPS },
            function( response ) {
                if ( response && response.success && response.data && response.data.trips ) {
                    var linkedMaps = buildLinkedMapsLookup( response.data.trips );
                    decorateAllCards( linkedMaps );
                    setupBadgeObserver( linkedMaps );
                }
            }
        );
    }

    /**
     * Build map of gmm_map_id -> trip for quick lookup.
     * @param {Array} trips - Array of trip objects.
     * @returns {Object} Map of gmm_map_id to trip.
     */
    function buildLinkedMapsLookup( trips ) {
        var linkedMaps = {};
        trips.forEach( function( trip ) {
            if ( trip.gmm_map_id ) {
                linkedMaps[ trip.gmm_map_id ] = trip;
            }
        });
        return linkedMaps;
    }

    /**
     * Find all map cards and decorate linked ones.
     * @param {Object} linkedMaps - Map of gmm_map_id to trip.
     */
    function decorateAllCards( linkedMaps ) {
        var elementsWithMid = document.querySelectorAll( '[' + DATA_MID_ATTR + ']' );

        elementsWithMid.forEach( function( el ) {
            decorateIfLinked( el, linkedMaps );
        });
    }

    /**
     * Check if element has a linked map and decorate it.
     * @param {Element} el - Element with data-mid attribute.
     * @param {Object} linkedMaps - Map of gmm_map_id to trip.
     */
    function decorateIfLinked( el, linkedMaps ) {
        var mapId = el.getAttribute( DATA_MID_ATTR );
        if ( mapId && linkedMaps[ mapId ] ) {
            addBadgeToCard( el, linkedMaps[ mapId ] );
        }
    }

    /**
     * Find the card container element from a data-mid element.
     * The data-mid is nested deep in share/menu buttons.
     * We traverse up looking for an element whose first child has a background-image
     * style (the map thumbnail).
     * @param {Element} midElement - Element with data-mid attribute.
     * @returns {Element|null} The card container or null.
     */
    function findCardContainer( midElement ) {
        var el = midElement;
        var maxLevels = 15;

        while ( el && maxLevels > 0 ) {
            el = el.parentElement;
            maxLevels--;

            if ( !el ) {
                break;
            }

            // Card container's first child is the thumbnail with background-image
            var firstChild = el.firstElementChild;
            if ( firstChild && firstChild.style && firstChild.style.backgroundImage ) {
                return el;
            }
        }

        return null;
    }

    /**
     * Add badge to a map card.
     * @param {Element} midElement - Element with data-mid attribute.
     * @param {Object} trip - Trip object.
     */
    function addBadgeToCard( midElement, trip ) {
        // Find the card container by traversing up to find element with thumbnail
        // The data-mid is nested deep in the share menu; traverse up to card root
        var card = findCardContainer( midElement );
        if ( !card ) {
            return;
        }

        // Don't add duplicate badges
        if ( card.querySelector( '.' + BADGE_CLASS ) ) {
            return;
        }

        // Create badge with icon + text
        var badge = document.createElement( 'div' );
        badge.className = BADGE_CLASS;
        badge.title = 'Linked to: ' + trip.title;

        var icon = document.createElement( 'img' );
        icon.src = chrome.runtime.getURL( 'images/icon-on-primary-16.png' );
        icon.className = BADGE_ICON_CLASS;
        icon.alt = '';

        var text = document.createElement( 'span' );
        text.textContent = 'Trip Tools';

        badge.appendChild( icon );
        badge.appendChild( text );

        // Insert at top of card
        card.style.position = 'relative';
        card.insertBefore( badge, card.firstChild );
    }

    /**
     * Set up observer for dynamically loaded cards.
     * My Maps home page may load cards via infinite scroll or tab switching.
     * @param {Object} linkedMaps - Map of gmm_map_id to trip.
     */
    function setupBadgeObserver( linkedMaps ) {
        var observer = new MutationObserver( function( mutations ) {
            mutations.forEach( function( mutation ) {
                mutation.addedNodes.forEach( function( node ) {
                    if ( node.nodeType === Node.ELEMENT_NODE ) {
                        // Check if new node itself has data-mid
                        if ( node.hasAttribute && node.hasAttribute( DATA_MID_ATTR ) ) {
                            decorateIfLinked( node, linkedMaps );
                        }

                        // Check descendants for data-mid
                        if ( node.querySelectorAll ) {
                            var newMidElements = node.querySelectorAll(
                                '[' + DATA_MID_ATTR + ']'
                            );
                            newMidElements.forEach( function( el ) {
                                decorateIfLinked( el, linkedMaps );
                            });
                        }
                    }
                });
            });
        });

        observer.observe( document.body, {
            childList: true,
            subtree: true
        });
    }

    // =========================================================================
    // Start
    // =========================================================================

    initialize();

})();
