/*
 * Trip Tools Chrome Extension - DOM Utilities
 * Reusable DOM manipulation helpers for content scripts.
 * Site-agnostic - no knowledge of specific page structures.
 */

var TTDom = TTDom || {};

/**
 * Default timing configuration.
 * Sites can override via TTDom.configure().
 */
TTDom.config = {
    clickDelayMs: 500,
    elementWaitMs: 3000,
    retryIntervalMs: 100
};

/**
 * Configure timing defaults.
 * @param {Object} options - Configuration overrides.
 */
TTDom.configure = function( options ) {
    Object.assign( TTDom.config, options );
};

/**
 * Wait for a specified duration.
 * @param {number} durationMs - Milliseconds to wait.
 * @returns {Promise<void>}
 */
TTDom.wait = function( durationMs ) {
    return new Promise( function( resolve ) {
        setTimeout( resolve, durationMs );
    });
};

/**
 * Wait for element to appear in DOM.
 * @param {string} selector - CSS selector.
 * @param {Object} options - { scope, timeoutMs }
 * @returns {Promise<Element>}
 */
TTDom.waitForElement = function( selector, options ) {
    options = options || {};
    var scope = options.scope || document;
    var timeoutMs = options.timeoutMs || TTDom.config.elementWaitMs;

    return new Promise( function( resolve, reject ) {
        var element = scope.querySelector( selector );
        if ( element ) {
            return resolve( element );
        }

        var observeTarget = scope === document ? document.body : scope;
        var observer = new MutationObserver( function() {
            var el = scope.querySelector( selector );
            if ( el ) {
                observer.disconnect();
                resolve( el );
            }
        });

        observer.observe( observeTarget, {
            childList: true,
            subtree: true
        });

        setTimeout( function() {
            observer.disconnect();
            reject( new Error( 'Element not found within timeout: ' + selector ) );
        }, timeoutMs );
    });
};

/**
 * Wait for element to be removed from DOM.
 * @param {string} selector - CSS selector.
 * @param {Object} options - { scope, timeoutMs }
 * @returns {Promise<void>}
 */
TTDom.waitForElementRemoved = function( selector, options ) {
    options = options || {};
    var scope = options.scope || document;
    var timeoutMs = options.timeoutMs || TTDom.config.elementWaitMs;

    return new Promise( function( resolve, reject ) {
        if ( !scope.querySelector( selector ) ) {
            return resolve();
        }

        var observeTarget = scope === document ? document.body : scope;
        var observer = new MutationObserver( function() {
            if ( !scope.querySelector( selector ) ) {
                observer.disconnect();
                resolve();
            }
        });

        observer.observe( observeTarget, {
            childList: true,
            subtree: true
        });

        setTimeout( function() {
            observer.disconnect();
            reject( new Error( 'Element persists beyond timeout: ' + selector ) );
        }, timeoutMs );
    });
};

/**
 * Simple click with delay.
 * @param {Element} element - Element to click.
 * @param {number} delayMs - Delay after click (optional, uses config default).
 * @returns {Promise<void>}
 */
TTDom.click = function( element, delayMs ) {
    delayMs = delayMs !== undefined ? delayMs : TTDom.config.clickDelayMs;
    return new Promise( function( resolve ) {
        element.click();
        setTimeout( resolve, delayMs );
    });
};

/**
 * Realistic click with full mouse event sequence.
 * Use when simple click() doesn't work due to event handlers.
 * @param {Element} element - Element to click.
 * @returns {Promise<void>}
 */
TTDom.clickRealistic = function( element ) {
    if ( !element ) {
        return Promise.reject( new Error( 'Cannot click null element' ) );
    }

    var scrollX = window.scrollX;
    var scrollY = window.scrollY;

    element.scrollIntoView();

    return TTDom.wait( 500 )
        .then( function() {
            var eventInit = {
                view: window,
                bubbles: true,
                cancelable: true
            };

            element.dispatchEvent( new MouseEvent( 'mousedown', eventInit ) );
            element.dispatchEvent( new MouseEvent( 'mouseup', eventInit ) );
            element.dispatchEvent( new MouseEvent( 'click', eventInit ) );

            window.scrollTo( scrollX, scrollY );
            return TTDom.wait( 500 );
        });
};

/**
 * Query all elements matching selector.
 * @param {string} selector - CSS selector.
 * @param {Element} scope - Scope element (default: document).
 * @returns {Array<Element>}
 */
