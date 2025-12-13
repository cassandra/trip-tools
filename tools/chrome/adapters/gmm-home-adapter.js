/*
 * Trip Tools Chrome Extension - Google My Maps Home Page Adapter
 * Handles GMM home page DOM manipulation for map creation.
 * Depends on: dom.js, site-adapter.js, gmm-home-selectors.js
 */

var TTGmmHomeAdapter = TTSiteAdapter.create({
    name: 'GMM-Home',
    selectors: TTGmmHomeSelectors,
    timing: {
        clickDelayMs: 500,
        elementWaitMs: 5000
    },
    methods: {

        // =====================================================================
        // Initialization
        // =====================================================================

        /**
         * Initialize GMM home adapter.
         */
        initialize: function() {
            this.log( 'Initializing with selector version: ' + this.selectors.VERSION );
            TTDom.configure( this.timing );
        },

        /**
         * Check if we're on the GMM home page.
         * @returns {boolean}
         */
        isHomePage: function() {
            var path = window.location.pathname;
            // Home page is /maps/d/ or /maps/d/u/0/ etc, but NOT /maps/d/edit
            return path.match( /^\/maps\/d\/(u\/\d+\/)?$/ ) !== null;
        },

        // =====================================================================
        // Map Creation
        // =====================================================================

        /**
         * Click the "Create a new map" button.
         * This will cause navigation to the new map's edit page.
         * @returns {Promise<void>}
         */
        clickCreateMap: function() {
            var self = this;

            return this.waitForElement( 'CREATE_MAP_BUTTON' )
                .then( function( button ) {
                    self.log( 'Clicking create map button' );
                    return TTDom.clickRealistic( button );
                });
        },

        /**
         * Get the create map button element if it exists.
         * @returns {Element|null}
         */
        getCreateMapButton: function() {
            return this.getElement( 'CREATE_MAP_BUTTON' );
        },

        // =====================================================================
        // Map List (for future use - Issue #123)
        // =====================================================================

        /**
         * Get all map items from the list.
         * @returns {Array<Object>} Array of { title, node }.
         */
        getMapList: function() {
            var self = this;
            var items = this.getAllElements( 'MAP_LIST_ITEM' );

            return items.map( function( node ) {
                return {
                    title: node.textContent.trim(),
                    node: node
                };
            });
        }
    }
});
