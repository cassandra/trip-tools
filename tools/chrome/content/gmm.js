/*
 * Trip Tools Chrome Extension - GMM Content Script
 * Injected into Google My Maps pages.
 * Uses TTGmmAdapter for DOM operations, TTClientConfig for categories.
 * Depends on: constants.js, storage.js, client-config.js, dom.js,
 *             site-adapter.js, gmm-selectors.js, gmm-adapter.js
 */

( function() {
    'use strict';

    // =========================================================================
    // Constants
    // =========================================================================

    var TT_BUTTON_CLASS = 'tt-gmm-btn';
    var TT_CATEGORY_BTN_CLASS = 'tt-category-btn';
    var TT_SUBCATEGORY_PICKER_CLASS = 'tt-subcategory-picker';
    var TT_DECORATED_ATTR = 'data-tt-decorated';

    // =========================================================================
    // Initialization
    // =========================================================================

    function initialize() {
        console.log( '[TT GMM] Content script loaded' );

        // Set up message listener for commands from popup/background
        chrome.runtime.onMessage.addListener( handleMessage );

        // Initialize adapter with our dialog handlers
        TTGmmAdapter.initialize({
            onAddToMapDialog: handleAddToMapDialog,
            onLocationDetailsDialog: handleLocationDetailsDialog
        });

        console.log( '[TT GMM] Adapter initialized, waiting for dialogs' );
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
        console.log( '[TT GMM] Received message:', request.type );

        switch ( request.type ) {
            case TT.MESSAGE.TYPE_GMM_SEARCH_AND_ADD:
                handleSearchAndAdd( request.data )
                    .then( function( result ) {
                        sendResponse({ success: true, data: result });
                    })
                    .catch( function( error ) {
                        sendResponse({ success: false, error: error.message });
                    });
                return true; // Async response

            case TT.MESSAGE.TYPE_GMM_GET_MAP_INFO:
                sendResponse({
                    success: true,
                    data: getMapInfo()
                });
                return false;

            default:
                return false;
        }
    }

    /**
     * Handle search and add location request.
     * @param {Object} data - { searchText, categorySlug, subcategorySlug }
     * @returns {Promise<Object>}
     */
    function handleSearchAndAdd( data ) {
        return TTClientConfig.getCategoryBySlug( data.categorySlug )
            .then( function( category ) {
                if ( !category ) {
                    throw new Error( 'Category not found: ' + data.categorySlug );
                }

                var subcategory = null;
                if ( data.subcategorySlug && category.subcategories ) {
                    subcategory = category.subcategories.find( function( s ) {
                        return s.slug === data.subcategorySlug;
                    });
                }

                var colorRgb = subcategory ? subcategory.gmm_color : category.gmm_color;
                var iconCode = subcategory ? subcategory.gmm_icon : category.gmm_icon;

                return TTGmmAdapter.searchAndAddLocation( data.searchText, {
                    layerTitle: category.title,
                    colorRgb: colorRgb,
                    iconCode: iconCode
                });
            })
            .then( function( result ) {
                // Build location data for server
                var locationData = {
                    gmm_id: result.gmmId,
                    title: result.title,
                    category_slug: data.categorySlug,
                    subcategory_slug: data.subcategorySlug
                };

                // Include coordinates if available
                if ( result.coordinates ) {
                    locationData.latitude = result.coordinates.latitude;
                    locationData.longitude = result.coordinates.longitude;
                }

                // Save to server
                return saveLocationToServer( locationData ).then( function( serverLocation ) {
                    return {
                        gmmId: result.gmmId,
                        title: result.title,
                        coordinates: result.coordinates,
                        serverLocation: serverLocation
                    };
                });
            });
    }

    /**
     * Get current map info from URL.
     * @returns {Object} { mapId, url, tabId }
     */
    function getMapInfo() {
        var url = new URL( window.location.href );
        var mapId = url.searchParams.get( 'mid' );

        return {
            mapId: mapId,
            url: window.location.href
        };
    }

    // =========================================================================
    // Dialog Handlers
    // =========================================================================

    /**
     * Handle add-to-map dialog opening.
     * Decorates with category buttons.
     * @param {Element} dialogNode - The dialog element.
     */
    function handleAddToMapDialog( dialogNode ) {
        // Check if already decorated
        if ( dialogNode.getAttribute( TT_DECORATED_ATTR ) ) {
            return;
        }
        dialogNode.setAttribute( TT_DECORATED_ATTR, 'true' );

        // Get categories from client config
        TTClientConfig.getLocationCategories()
            .then( function( categories ) {
                if ( categories && categories.length > 0 ) {
                    decorateAddToMapDialog( dialogNode, categories );
                } else {
                    console.log( '[TT GMM] No categories available' );
                }
            })
            .catch( function( error ) {
                console.error( '[TT GMM] Failed to get categories:', error );
            });
    }

    /**
     * Decorate add-to-map dialog with category buttons.
     * @param {Element} dialogNode - The dialog element.
     * @param {Array} categories - Location categories from server.
     */
    function decorateAddToMapDialog( dialogNode, categories ) {
        var addButton = dialogNode.querySelector( TTGmmAdapter.selectors.ADD_TO_MAP_BUTTON );
        if ( !addButton ) {
            return;
        }

        var container = addButton.parentNode;

        // Create button container
        var buttonContainer = TTDom.createElement( 'div', {
            className: 'tt-category-buttons'
        });

        // Add a button for each category
        categories.forEach( function( category ) {
            var button = TTDom.createElement( 'button', {
                id: 'tt-add-' + category.slug,
                className: TT_BUTTON_CLASS + ' ' + TT_CATEGORY_BTN_CLASS,
                text: category.title
            });

            button.addEventListener( 'click', function( event ) {
                event.stopPropagation();
                handleCategoryButtonClick( dialogNode, category );
            });

            buttonContainer.appendChild( button );
        });

        container.appendChild( buttonContainer );
        console.log( '[TT GMM] Add-to-map dialog decorated with ' + categories.length + ' categories' );
    }

    /**
     * Handle category button click.
     * Shows subcategory picker if needed, otherwise adds location directly.
     * @param {Element} dialogNode - The dialog element.
     * @param {Object} category - Category from server.
     */
    function handleCategoryButtonClick( dialogNode, category ) {
        console.log( '[TT GMM] Category selected: ' + category.title );

        // If category has subcategories, show picker
        if ( category.subcategories && category.subcategories.length > 0 ) {
            showSubcategoryPicker( dialogNode, category );
        } else {
            addLocationWithCategory( dialogNode, category, null );
        }
    }

    /**
     * Show subcategory picker overlay.
     * @param {Element} dialogNode - The dialog element.
     * @param {Object} category - Category with subcategories.
     */
    function showSubcategoryPicker( dialogNode, category ) {
        // Remove any existing picker
        var existingPicker = document.querySelector( '.' + TT_SUBCATEGORY_PICKER_CLASS );
        if ( existingPicker ) {
            existingPicker.remove();
        }

        // Create picker container
        var picker = TTDom.createElement( 'div', {
            className: TT_SUBCATEGORY_PICKER_CLASS
        });

        // Add header
        var header = TTDom.createElement( 'div', {
            className: 'tt-picker-header',
            text: 'Select ' + category.title + ' type:'
        });
        picker.appendChild( header );

        // Add button container
        var buttonContainer = TTDom.createElement( 'div', {
            className: 'tt-picker-buttons'
        });

        // Add subcategory buttons
        category.subcategories.forEach( function( subcategory ) {
            var btn = TTDom.createElement( 'button', {
                className: TT_BUTTON_CLASS,
                text: subcategory.title
            });

            btn.addEventListener( 'click', function( event ) {
                event.stopPropagation();
                picker.remove();
                addLocationWithCategory( dialogNode, category, subcategory );
            });

            buttonContainer.appendChild( btn );
        });

        picker.appendChild( buttonContainer );

        // Add cancel button
        var cancelBtn = TTDom.createElement( 'button', {
            className: TT_BUTTON_CLASS + ' tt-cancel-btn',
            text: 'Cancel'
        });
        cancelBtn.addEventListener( 'click', function() {
            picker.remove();
        });
        picker.appendChild( cancelBtn );

        document.body.appendChild( picker );
    }

    /**
     * Add location with category/subcategory styling.
     * @param {Element} dialogNode - The dialog element.
     * @param {Object} category - Category from server.
     * @param {Object|null} subcategory - Subcategory or null.
     */
    function addLocationWithCategory( dialogNode, category, subcategory ) {
        var colorRgb = subcategory ? subcategory.gmm_color : category.gmm_color;
        var iconCode = subcategory ? subcategory.gmm_icon : category.gmm_icon;

        console.log( '[TT GMM] Adding location - layer: ' + category.title +
                     ', color: ' + colorRgb + ', icon: ' + iconCode );

        TTGmmAdapter.addLocationToLayer({
            layerTitle: category.title,
            colorRgb: colorRgb,
            iconCode: iconCode
        })
        .then( function( result ) {
            console.log( '[TT GMM] Location added to map:', result );

            // Build location data for server
            var locationData = {
                gmm_id: result.gmmId,
                title: result.title,
                category_slug: category.slug,
                subcategory_slug: subcategory ? subcategory.slug : null
            };

            // Include coordinates if available
            if ( result.coordinates ) {
                locationData.latitude = result.coordinates.latitude;
                locationData.longitude = result.coordinates.longitude;
            }

            // Save to server via background script
            return saveLocationToServer( locationData );
        })
        .then( function( serverLocation ) {
            console.log( '[TT GMM] Location saved to server:', serverLocation );
        })
        .catch( function( error ) {
            console.error( '[TT GMM] Failed to add location:', error );
        });
    }

    // =========================================================================
    // Location Details Dialog
    // =========================================================================

    /**
     * Handle location details dialog opening.
     * @param {Element} dialogNode - The dialog element.
     */
    function handleLocationDetailsDialog( dialogNode ) {
        // Check if already decorated
        if ( dialogNode.getAttribute( TT_DECORATED_ATTR ) ) {
            return;
        }
        dialogNode.setAttribute( TT_DECORATED_ATTR, 'true' );

        var title = TTGmmAdapter.getLocationTitle();
        if ( !title ) {
            return;
        }

        var gmmId = TTGmmAdapter.getCurrentLocationId();
        console.log( '[TT GMM] Location details opened: ' + title + ' (id: ' + gmmId + ')' );

        // Look up location from server
        getLocationFromServer( gmmId )
            .then( function( location ) {
                if ( location ) {
                    decorateLocationDetails( dialogNode, location );
                }
            })
            .catch( function( error ) {
                console.error( '[TT GMM] Failed to get location details:', error );
            });
    }

    /**
     * Decorate location details with custom attributes.
     * @param {Element} dialogNode - The dialog element.
     * @param {Object} location - Location from server.
     */
    function decorateLocationDetails( dialogNode, location ) {
        var isEditMode = TTGmmAdapter.isEditMode();

        // Get category definition for custom attributes
        TTClientConfig.getCategoryBySlug( location.category_slug )
            .then( function( category ) {
                if ( category ) {
                    addCustomAttributeUI( dialogNode, location, category, isEditMode );
                }
            });
    }

    /**
     * Add custom attribute UI to location details.
     * @param {Element} dialogNode - The dialog element.
     * @param {Object} location - Location from server.
     * @param {Object} category - Category definition.
     * @param {boolean} isEditMode - Whether in edit mode.
     */
    function addCustomAttributeUI( dialogNode, location, category, isEditMode ) {
        // TODO: Implement custom attribute display/editing
        // This will be similar to the prototype but pulling attribute definitions
        // from category.custom_attributes (from server config)
        console.log( '[TT GMM] Custom attributes UI not yet implemented' );
    }

    // =========================================================================
    // Server Communication
    // =========================================================================

    /**
     * Save location to server via background script.
     * @param {Object} locationData - Location data to save.
     * @returns {Promise<Object>} Server response.
     */
    function saveLocationToServer( locationData ) {
        return new Promise( function( resolve, reject ) {
            chrome.runtime.sendMessage({
                type: TT.MESSAGE.TYPE_SAVE_LOCATION,
                data: locationData
            }, function( response ) {
                if ( chrome.runtime.lastError ) {
                    reject( new Error( chrome.runtime.lastError.message ) );
                    return;
                }
                if ( response && response.success ) {
                    resolve( response.data );
                } else {
                    reject( new Error( response ? response.error : 'No response' ) );
                }
            });
        });
    }

    /**
     * Get location from server via background script.
     * @param {string} gmmId - GMM location ID.
     * @returns {Promise<Object|null>} Location or null.
     */
    function getLocationFromServer( gmmId ) {
        return new Promise( function( resolve, reject ) {
            chrome.runtime.sendMessage({
                type: TT.MESSAGE.TYPE_GET_LOCATION,
                data: { gmm_id: gmmId }
            }, function( response ) {
                if ( chrome.runtime.lastError ) {
                    reject( new Error( chrome.runtime.lastError.message ) );
                    return;
                }
                if ( response && response.success ) {
                    resolve( response.data );
                } else if ( response && !response.success && response.notFound ) {
                    resolve( null );
                } else {
                    reject( new Error( response ? response.error : 'No response' ) );
                }
            });
        });
    }

    // =========================================================================
    // Start
    // =========================================================================

    initialize();

})();
