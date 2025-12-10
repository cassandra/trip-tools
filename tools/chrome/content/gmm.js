/*
 * Trip Tools Chrome Extension - GMM Content Script
 * Injected into Google My Maps pages.
 * Uses TTGmmAdapter for DOM operations, service worker for categories.
 * Depends on: constants.js, storage.js, dom.js,
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
    // Service Worker Communication
    // =========================================================================

    /**
     * Request full client config from service worker.
     * Includes categories and enum type definitions.
     * @returns {Promise<Object>} Config with location_categories, desirability_type, advanced_booking_type.
     */
    function getClientConfig() {
        return new Promise( function( resolve, reject ) {
            chrome.runtime.sendMessage({
                type: TT.MESSAGE.TYPE_GET_LOCATION_CATEGORIES
            }, function( response ) {
                if ( chrome.runtime.lastError ) {
                    reject( new Error( chrome.runtime.lastError.message ) );
                    return;
                }
                if ( response && response.success ) {
                    resolve( response.data || {} );
                } else {
                    reject( new Error( response ? response.error : 'No response' ) );
                }
            });
        });
    }

    /**
     * Request location categories from service worker.
     * @returns {Promise<Array>} Array of category objects.
     */
    function getLocationCategories() {
        return getClientConfig()
            .then( function( config ) {
                return config.location_categories || [];
            });
    }

    /**
     * Get a category by slug from cached categories.
     * @param {string} slug - Category slug.
     * @returns {Promise<Object|null>} Category object or null.
     */
    function getCategoryBySlug( slug ) {
        return getLocationCategories()
            .then( function( categories ) {
                return categories.find( function( c ) {
                    return c.slug === slug;
                }) || null;
            });
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

            case TT.MESSAGE.TYPE_GMM_RENAME_MAP:
                handleRenameMap( request.data )
                    .then( function( result ) {
                        sendResponse({ success: true, data: result });
                    })
                    .catch( function( error ) {
                        sendResponse({ success: false, error: error.message });
                    });
                return true; // Async response

            case TT.MESSAGE.TYPE_PING:
                sendResponse({ success: true, page: 'gmm-edit' });
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
        return getCategoryBySlug( data.categorySlug )
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

                var colorRgb = subcategory ? subcategory.color_code : category.color_code;
                var iconCode = subcategory ? subcategory.icon_code : category.icon_code;

                return TTGmmAdapter.searchAndAddLocation( data.searchText, {
                    layerTitle: category.name,
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

    /**
     * Handle rename map request.
     * @param {Object} data - { title, description }
     * @returns {Promise<Object>}
     */
    function handleRenameMap( data ) {
        if ( !data || !data.title ) {
            return Promise.reject( new Error( 'Title is required' ) );
        }

        return TTGmmAdapter.renameMap({
            title: data.title,
            description: data.description
        })
            .then( function() {
                return {
                    success: true,
                    title: data.title
                };
            });
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

        // Get categories from service worker
        getLocationCategories()
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

        // Hide the original "Add to map" button
        addButton.style.display = 'none';

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
                text: category.name
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
        console.log( '[TT GMM] Category selected: ' + category.name );

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
            text: 'Select ' + category.name + ' type:'
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
                text: subcategory.name
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
        var colorRgb = subcategory ? subcategory.color_code : category.color_code;
        var iconCode = subcategory ? subcategory.icon_code : category.icon_code;

        console.log( '[TT GMM] Adding location - layer: ' + category.name +
                     ', color: ' + colorRgb + ', icon: ' + iconCode );

        TTGmmAdapter.addLocationToLayer({
            layerTitle: category.name,
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
            showErrorNotification( 'Location not saved to server. Try syncing later.' );
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
        // Get full client config for categories and enum types
        getClientConfig()
            .then( function( config ) {
                // Render UI for current mode
                function renderUI() {
                    var isEditMode = TTGmmAdapter.isEditMode();
                    addCustomAttributeUI( dialogNode, location, config, isEditMode );
                }

                renderUI();

                // Watch for edit mode changes via contenteditable attribute
                var titleNode = dialogNode.querySelector( TTGmmAdapter.selectors.TITLE_DIV );
                if ( titleNode ) {
                    var observer = new MutationObserver( function( mutations ) {
                        mutations.forEach( function( mutation ) {
                            if ( mutation.attributeName === 'contenteditable' ) {
                                renderUI();
                            }
                        });
                    });
                    observer.observe( titleNode, { attributes: true } );
                }
            })
            .catch( function( error ) {
                console.error( '[TT GMM] Failed to get client config:', error );
            });
    }

    // =========================================================================
    // Custom Attributes UI Helpers
    // =========================================================================

    var TT_CUSTOM_ATTRS_CONTAINER_ID = 'tt-custom-attrs-container';
    var TT_INTERCEPTED_ATTR = 'data-tt-intercepted';

    /**
     * Build a dropdown select element.
     * @param {string} id - Element ID.
     * @param {string} label - Label text.
     * @param {Array} options - Array of {value, label} objects.
     * @param {string} currentValue - Currently selected value.
     * @returns {Element} The dropdown group element.
     */
    function buildDropdown( id, label, options, currentValue ) {
        var group = TTDom.createElement( 'div', {
            className: 'tt-attribute-group'
        });

        var labelEl = TTDom.createElement( 'label', {
            className: 'tt-attribute-label',
            text: label
        });
        labelEl.setAttribute( 'for', id );

        var select = TTDom.createElement( 'select', {
            id: id,
            className: 'tt-attribute-select'
        });

        // Add empty option
        var emptyOption = TTDom.createElement( 'option', {
            text: '-- Select --'
        });
        emptyOption.value = '';
        select.appendChild( emptyOption );

        // Add options
        options.forEach( function( opt ) {
            var option = TTDom.createElement( 'option', {
                text: opt.label
            });
            option.value = opt.value;
            if ( opt.value === currentValue ) {
                option.selected = true;
            }
            select.appendChild( option );
        });

        group.appendChild( labelEl );
        group.appendChild( select );
        return group;
    }

    /**
     * Build a read-only field display.
     * @param {string} label - Label text.
     * @param {string} value - Display value.
     * @returns {Element} The field group element.
     */
    function buildReadOnlyField( label, value ) {
        var group = TTDom.createElement( 'div', {
            className: 'tt-attribute-group'
        });

        var labelEl = TTDom.createElement( 'span', {
            className: 'tt-attribute-label',
            text: label
        });

        var valueEl = TTDom.createElement( 'span', {
            className: 'tt-attribute-value',
            text: value || '—'
        });

        group.appendChild( labelEl );
        group.appendChild( valueEl );
        return group;
    }

    /**
     * Build category dropdown options from categories hierarchy.
     * @param {Array} categories - Array of category objects with subcategories.
     * @returns {Array} Flattened array of {value, label} options.
     */
    function buildCategoryOptions( categories ) {
        var options = [];
        categories.forEach( function( category ) {
            category.subcategories.forEach( function( sub ) {
                options.push({
                    value: sub.slug,
                    label: category.name + ' — ' + sub.name
                });
            });
        });
        return options;
    }

    /**
     * Look up display label for an enum value.
     * @param {Array} enumList - Array of {value, label} objects.
     * @param {string} value - Value to look up.
     * @returns {string|null} Label or null if not found.
     */
    function getLabelForValue( enumList, value ) {
        if ( !value || !enumList ) {
            return null;
        }
        var item = enumList.find( function( e ) {
            return e.value === value;
        });
        return item ? item.label : null;
    }

    /**
     * Find subcategory label from categories hierarchy.
     * @param {Array} categories - Array of category objects with subcategories.
     * @param {string} subcategorySlug - Subcategory slug to find.
     * @returns {string|null} "Category — Subcategory" label or null.
     */
    function getSubcategoryLabel( categories, subcategorySlug ) {
        if ( !subcategorySlug || !categories ) {
            return null;
        }
        for ( var i = 0; i < categories.length; i++ ) {
            var category = categories[i];
            for ( var j = 0; j < category.subcategories.length; j++ ) {
                var sub = category.subcategories[j];
                if ( sub.slug === subcategorySlug ) {
                    return category.name + ' — ' + sub.name;
                }
            }
        }
        return null;
    }

    /**
     * Send location update to server via background.
     * @param {string} locationUuid - Location UUID.
     * @param {Object} updates - Fields to update.
     */
    function updateLocationOnServer( locationUuid, updates ) {
        chrome.runtime.sendMessage({
            type: TT.MESSAGE.TYPE_UPDATE_LOCATION,
            data: {
                uuid: locationUuid,
                updates: updates
            }
        }, function( response ) {
            if ( chrome.runtime.lastError ) {
                console.error( '[TT GMM] Update location failed:', chrome.runtime.lastError.message );
                return;
            }
            if ( response && response.success ) {
                console.log( '[TT GMM] Location updated on server' );
            } else {
                console.error( '[TT GMM] Update location failed:', response && response.error );
            }
        });
    }

    /**
     * Intercept GMM save button to capture custom attribute values.
     * @param {Element} dialogNode - The dialog element.
     * @param {Object} location - Location object with uuid.
     */
    function interceptSaveButton( dialogNode, location ) {
        var saveButton = dialogNode.querySelector( TTGmmAdapter.selectors.EDIT_SAVE_BUTTON );
        if ( !saveButton || saveButton.hasAttribute( TT_INTERCEPTED_ATTR ) ) {
            return;
        }
        saveButton.setAttribute( TT_INTERCEPTED_ATTR, 'true' );

        saveButton.addEventListener( 'click', function( event ) {
            var container = document.getElementById( TT_CUSTOM_ATTRS_CONTAINER_ID );
            if ( !container ) {
                return; // Let native save proceed
            }

            var categorySelect = container.querySelector( '#tt-attr-category' );
            var desirabilitySelect = container.querySelector( '#tt-attr-desirability' );
            var advancedBookingSelect = container.querySelector( '#tt-attr-advanced-booking' );

            var updates = {
                subcategory_slug: categorySelect ? ( categorySelect.value || null ) : null,
                desirability: desirabilitySelect ? ( desirabilitySelect.value || null ) : null,
                advanced_booking: advancedBookingSelect ? ( advancedBookingSelect.value || null ) : null
            };

            updateLocationOnServer( location.uuid, updates );
            // Don't prevent default - let GMM save proceed
        }, true ); // Capture phase to run before GMM's handler
    }

    /**
     * Add custom attribute UI to location details.
     * @param {Element} dialogNode - The dialog element.
     * @param {Object} location - Location from server.
     * @param {Object} config - Client config with categories and enum types.
     * @param {boolean} isEditMode - Whether in edit mode.
     */
    function addCustomAttributeUI( dialogNode, location, config, isEditMode ) {
        // Remove any existing custom attributes container
        var existing = document.getElementById( TT_CUSTOM_ATTRS_CONTAINER_ID );
        if ( existing ) {
            existing.remove();
        }

        // Find title div to insert after
        var titleDiv = dialogNode.querySelector( TTGmmAdapter.selectors.TITLE_DIV );
        if ( !titleDiv ) {
            console.warn( '[TT GMM] Could not find title div for custom attributes' );
            return;
        }

        // Get notes container for hiding in edit mode
        var notesContainer = dialogNode.querySelector( TTGmmAdapter.selectors.NOTES_CONTAINER );

        // Create container
        var container = TTDom.createElement( 'div', {
            id: TT_CUSTOM_ATTRS_CONTAINER_ID,
            className: 'tt-custom-attrs'
        });

        var categories = config.location_categories || [];
        var desirabilityTypes = config.desirability_type || [];
        var advancedBookingTypes = config.advanced_booking_type || [];

        if ( isEditMode ) {
            // Edit mode: show dropdowns, hide description
            if ( notesContainer ) {
                notesContainer.style.display = 'none';
            }

            // Category dropdown
            var categoryOptions = buildCategoryOptions( categories );
            var categoryDropdown = buildDropdown(
                'tt-attr-category',
                'Category',
                categoryOptions,
                location.subcategory_slug
            );
            container.appendChild( categoryDropdown );

            // Desirability dropdown
            var desirabilityDropdown = buildDropdown(
                'tt-attr-desirability',
                'Desirability',
                desirabilityTypes,
                location.desirability
            );
            container.appendChild( desirabilityDropdown );

            // Advanced Booking dropdown
            var advancedBookingDropdown = buildDropdown(
                'tt-attr-advanced-booking',
                'Advanced Booking',
                advancedBookingTypes,
                location.advanced_booking
            );
            container.appendChild( advancedBookingDropdown );

            // Set up save button interception
            interceptSaveButton( dialogNode, location );

        } else {
            // Read-only mode: show values, keep description visible
            if ( notesContainer ) {
                notesContainer.style.display = '';
            }

            // Category
            var categoryLabel = getSubcategoryLabel( categories, location.subcategory_slug );
            if ( categoryLabel ) {
                container.appendChild( buildReadOnlyField( 'Category', categoryLabel ) );
            }

            // Desirability
            var desirabilityLabel = getLabelForValue( desirabilityTypes, location.desirability );
            if ( desirabilityLabel ) {
                container.appendChild( buildReadOnlyField( 'Desirability', desirabilityLabel ) );
            }

            // Advanced Booking
            var advancedBookingLabel = getLabelForValue( advancedBookingTypes, location.advanced_booking );
            if ( advancedBookingLabel ) {
                container.appendChild( buildReadOnlyField( 'Advanced Booking', advancedBookingLabel ) );
            }

            // If no attributes to show, don't add empty container
            if ( container.children.length === 0 ) {
                return;
            }
        }

        // Insert after title div
        titleDiv.parentNode.insertBefore( container, titleDiv.nextSibling );
    }

    // =========================================================================
    // Server Communication
    // =========================================================================

    /**
     * Show error notification banner in GMM page.
     * Auto-dismisses after 5 seconds.
     * @param {string} message - Error message to display.
     */
    function showErrorNotification( message ) {
        // Remove any existing notification
        var existing = document.querySelector( '.tt-error-notification' );
        if ( existing ) {
            existing.remove();
        }

        var notification = TTDom.createElement( 'div', {
            className: 'tt-error-notification',
            text: message
        });

        // Style inline to ensure it displays correctly in GMM
        notification.style.cssText = [
            'position: fixed',
            'top: 20px',
            'left: 50%',
            'transform: translateX(-50%)',
            'background: #d93025',
            'color: white',
            'padding: 12px 24px',
            'border-radius: 8px',
            'font-family: "Google Sans", Roboto, Arial, sans-serif',
            'font-size: 14px',
            'box-shadow: 0 4px 12px rgba(0,0,0,0.3)',
            'z-index: 10000',
            'cursor: pointer'
        ].join( ';' );

        notification.addEventListener( 'click', function() {
            notification.remove();
        });

        document.body.appendChild( notification );

        // Auto-dismiss after 5 seconds
        setTimeout( function() {
            if ( notification.parentNode ) {
                notification.remove();
            }
        }, 5000 );
    }

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
                    var errorMsg = ( response && response.data && response.data.error )
                        ? response.data.error
                        : 'No response';
                    reject( new Error( errorMsg ) );
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
                } else if ( response && response.data && response.data.notFound ) {
                    resolve( null );
                } else {
                    var errorMsg = ( response && response.data && response.data.error )
                        ? response.data.error
                        : 'No response';
                    reject( new Error( errorMsg ) );
                }
            });
        });
    }

    // =========================================================================
    // Start
    // =========================================================================

    initialize();

})();
