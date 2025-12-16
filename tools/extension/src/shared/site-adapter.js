/*
 * Trip Tools Chrome Extension - Site Adapter Base
 * Factory for creating site-specific DOM adapters.
 * Provides selector management and common patterns.
 * Depends on: dom.js
 */

var TTSiteAdapter = TTSiteAdapter || {};

/**
 * Create a site adapter with configured selectors.
 * @param {Object} config - Adapter configuration.
 * @param {string} config.name - Adapter name for logging.
 * @param {Object} config.selectors - CSS selectors keyed by name.
 * @param {Object} config.timing - Timing configuration overrides.
 * @param {Object} config.methods - Custom methods to add to adapter.
 * @returns {Object} Adapter instance.
 */
TTSiteAdapter.create = function( config ) {
    var adapter = {
        name: config.name,
        selectors: Object.assign( {}, config.selectors || {} ),
        timing: config.timing || {},

        /**
         * Initialize the adapter. Called when content script loads.
         * Can be overridden by config.methods.initialize.
         */
        initialize: function() {
            this.log( 'Adapter initialized' );
            TTDom.configure( this.timing );
        },

        /**
         * Get element by selector key.
         * @param {string} key - Selector key from config.
         * @param {Element} scope - Optional scope element.
         * @returns {Element|null}
         */
        getElement: function( key, scope ) {
            var selector = this.selectors[key];
            if ( !selector ) {
                this.warn( 'Unknown selector: ' + key );
                return null;
            }
            scope = scope || document;
            return scope.querySelector( selector );
        },

        /**
         * Get all elements by selector key.
         * @param {string} key - Selector key from config.
         * @param {Element} scope - Optional scope element.
         * @returns {Array<Element>}
         */
        getAllElements: function( key, scope ) {
            var selector = this.selectors[key];
            if ( !selector ) {
                this.warn( 'Unknown selector: ' + key );
                return [];
            }
            return TTDom.queryAll( selector, scope );
        },

        /**
         * Wait for element by selector key.
         * @param {string} key - Selector key from config.
         * @param {Object} options - Wait options { scope, timeoutMs }.
         * @returns {Promise<Element>}
         */
        waitForElement: function( key, options ) {
            var selector = this.selectors[key];
            if ( !selector ) {
                return Promise.reject(
                    new Error( '[' + this.name + '] Unknown selector: ' + key )
                );
            }
            return TTDom.waitForElement( selector, options );
        },

        /**
         * Wait for element to be removed by selector key.
         * @param {string} key - Selector key from config.
         * @param {Object} options - Wait options { scope, timeoutMs }.
         * @returns {Promise<void>}
         */
        waitForElementRemoved: function( key, options ) {
            var selector = this.selectors[key];
            if ( !selector ) {
                return Promise.reject(
                    new Error( '[' + this.name + '] Unknown selector: ' + key )
                );
            }
            return TTDom.waitForElementRemoved( selector, options );
        },

        /**
         * Get visible elements by selector key.
         * @param {string} key - Selector key from config.
         * @param {Element} scope - Optional scope element.
         * @returns {Array<Element>}
         */
        getVisibleElements: function( key, scope ) {
            var selector = this.selectors[key];
            if ( !selector ) {
                this.warn( 'Unknown selector: ' + key );
                return [];
            }
            return TTDom.queryVisible( selector, scope );
        },

        /**
         * Find element by selector key and attribute value.
         * @param {string} key - Selector key from config.
         * @param {string} attrName - Attribute name.
         * @param {string} attrValue - Attribute value to match.
         * @param {Element} scope - Optional scope element.
         * @returns {Element|null}
         */
        findByAttribute: function( key, attrName, attrValue, scope ) {
            var selector = this.selectors[key];
            if ( !selector ) {
                this.warn( 'Unknown selector: ' + key );
                return null;
            }
            return TTDom.findByAttribute( selector, attrName, attrValue, scope );
        },

        /**
         * Observe for elements matching selector key.
         * @param {string} key - Selector key from config.
         * @param {Function} onMatch - Callback for matching elements.
         * @param {Element} scope - Optional scope element.
         * @returns {MutationObserver}
         */
        observe: function( key, onMatch, scope ) {
            var selector = this.selectors[key];
            if ( !selector ) {
                this.warn( 'Unknown selector for observe: ' + key );
                return null;
            }
            return TTDom.observe({
                selector: selector,
                onMatch: onMatch,
                scope: scope
            });
        },

        /**
         * Get raw selector by key.
         * Useful when you need the selector string directly.
         * @param {string} key - Selector key from config.
         * @returns {string|null}
         */
        getSelector: function( key ) {
            return this.selectors[key] || null;
        },

        /**
         * Update selectors at runtime.
         * Use for version-specific selector changes.
         * @param {Object} updates - Selector updates to apply.
         */
        updateSelectors: function( updates ) {
            Object.assign( this.selectors, updates );
            this.log( 'Selectors updated' );
        },

        /**
         * Log with adapter context.
         * @param {string} message - Message to log.
         */
        log: function( message ) {
            console.log( '[' + this.name + '] ' + message );
        },

        /**
         * Warn with adapter context.
         * @param {string} message - Message to log.
         */
        warn: function( message ) {
            console.warn( '[' + this.name + '] ' + message );
        },

        /**
         * Error with adapter context.
         * @param {string} message - Message to log.
         */
        error: function( message ) {
            console.error( '[' + this.name + '] ' + message );
        }
    };

    // Allow config to extend adapter with custom methods
    if ( config.methods ) {
        Object.keys( config.methods ).forEach( function( methodName ) {
            adapter[methodName] = config.methods[methodName];
        });
    }

    return adapter;
};
