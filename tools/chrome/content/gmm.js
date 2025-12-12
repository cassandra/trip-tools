/*
 * Trip Tools Chrome Extension - GMM Content Script
 * Injected into Google My Maps pages.
 * Uses TTGmmAdapter for DOM operations, service worker for categories.
 * Depends on: constants.js, storage.js, dom.js, text-utils.js,
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

        // Dispatch page load actions (auto-sync check, etc.)
        dispatchPageLoad();
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
    // Page Load Dispatcher
    // =========================================================================

    /**
     * Wait for GMM to be ready (layer pane populated).
     * @returns {Promise<void>}
     */
    function waitForGmmReady() {
        return TTDom.waitForElement( TTGmmAdapter.selectors.LAYER_PANE, { timeout: 10000 } )
            .then( function() {
                // Additional wait for layers to populate
                return TTDom.wait( 1000 );
            });
    }

    /**
     * Dispatch page load actions.
     * Triggers sync check which is self-contained (determines linkage internally).
     */
    function dispatchPageLoad() {
        waitForGmmReady()
            .then( function() {
                console.log( '[TT GMM] Page load - triggering sync check' );
                // TTGmmSync.onPageLoad() is self-contained:
                // - Gets map ID from URL
                // - Checks linkage via service worker
                // - Runs sync if linked, skips if not
                if ( typeof TTGmmSync !== 'undefined' && TTGmmSync.onPageLoad ) {
                    TTGmmSync.onPageLoad();
                }
            } )
            .catch( function( error ) {
                console.error( '[TT GMM] Page load dispatch failed:', error );
            } );
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
                    data: TTGmmAdapter.getMapInfo()
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
     * Decorates with category buttons, or delegates to sync module for FIX mode.
     * Only decorates if map is linked to a trip.
     * @param {Element} dialogNode - The dialog element.
     */
    function handleAddToMapDialog( dialogNode ) {
        var currentMode = TTOperationMode.getMode();

        // FIX mode: delegate to sync module (still requires linkage, handled in sync module)
        if ( currentMode === TTOperationMode.Mode.GMM_SYNC_FIX ) {
            TTGmmSync.decorateFixModeDialog( dialogNode );
            return;
        }

        // Other operation modes: skip decoration
        if ( TTOperationMode.suppressGmmIntercepts() ) {
            return;
        }

        // Check if already decorated
        if ( dialogNode.getAttribute( TT_DECORATED_ATTR ) ) {
            return;
        }
        dialogNode.setAttribute( TT_DECORATED_ATTR, 'true' );

        // Check if map is linked to a trip before decorating
        TTGmmAdapter.isGmmMapLinkedToTrip()
            .then( function( result ) {
                if ( !result.isLinked ) {
                    console.log( '[TT GMM] Map not linked - skipping add-to-map decoration' );
                    return;
                }

                // Get categories from service worker
                return getLocationCategories()
                    .then( function( categories ) {
                        if ( categories && categories.length > 0 ) {
                            decorateAddToMapDialog( dialogNode, categories );
                        } else {
                            console.log( '[TT GMM] No categories available' );
                        }
                    } );
            } )
            .catch( function( error ) {
                console.error( '[TT GMM] Failed to decorate add-to-map:', error );
            } );
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

        if ( category.subcategories && category.subcategories.length > 1 ) {
            // Multiple subcategories - show picker
            showSubcategoryPicker( dialogNode, category );
        } else if ( category.subcategories && category.subcategories.length === 1 ) {
            // Singleton subcategory - auto-select
            addLocationWithCategory( dialogNode, category, category.subcategories[0] );
        } else {
            // No subcategories (shouldn't happen with proper seed data)
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
     * Extracts contact info from "Details from Google Maps" section before adding.
     * @param {Element} dialogNode - The dialog element.
     * @param {Object} category - Category from server.
     * @param {Object|null} subcategory - Subcategory or null.
     */
    function addLocationWithCategory( dialogNode, category, subcategory ) {
        var colorRgb = subcategory ? subcategory.color_code : category.color_code;
        var iconCode = subcategory ? subcategory.icon_code : category.icon_code;
        var locationName = subcategory ? subcategory.name : category.name;

        // Enter operating mode to prevent user interaction during DOM manipulation
        TTOperationMode.enter( TTOperationMode.Mode.GMM_USER_ADD, {
            message: "Adding as '" + locationName + "'..."
        });

        // Extract contact info before dialog closes (best effort)
        var contactInfo = TTGmmAdapter.getContactInfo( dialogNode );
        if ( contactInfo.length > 0 ) {
            console.log( '[TT GMM] Extracted contact info:', contactInfo );
        }

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

            // Include contact info if extracted
            if ( contactInfo.length > 0 ) {
                locationData.contact_info = contactInfo;
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
        })
        .finally( function() {
            TTOperationMode.exit();
        });
    }

    // =========================================================================
    // Location Details Dialog
    // =========================================================================

    /**
     * Handle location details dialog opening.
     * Only decorates if map is linked to a trip.
     * @param {Element} dialogNode - The dialog element.
     */
    function handleLocationDetailsDialog( dialogNode ) {
        // Skip decoration during operation modes that suppress intercepts
        if ( TTOperationMode.suppressGmmIntercepts() ) {
            return;
        }

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

        // Only decorate if map is linked to a trip
        TTGmmAdapter.isGmmMapLinkedToTrip()
            .then( function( result ) {
                if ( !result.isLinked ) {
                    console.log( '[TT GMM] Skipping location details decoration - map not linked' );
                    return;
                }

                // Look up location from server
                return getLocationFromServer( gmmId )
                    .then( function( location ) {
                        if ( location ) {
                            decorateLocationDetails( dialogNode, location );
                        }
                    });
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

                // Intercept delete button (only needs to be done once)
                interceptDeleteButton( dialogNode, location );

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

    // =========================================================================
    // Location Notes UI Helpers
    // =========================================================================

    var TT_NOTES_CONTAINER_ID = 'tt-notes-container';

    /**
     * Extract hostname from URL for compact display.
     * @param {string} url - Full URL.
     * @returns {string} Hostname or original URL if parsing fails.
     */
    function getHostnameFromUrl( url ) {
        if ( !url ) {
            return '';
        }
        try {
            var urlObj = new URL( url );
            return urlObj.hostname;
        } catch ( e ) {
            return url;
        }
    }

    /**
     * Set up auto-grow behavior on a textarea.
     * @param {HTMLTextAreaElement} textarea - The textarea element.
     */
    function setupTextareaAutoGrow( textarea ) {
        function adjustHeight() {
            textarea.style.height = 'auto';
            textarea.style.height = textarea.scrollHeight + 'px';
        }
        textarea.addEventListener( 'input', adjustHeight );
        // Initial adjustment
        adjustHeight();
    }

    /**
     * Prevent Enter key from submitting form on single-line inputs.
     * @param {HTMLInputElement} input - The input element.
     */
    function preventEnterSubmit( input ) {
        input.addEventListener( 'keydown', function( e ) {
            if ( e.key === 'Enter' ) {
                e.preventDefault();
            }
        });
    }

    /**
     * Build a read-only note card for view mode.
     * @param {Object} note - Note object with text, source_label, source_url.
     * @returns {Element} The note card element.
     */
    function buildReadOnlyNoteCard( note ) {
        var card = TTDom.createElement( 'div', {
            className: 'tt-note-card'
        });

        // Note text
        var textEl = TTDom.createElement( 'div', {
            className: 'tt-note-text-display',
            text: note.text || ''
        });
        card.appendChild( textEl );

        // Source line (only if source_label or source_url present)
        if ( note.source_label || note.source_url ) {
            var sourceEl = TTDom.createElement( 'div', {
                className: 'tt-note-source-display'
            });

            var sourceText = '— ';
            if ( note.source_label && note.source_url ) {
                sourceText += note.source_label + ' · ';
                var link = TTDom.createElement( 'a', {
                    text: getHostnameFromUrl( note.source_url )
                });
                link.href = note.source_url;
                link.target = '_blank';
                link.rel = 'noopener noreferrer';
                sourceEl.appendChild( document.createTextNode( sourceText ) );
                sourceEl.appendChild( link );
                sourceEl.appendChild( document.createTextNode( ' ↗' ) );
            } else if ( note.source_label ) {
                sourceEl.textContent = sourceText + note.source_label;
            } else if ( note.source_url ) {
                var link = TTDom.createElement( 'a', {
                    text: getHostnameFromUrl( note.source_url )
                });
                link.href = note.source_url;
                link.target = '_blank';
                link.rel = 'noopener noreferrer';
                sourceEl.appendChild( document.createTextNode( sourceText ) );
                sourceEl.appendChild( link );
                sourceEl.appendChild( document.createTextNode( ' ↗' ) );
            }
            card.appendChild( sourceEl );
        }

        return card;
    }

    // =========================================================================
    // Notes Radio Selector UI (Edit Mode)
    // =========================================================================

    /**
     * Build truncated preview text for note radio label.
     * @param {Object} note - Note object with text, source_label.
     * @returns {string} Preview text for display.
     */
    function buildNotePreview( note ) {
        var preview = '';

        // Prepend source label if exists
        if ( note.source_label ) {
            preview = note.source_label + ': ';
        }

        // Get first line, truncate to ~40 chars
        var text = ( note.text || '' ).split( '\n' )[0];
        if ( text.length > 40 ) {
            text = text.substring( 0, 37 ) + '...';
        }
        preview += text;

        return preview || '(empty note)';
    }

    var TT_DESCRIPTION_OWNER_ATTR = 'data-tt-note-owner';

    /**
     * Handle note radio selection change.
     * Saves current description text to its owner, loads newly selected note.
     * @param {Element} container - The notes selector container.
     * @param {number} noteIndex - Index of note to select (-1 for New Note).
     * @param {Element} gmmDescriptionValue - GMM's description contenteditable element.
     */
    function selectNoteRadio( container, noteIndex, gmmDescriptionValue ) {
        // Save current description text to its owner (the note whose content is currently displayed)
        var ownerAttr = gmmDescriptionValue.getAttribute( TT_DESCRIPTION_OWNER_ATTR );
        if ( ownerAttr !== null ) {
            var ownerIndex = parseInt( ownerAttr, 10 );
            var ownerItem = container.querySelector( '[data-tt-note-index="' + ownerIndex + '"]' );
            if ( ownerItem ) {
                var currentText = ( gmmDescriptionValue.innerText || '' ).trim();
                ownerItem.setAttribute( 'data-tt-note-text', currentText );
            }
        }

        // Find and select new item
        var newItem = container.querySelector( '[data-tt-note-index="' + noteIndex + '"]' );
        if ( newItem ) {
            var radio = newItem.querySelector( 'input[type="radio"]' );
            radio.checked = true;

            // Load selected note's stored text into description
            var noteText = newItem.getAttribute( 'data-tt-note-text' ) || '';
            gmmDescriptionValue.innerHTML = noteText.replace( /\n/g, '<br>' );

            // Update description owner to new note
            gmmDescriptionValue.setAttribute( TT_DESCRIPTION_OWNER_ATTR, String( noteIndex ) );

            gmmDescriptionValue.focus();
        }
    }

    /**
     * Handle delete button click on a note item.
     * @param {Element} item - The radio item element to delete.
     * @param {Element} container - The notes selector container.
     * @param {Element} gmmDescriptionValue - GMM's description contenteditable element.
     */
    function deleteNoteItem( item, container, gmmDescriptionValue ) {
        var wasSelected = item.querySelector( 'input:checked' ) !== null;

        // Remove item from DOM
        item.remove();

        // If was selected, switch to New Note
        if ( wasSelected ) {
            selectNoteRadio( container, -1, gmmDescriptionValue );
        }
    }

    /**
     * Build a radio item for an existing note.
     * @param {Object} note - Note object with text, source_label, source_url.
     * @param {number} index - Index of the note in original array.
     * @param {Element} gmmDescriptionValue - GMM's description contenteditable element.
     * @param {Element} container - The notes selector container.
     * @returns {Element} The radio item element.
     */
    function buildNoteRadioItem( note, index, gmmDescriptionValue, container ) {
        var item = TTDom.createElement( 'div', {
            className: 'tt-note-radio-item'
        });
        item.setAttribute( 'data-tt-note-index', index );
        item.setAttribute( 'data-tt-note-text', note.text || '' );

        // Wrap radio and label in <label> for click-to-select behavior
        var labelWrapper = TTDom.createElement( 'label', {
            className: 'tt-note-radio-wrapper'
        });

        // Radio input
        var radio = TTDom.createElement( 'input', {
            className: 'tt-note-radio'
        });
        radio.type = 'radio';
        radio.name = 'tt-note-selector';
        radio.addEventListener( 'change', function() {
            if ( radio.checked ) {
                selectNoteRadio( container, index, gmmDescriptionValue );
            }
        });
        labelWrapper.appendChild( radio );

        // Label text with truncated preview
        var labelText = TTDom.createElement( 'span', {
            className: 'tt-note-radio-label',
            text: buildNotePreview( note )
        });
        labelWrapper.appendChild( labelText );

        item.appendChild( labelWrapper );

        // Delete button
        var deleteBtn = TTDom.createElement( 'button', {
            className: 'tt-note-delete',
            text: '×'
        });
        deleteBtn.type = 'button';
        deleteBtn.title = 'Delete note';
        deleteBtn.addEventListener( 'click', function( e ) {
            e.preventDefault();
            deleteNoteItem( item, container, gmmDescriptionValue );
        });
        item.appendChild( deleteBtn );

        return item;
    }

    /**
     * Build the "New Note" radio item.
     * @param {Element} gmmDescriptionValue - GMM's description contenteditable element.
     * @param {Element} container - The notes selector container.
     * @returns {Element} The radio item element.
     */
    function buildNewNoteRadioItem( gmmDescriptionValue, container ) {
        var item = TTDom.createElement( 'div', {
            className: 'tt-note-radio-item tt-note-new'
        });
        item.setAttribute( 'data-tt-note-index', '-1' );
        item.setAttribute( 'data-tt-note-text', '' );

        // Wrap radio and label in <label> for click-to-select behavior
        var labelWrapper = TTDom.createElement( 'label', {
            className: 'tt-note-radio-wrapper'
        });

        // Radio input
        var radio = TTDom.createElement( 'input', {
            className: 'tt-note-radio'
        });
        radio.type = 'radio';
        radio.name = 'tt-note-selector';
        radio.addEventListener( 'change', function() {
            if ( radio.checked ) {
                selectNoteRadio( container, -1, gmmDescriptionValue );
            }
        });
        labelWrapper.appendChild( radio );

        // Label text
        var labelText = TTDom.createElement( 'span', {
            className: 'tt-note-radio-label',
            text: 'New Note'
        });
        labelWrapper.appendChild( labelText );

        item.appendChild( labelWrapper );

        // No delete button for New Note

        return item;
    }

    /**
     * Build the note selector UI for edit mode.
     * @param {Object} location - Location from server with location_notes.
     * @param {Element} gmmDescriptionValue - GMM's description contenteditable element.
     * @returns {Element} The notes selector container element.
     */
    function buildNoteSelectorUI( location, gmmDescriptionValue ) {
        var container = TTDom.createElement( 'div', {
            id: TT_NOTES_CONTAINER_ID,
            className: 'tt-note-selector'
        });

        // Store original notes for source_label/source_url preservation on save
        var notes = location.location_notes || [];
        container.setAttribute( 'data-tt-original-notes', JSON.stringify( notes ) );

        // Build radio items for existing notes
        notes.forEach( function( note, index ) {
            var item = buildNoteRadioItem( note, index, gmmDescriptionValue, container );
            container.appendChild( item );
        });

        // Build "New Note" radio item (always last, always exists)
        var newNoteItem = buildNewNoteRadioItem( gmmDescriptionValue, container );
        container.appendChild( newNoteItem );

        // Select "New Note" by default
        var newNoteRadio = newNoteItem.querySelector( 'input[type="radio"]' );
        newNoteRadio.checked = true;

        // Set description owner to "New Note" (-1)
        // Description already cleared by caller
        gmmDescriptionValue.setAttribute( TT_DESCRIPTION_OWNER_ATTR, '-1' );

        return container;
    }

    /**
     * Flatten notes array to text for GMM description field.
     * Format: Note text, then source line, then separator between notes.
     * @param {Array} notes - Array of note objects.
     * @returns {string} Flattened text.
     */
    function flattenNotesToDescription( notes ) {
        var parts = [];
        notes.forEach( function( note ) {
            var text = note.text || '';
            if ( !text.trim() ) {
                return;
            }

            var notePart = text;

            // Add source line if present
            if ( note.source_label || note.source_url ) {
                notePart += '\n— ';
                if ( note.source_label && note.source_url ) {
                    notePart += note.source_label + ' (' + note.source_url + ')';
                } else if ( note.source_label ) {
                    notePart += note.source_label;
                } else {
                    notePart += note.source_url;
                }
            }

            parts.push( notePart );
        });
        return parts.join( '\n-----\n' );
    }

    /**
     * Build the notes UI section for view mode (read-only).
     * @param {Object} location - Location from server with location_notes.
     * @returns {Element} The notes container element.
     */
    function buildNotesUI( location ) {
        var container = TTDom.createElement( 'div', {
            id: TT_NOTES_CONTAINER_ID,
            className: 'tt-notes-container'
        });

        var notes = location.location_notes || [];

        // View mode: show read-only cards
        notes.forEach( function( note ) {
            container.appendChild( buildReadOnlyNoteCard( note ) );
        });

        return container;
    }

    /**
     * Collect final notes array from radio selector DOM state.
     * @param {Element} gmmDescriptionValue - GMM's description contenteditable element.
     * @param {Element} notesContainer - The notes selector container (may be null).
     * @returns {Array} Final notes array to save.
     */
    function collectNoteChanges( gmmDescriptionValue, notesContainer ) {
        var finalNotes = [];

        // If no notes container, just handle description as single note
        if ( !notesContainer ) {
            var text = ( gmmDescriptionValue.innerText || '' ).trim();
            if ( text ) {
                finalNotes.push({ text: text, source_label: '', source_url: '' });
            }
            return finalNotes;
        }

        // Save current description to its owner (the note whose content is displayed)
        var ownerAttr = gmmDescriptionValue.getAttribute( TT_DESCRIPTION_OWNER_ATTR );
        if ( ownerAttr !== null ) {
            var ownerIndex = parseInt( ownerAttr, 10 );
            var ownerItem = notesContainer.querySelector( '[data-tt-note-index="' + ownerIndex + '"]' );
            if ( ownerItem ) {
                var currentText = ( gmmDescriptionValue.innerText || '' ).trim();
                ownerItem.setAttribute( 'data-tt-note-text', currentText );
            }
        }

        // Get original notes for source_label/source_url preservation
        var originalNotes = [];
        try {
            originalNotes = JSON.parse( notesContainer.getAttribute( 'data-tt-original-notes' ) || '[]' );
        } catch ( e ) {
            // Ignore parse errors
        }

        // Iterate all radio items, collect non-empty notes
        var items = notesContainer.querySelectorAll( '.tt-note-radio-item' );
        items.forEach( function( item ) {
            var text = ( item.getAttribute( 'data-tt-note-text' ) || '' ).trim();
            if ( !text ) {
                return; // Skip empty notes
            }

            var index = parseInt( item.getAttribute( 'data-tt-note-index' ), 10 );

            if ( index >= 0 && originalNotes[index] ) {
                // Existing note - preserve source info, update text
                finalNotes.push({
                    text: text,
                    source_label: originalNotes[index].source_label || '',
                    source_url: originalNotes[index].source_url || ''
                });
            } else {
                // New note (index -1)
                finalNotes.push({ text: text, source_label: '', source_url: '' });
            }
        });

        return finalNotes;
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
                updates: updates,
                gmm_map_id: TTGmmAdapter.getMapInfo().mapId
            }
        }, function( response ) {
            if ( chrome.runtime.lastError ) {
                console.error( '[TT GMM] Update location failed:', chrome.runtime.lastError.message );
                showErrorNotification( 'Changes not saved to server. Try editing again later.' );
                return;
            }
            if ( response && response.success ) {
                console.log( '[TT GMM] Location updated on server' );
            } else {
                console.error( '[TT GMM] Update location failed:', response && response.error );
                showErrorNotification( 'Changes not saved to server. Try editing again later.' );
            }
        });
    }

    /**
     * Send location delete to server via background.
     * @param {string} locationUuid - Location UUID.
     * @param {string} gmmId - GMM feature ID for metadata cleanup.
     * @returns {Promise<boolean>} Resolves to true on success, false on failure.
     */
    function deleteLocationOnServer( locationUuid, gmmId ) {
        return new Promise( function( resolve ) {
            chrome.runtime.sendMessage({
                type: TT.MESSAGE.TYPE_DELETE_LOCATION,
                data: {
                    uuid: locationUuid,
                    gmmId: gmmId,
                    gmm_map_id: TTGmmAdapter.getMapInfo().mapId
                }
            }, function( response ) {
                if ( chrome.runtime.lastError ) {
                    console.error( '[TT GMM] Delete location failed:', chrome.runtime.lastError.message );
                    showErrorNotification( 'Could not delete location. Try again later.' );
                    resolve( false );
                    return;
                }
                if ( response && response.success ) {
                    console.log( '[TT GMM] Location deleted from server' );
                    resolve( true );
                } else {
                    console.error( '[TT GMM] Delete location failed:', response && response.error );
                    showErrorNotification( 'Could not delete location. Try again later.' );
                    resolve( false );
                }
            });
        });
    }

    /**
     * Intercept GMM save button to capture custom attribute values and notes.
     * @param {Element} dialogNode - The dialog element.
     * @param {Object} location - Location object with uuid and location_notes.
     * @param {Element} gmmDescriptionValue - GMM's description contenteditable element.
     */
    function interceptSaveButton( dialogNode, location, gmmDescriptionValue ) {
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

            // Collect notes from radio selector state
            var notesContainer = document.getElementById( TT_NOTES_CONTAINER_ID );
            var locationNotes = [];

            if ( gmmDescriptionValue ) {
                locationNotes = collectNoteChanges( gmmDescriptionValue, notesContainer );
            }

            var updates = {
                subcategory_slug: categorySelect ? ( categorySelect.value || null ) : null,
                desirability: desirabilitySelect ? ( desirabilitySelect.value || null ) : null,
                advanced_booking: advancedBookingSelect ? ( advancedBookingSelect.value || null ) : null,
                location_notes: locationNotes
            };

            // Write flattened notes to GMM description for native storage sync
            // Convert \n to <br> for contenteditable
            if ( gmmDescriptionValue && locationNotes.length > 0 ) {
                var flattenedDescription = flattenNotesToDescription( locationNotes );
                gmmDescriptionValue.innerHTML = flattenedDescription.replace( /\n/g, '<br>' );
            }

            updateLocationOnServer( location.uuid, updates );
            // Don't prevent default - let GMM save proceed
        }, true ); // Capture phase to run before GMM's handler
    }

    /**
     * Intercept GMM delete button to delete location from server.
     * Clones the button so we can control when GMM's delete happens.
     * @param {Element} dialogNode - The dialog element.
     * @param {Object} location - Location object with uuid and gmm_id.
     */
    function interceptDeleteButton( dialogNode, location ) {
        var originalButton = dialogNode.querySelector( TTGmmAdapter.selectors.DELETE_BUTTON );
        if ( !originalButton || originalButton.hasAttribute( TT_INTERCEPTED_ATTR ) ) {
            return;
        }
        originalButton.setAttribute( TT_INTERCEPTED_ATTR, 'true' );

        // Clone the button (without our intercept attribute)
        var clonedButton = originalButton.cloneNode( true );
        clonedButton.removeAttribute( TT_INTERCEPTED_ATTR );

        // Hide original, insert clone in its place
        originalButton.style.display = 'none';
        originalButton.parentNode.insertBefore( clonedButton, originalButton );

        // Our clone handles the click
        clonedButton.addEventListener( 'click', function( event ) {
            event.preventDefault();
            event.stopPropagation();

            console.log( '[TT GMM] Delete button clicked for:', location.uuid );

            deleteLocationOnServer( location.uuid, location.gmm_id )
                .then( function( success ) {
                    if ( success ) {
                        // Server delete succeeded - trigger GMM's delete
                        originalButton.click();
                    }
                    // On failure: error notification already shown, GMM untouched
                });
        });
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

        // Remove any existing notes container
        var existingNotes = document.getElementById( TT_NOTES_CONTAINER_ID );
        if ( existingNotes ) {
            existingNotes.remove();
        }

        // Find title div to insert after (for attribute dropdowns)
        var titleDiv = dialogNode.querySelector( TTGmmAdapter.selectors.TITLE_DIV );
        if ( !titleDiv ) {
            console.warn( '[TT GMM] Could not find title div for custom attributes' );
            return;
        }

        // Get GMM notes container - we'll insert our notes near it
        var gmmNotesContainer = dialogNode.querySelector( TTGmmAdapter.selectors.NOTES_CONTAINER );

        // Get #map-infowindow-content - GMM's keyboard handlers likely check if
        // events originate from within this container
        var gmmContentContainer = dialogNode.querySelector( '#map-infowindow-content' );

        // Create container for attributes (dropdowns go after title)
        var container = TTDom.createElement( 'div', {
            id: TT_CUSTOM_ATTRS_CONTAINER_ID,
            className: 'tt-custom-attrs'
        });

        var categories = config.location_categories || [];
        var desirabilityTypes = config.desirability_type || [];
        var advancedBookingTypes = config.advanced_booking_type || [];

        if ( isEditMode ) {
            // Edit mode: show dropdowns
            // Find GMM's contenteditable description div - we'll embed our notes UI inside it
            // so it inherits GMM's keyboard handler protection
            var gmmDescriptionValue = gmmNotesContainer ?
                gmmNotesContainer.querySelector( '#map-infowindow-attr-description-value' ) : null;

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

            // Insert attribute dropdowns after title
            titleDiv.parentNode.insertBefore( container, titleDiv.nextSibling );

            // Clear GMM description on edit start (we manage notes separately)
            if ( gmmDescriptionValue ) {
                gmmDescriptionValue.innerHTML = '';
            }

            // Build note selector UI for edit mode
            // Always show selector (includes "New Note" option even with no existing notes)
            if ( gmmDescriptionValue ) {
                var notesUI = buildNoteSelectorUI( location, gmmDescriptionValue );
                // Insert before the GMM description so selector appears above edit area
                if ( gmmDescriptionValue.parentNode ) {
                    gmmDescriptionValue.parentNode.insertBefore( notesUI, gmmDescriptionValue );
                } else if ( gmmNotesContainer ) {
                    gmmNotesContainer.insertBefore( notesUI, gmmNotesContainer.firstChild );
                } else {
                    container.appendChild( notesUI );
                }
            }

            // Set up save button interception
            interceptSaveButton( dialogNode, location, gmmDescriptionValue );

        } else {
            // Read-only mode: show values, hide GMM description (we show our notes instead)
            if ( gmmNotesContainer ) {
                gmmNotesContainer.style.display = 'none';
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

            // Add notes section (read-only) - only if there are notes
            var notes = location.location_notes || [];
            if ( notes.length > 0 ) {
                var notesUI = buildNotesUI( location );
                container.appendChild( notesUI );
            }

            // If no attributes and no notes to show, don't add empty container
            if ( container.children.length === 0 ) {
                return;
            }

            // Insert after title div
            titleDiv.parentNode.insertBefore( container, titleDiv.nextSibling );
        }
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
            locationData.gmm_map_id = TTGmmAdapter.getMapInfo().mapId;
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