TTDom.queryAll = function( selector, scope ) {
    scope = scope || document;
    return Array.from( scope.querySelectorAll( selector ) );
};

/**
 * Query visible elements matching selector.
 * @param {string} selector - CSS selector.
 * @param {Element} scope - Scope element (default: document).
 * @returns {Array<Element>}
 */
TTDom.queryVisible = function( selector, scope ) {
    var elements = TTDom.queryAll( selector, scope );

    return elements.filter( function( el ) {
        var style = window.getComputedStyle( el );
        return style.display !== 'none' &&
               style.visibility !== 'hidden' &&
               el.offsetWidth > 0 &&
               el.offsetHeight > 0;
    });
};

/**
 * Find element by attribute value.
 * @param {string} selector - Base CSS selector.
 * @param {string} attrName - Attribute name to check.
 * @param {string} attrValue - Attribute value to match.
 * @param {Element} scope - Scope element (default: document).
 * @returns {Element|null}
 */
TTDom.findByAttribute = function( selector, attrName, attrValue, scope ) {
    var elements = TTDom.queryAll( selector, scope );
    return elements.find( function( el ) {
        return el.getAttribute( attrName ) === attrValue;
    }) || null;
};

/**
 * Observe DOM for elements matching selector.
 * Calls onMatch for each matching element added to the DOM.
 * @param {Object} options - { selector, onMatch, scope }
 * @returns {MutationObserver} The observer (call .disconnect() to stop).
 */
TTDom.observe = function( options ) {
    var selector = options.selector;
    var onMatch = options.onMatch;
    var scope = options.scope || document.body;

    var observer = new MutationObserver( function( mutations ) {
        mutations.forEach( function( mutation ) {
            if ( mutation.type !== 'childList' ) {
                return;
            }

            mutation.addedNodes.forEach( function( node ) {
                if ( node.nodeType !== Node.ELEMENT_NODE ) {
                    return;
                }

                // Check if the node itself matches
                if ( node.matches && node.matches( selector ) ) {
                    onMatch( node );
                }

                // Also check children of added node
                if ( node.querySelectorAll ) {
                    var matches = node.querySelectorAll( selector );
                    matches.forEach( onMatch );
                }
            });
        });
    });

    observer.observe( scope, { childList: true, subtree: true } );
    return observer;
};

/**
 * Retry an async operation with exponential backoff.
 * @param {Function} operation - Async function to retry.
 * @param {Object} options - { maxAttempts, initialDelayMs }
 * @returns {Promise}
 */
TTDom.retry = function( operation, options ) {
    options = options || {};
    var maxAttempts = options.maxAttempts || 3;
    var initialDelayMs = options.initialDelayMs || 500;

    var attempt = 0;

    function tryOnce() {
        attempt++;
        return Promise.resolve()
            .then( function() {
                return operation();
            })
            .catch( function( error ) {
                if ( attempt >= maxAttempts ) {
                    throw error;
                }
                var delay = initialDelayMs * Math.pow( 2, attempt - 1 );
                console.log( '[TTDom] Retry attempt ' + attempt + ' after ' + delay + 'ms' );
                return TTDom.wait( delay ).then( tryOnce );
            });
    }

    return tryOnce();
};

/**
 * Create an element with attributes and content.
 * @param {string} tag - HTML tag name.
 * @param {Object} options - { id, className, attrs, text, html, children }
 * @returns {Element}
 */
TTDom.createElement = function( tag, options ) {
    options = options || {};
    var el = document.createElement( tag );

    if ( options.id ) {
        el.id = options.id;
    }

    if ( options.className ) {
        el.className = options.className;
    }

    if ( options.attrs ) {
        Object.keys( options.attrs ).forEach( function( key ) {
            el.setAttribute( key, options.attrs[key] );
        });
    }

    if ( options.text ) {
        el.textContent = options.text;
    }

    if ( options.html ) {
        el.innerHTML = options.html;
    }

    if ( options.children ) {
        options.children.forEach( function( child ) {
            el.appendChild( child );
        });
    }

    return el;
};

/**
 * Set input value and dispatch change event.
 * @param {Element} input - Input element.
 * @param {string} value - Value to set.
 */
TTDom.setInputValue = function( input, value ) {
    input.value = value;
    input.dispatchEvent( new Event( 'input', { bubbles: true } ) );
    input.dispatchEvent( new Event( 'change', { bubbles: true } ) );
};
