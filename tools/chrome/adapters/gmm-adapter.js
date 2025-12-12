/*
 * Trip Tools Chrome Extension - Google My Maps Adapter
 * Handles all GMM DOM manipulation through the adapter pattern.
 * Depends on: dom.js, site-adapter.js, gmm-selectors.js
 */

var TTGmmAdapter = TTSiteAdapter.create({
    name: 'GMM',
    selectors: TTGmmSelectors,
    timing: {
        clickDelayMs: 500,
        elementWaitMs: 3000
    },
    methods: {

        // =====================================================================
        // Initialization
        // =====================================================================

        /**
         * Initialize GMM adapter and set up observers.
         * @param {Object} handlers - Event handlers.
         * @param {Function} handlers.onAddToMapDialog - Called when add-to-map dialog opens.
         * @param {Function} handlers.onLocationDetailsDialog - Called when location details open.
         */
        initialize: function( handlers ) {
            this.handlers = handlers || {};
            this.log( 'Initializing with selector version: ' + this.selectors.VERSION );
            TTDom.configure( this.timing );
            this._setupDialogObserver();
        },

        /**
         * Set up observer for dialog appearances.
         * @private
         */
        _setupDialogObserver: function() {
            var self = this;

            TTDom.observe({
                selector: this.selectors.DIALOG,
                onMatch: function( dialogNode ) {
                    self._handleDialogOpened( dialogNode );
                }
            });
        },

        /**
         * Handle dialog opened event.
         * Determines dialog type and dispatches to appropriate handler.
         * @private
         * @param {Element} dialogNode - The dialog element.
         */
        _handleDialogOpened: function( dialogNode ) {
            // Check for add-to-map dialog
            var addButton = dialogNode.querySelector( this.selectors.ADD_TO_MAP_BUTTON );
            if ( addButton ) {
                this.log( 'Add-to-map dialog detected' );
                if ( this.handlers.onAddToMapDialog ) {
                    this.handlers.onAddToMapDialog( dialogNode );
                }
                return;
            }

            // Check for location details dialog
            var infoContainer = dialogNode.querySelector( this.selectors.INFO_CONTAINER );
            if ( infoContainer ) {
                this.log( 'Location details dialog detected' );
                if ( this.handlers.onLocationDetailsDialog ) {
                    this.handlers.onLocationDetailsDialog( dialogNode );
                }
                return;
            }
        },

        // =====================================================================
        // Map Context
        // =====================================================================

        /**
         * Get map info from current page URL.
         * @returns {Object} { mapId, url }
         */
        getMapInfo: function() {
            var url = new URL( window.location.href );
            var mapId = url.searchParams.get( 'mid' );

            return {
                mapId: mapId,
                url: window.location.href
            };
        },

        /**
         * Check if current GMM map is linked to any trip.
         * Uses GMM map index in service worker (3-layer cache).
         * @returns {Promise<{isLinked: boolean, tripUuid: string|null}>}
         */
        isGmmMapLinkedToTrip: function() {
            var mapId = this.getMapInfo().mapId;
            if ( !mapId ) {
                return Promise.resolve( { isLinked: false, tripUuid: null } );
            }

            return new Promise( function( resolve ) {
                chrome.runtime.sendMessage( {
                    type: TT.MESSAGE.TYPE_IS_GMM_MAP_LINKED,
                    data: { gmm_map_id: mapId }
                }, function( response ) {
                    if ( chrome.runtime.lastError || !response || !response.success ) {
                        resolve( { isLinked: false, tripUuid: null } );
                        return;
                    }
                    resolve( {
                        isLinked: response.data.isLinked,
                        tripUuid: response.data.tripUuid
                    } );
                } );
            } );
        },

        // =====================================================================
        // Layer Operations
        // =====================================================================

        /**
         * Get all layers from the map.
         * @returns {Array<Object>} Array of { id, title, node }.
         */
        getLayers: function() {
            var self = this;
            var layerNodes = this.getAllElements( 'LAYER_ITEM' );

            return layerNodes.map( function( node ) {
                var headerNode = node.childNodes[0];
                var titleNode = headerNode ? headerNode.childNodes[1] : null;

                return {
                    id: node.getAttribute( self.selectors.ATTR_LAYER_ID ),
                    title: titleNode ? titleNode.textContent : '',
                    node: node
                };
            });
        },

        /**
         * Find layer by title.
         * @param {string} title - Layer title.
         * @returns {Object|null} Layer info or null.
         */
        findLayerByTitle: function( title ) {
            var layers = this.getLayers();
            return layers.find( function( layer ) {
                return layer.title === title;
            }) || null;
        },

        /**
         * Select a layer (make it active for adding locations).
         * @param {Object} layer - Layer info from getLayers().
         * @returns {Promise<void>}
         */
        selectLayer: function( layer ) {
            var headerNode = layer.node.firstChild;
            var titleNode = headerNode.childNodes[1];
            return TTDom.clickRealistic( titleNode );
        },

        /**
         * Create a new layer with given title.
         * @param {string} title - Layer title.
         * @returns {Promise<Object>} New layer info.
         */
        createLayer: function( title ) {
            var self = this;

            var addButton = this.getElement( 'ADD_LAYER_BUTTON' );
            if ( !addButton ) {
                return Promise.reject( new Error( 'Add layer button not found' ) );
            }

            return TTDom.clickRealistic( addButton )
                .then( function() {
                    return TTDom.wait( 2000 );
                })
                .then( function() {
                    // Get the newly added layer (last one)
                    var layers = self.getLayers();
                    var newLayer = layers[layers.length - 1];
                    return self._renameLayer( newLayer, title );
                });
        },

        /**
         * Get or create layer by title.
         * If an empty "Untitled layer" exists, repurposes it instead of creating new.
         * @param {string} title - Layer title.
         * @returns {Promise<Object>} Layer info.
         */
        getOrCreateLayer: function( title ) {
            var self = this;
            var existing = this.findLayerByTitle( title );
            if ( existing ) {
                return Promise.resolve( existing );
            }

            // Check for empty default layer to repurpose
            var untitledLayer = this.findLayerByTitle( TT.CONFIG.GMM_DEFAULT_LAYER_NAME );
            if ( untitledLayer && this._isLayerEmpty( untitledLayer ) ) {
                this.log( 'Repurposing empty default layer as: ' + title );
                return this._renameLayer( untitledLayer, title );
            }

            return this.createLayer( title );
        },

        /**
         * Check if a layer has no location items.
         * @private
         * @param {Object} layer - Layer info from getLayers().
         * @returns {boolean} True if layer is empty.
         */
        _isLayerEmpty: function( layer ) {
            if ( !layer || !layer.node ) {
                return false;
            }
            var locationItems = layer.node.querySelectorAll( this.selectors.LOCATION_ITEM );
            return locationItems.length === 0;
        },

        /**
         * Rename a layer.
         * @private
         * @param {Object} layer - Layer info.
         * @param {string} newTitle - New title.
         * @returns {Promise<Object>} Updated layer info.
         */
        _renameLayer: function( layer, newTitle ) {
            var self = this;
            var headerNode = layer.node.firstChild;
            var menuNode = headerNode.childNodes[2];

            return TTDom.click( menuNode )
                .then( function() {
                    var visibleMenus = self.getVisibleElements( 'LAYER_OPTIONS_MENU' );
                    if ( visibleMenus.length === 0 ) {
                        throw new Error( 'Layer options menu not found' );
                    }

                    // New menus usually added at the end
                    var menu = visibleMenus[visibleMenus.length - 1];

                    // Find rename option
                    var renameItem = Array.from( menu.childNodes ).find( function( item ) {
                        return item.getAttribute( self.selectors.ATTR_LAYER_MENU_ITEM )
                               === self.selectors.VALUE_LAYER_MENU_RENAME;
                    });

                    if ( !renameItem ) {
                        throw new Error( 'Rename option not found in menu' );
                    }

                    return TTDom.clickRealistic( renameItem );
                })
                .then( function() {
                    return self.waitForElement( 'LAYER_UPDATE_DIALOG' );
                })
                .then( function( dialog ) {
                    var input = dialog.querySelector( self.selectors.LAYER_NAME_INPUT );
                    var saveButton = dialog.querySelector( self.selectors.LAYER_SAVE_BUTTON );

                    TTDom.setInputValue( input, newTitle );
                    return TTDom.click( saveButton );
                })
                .then( function() {
                    // Return updated layer info
                    return self.findLayerByTitle( newTitle );
                });
        },

        // =====================================================================
        // Location Operations
        // =====================================================================

        /**
         * Get locations from a layer.
         * @param {Object} layer - Layer info.
         * @returns {Array<Object>} Array of { id, title, iconCode, node }.
         */
        getLocationsInLayer: function( layer ) {
            var self = this;
            var locationNodes = layer.node.querySelectorAll( this.selectors.LOCATION_ITEM );

            return Array.from( locationNodes ).map( function( node ) {
                var iconNode = node.childNodes[0];
                var titleContainer = node.childNodes[1];
                var titleNode = titleContainer ? titleContainer.firstChild : null;

                var iconCode = null;
                if ( iconNode ) {
                    var iconCodeNode = iconNode.querySelector( self.selectors.ICON_ELEMENT );
                    if ( iconCodeNode ) {
                        var iconCodeAttr = iconCodeNode.getAttribute( self.selectors.ATTR_ICON_CODE );
                        // Icon code format is "code-color", we want just the code
                        iconCode = iconCodeAttr ? iconCodeAttr.split( '-' )[0] : null;
                    }
                }

                return {
                    id: node.getAttribute( self.selectors.ATTR_LOCATION_ID ),
                    title: titleNode ? titleNode.textContent : '',
                    iconCode: iconCode,
                    node: node
                };
            });
        },

        /**
         * Find location by title across all layers.
         * @param {string} title - Location title.
         * @returns {Object|null} { location, layer } or null.
         */
        findLocationByTitle: function( title ) {
            var self = this;
            var layers = this.getLayers();

            for ( var i = 0; i < layers.length; i++ ) {
                var layer = layers[i];
                var locations = this.getLocationsInLayer( layer );
                var location = locations.find( function( loc ) {
                    return loc.title === title;
                });
                if ( location ) {
                    return { location: location, layer: layer };
                }
            }
            return null;
        },

        /**
         * Find location by GMM ID across all layers.
         * @param {string} gmmId - GMM location ID (fl_id attribute).
         * @returns {Object|null} { location, layer } or null.
         */
        findLocationById: function( gmmId ) {
            var self = this;
            var layers = this.getLayers();

            for ( var i = 0; i < layers.length; i++ ) {
                var layer = layers[i];
                var locations = this.getLocationsInLayer( layer );
                var location = locations.find( function( loc ) {
                    return loc.id === gmmId;
                });
                if ( location ) {
                    return { location: location, layer: layer };
                }
            }
            return null;
        },

        /**
         * Open a location's info dialog by clicking it in the layer list.
         * @param {string} gmmId - GMM location ID (fl_id attribute).
         * @returns {Promise<Object>} Location info with { id, title, layer, coordinates }.
         */
        openLocationById: function( gmmId ) {
            var self = this;
            var result = this.findLocationById( gmmId );

            if ( !result ) {
                return Promise.reject( new Error( 'Location not found: ' + gmmId ) );
            }

            var location = result.location;
            var layer = result.layer;

            this.log( 'Opening location: ' + location.title );

            // Click the location node to open its info dialog
            return TTDom.clickRealistic( location.node )
                .then( function() {
                    // Wait for info dialog to appear
                    return self.waitForElement( 'INFO_CONTAINER' );
                })
                .then( function() {
                    // Extract coordinates from the info dialog
                    var coordinates = self.getCoordinates();

                    return {
                        id: location.id,
                        title: location.title,
                        iconCode: location.iconCode,
                        layer: layer,
                        coordinates: coordinates
                    };
                });
        },

        /**
         * Delete a location from GMM by clicking it and pressing delete.
         * @param {string} gmmId - GMM location ID (fl_id attribute).
         * @returns {Promise<void>}
         */
        deleteLocationById: function( gmmId ) {
            var self = this;
            var result = this.findLocationById( gmmId );

            if ( !result ) {
                return Promise.reject( new Error( 'Location not found: ' + gmmId ) );
            }

            var location = result.location;

            this.log( 'Deleting location: ' + location.title );

            // Click the location node to open its info dialog
            return TTDom.clickRealistic( location.node )
                .then( function() {
                    // Wait for info dialog and delete button
                    return self.waitForElement( 'DELETE_BUTTON' );
                })
                .then( function( deleteButton ) {
                    self.log( 'Clicking delete button' );
                    return TTDom.clickRealistic( deleteButton );
                })
                .then( function() {
                    // Brief wait for GMM to process the delete
                    return TTDom.wait( 500 );
                });
        },

        /**
         * Click the "Add to map" button in the current dialog.
         * @returns {Promise<void>}
         */
        clickAddToMap: function() {
            var button = this.getElement( 'ADD_TO_MAP_BUTTON' );
            if ( !button ) {
                return Promise.reject( new Error( 'Add to map button not found' ) );
            }
            return TTDom.click( button );
        },

        /**
         * Rename the current location in the info window.
         * Clicks edit, changes the title, and saves.
         * @param {string} newTitle - The new title for the location.
         * @returns {Promise<void>}
         */
        renameCurrentLocation: function( newTitle ) {
            var self = this;

            return this.waitForElement( 'EDIT_BUTTON' )
                .then( function( editButton ) {
                    self.log( 'Clicking edit button to rename location' );
                    return TTDom.clickRealistic( editButton );
                })
                .then( function() {
                    // Wait for edit mode (title becomes contenteditable)
                    return TTDom.wait( 500 );
                })
                .then( function() {
                    var titleDiv = self.getElement( 'TITLE_DIV' );
                    if ( !titleDiv ) {
                        throw new Error( 'Title element not found' );
                    }

                    // Check if in edit mode
                    if ( titleDiv.getAttribute( self.selectors.ATTR_CONTENT_EDITABLE ) !== 'true' ) {
                        throw new Error( 'Title is not editable' );
                    }

                    // Set the new title
                    self.log( 'Setting location title to: ' + newTitle );
                    titleDiv.textContent = newTitle;

                    // Trigger input event for GMM to detect the change
                    titleDiv.dispatchEvent( new Event( 'input', { bubbles: true } ) );

                    return TTDom.wait( 200 );
                })
                .then( function() {
                    // Click save button - need to click the inner div[role="button"]
                    return self.waitForElement( 'EDIT_SAVE_BUTTON' );
                })
                .then( function( saveButton ) {
                    // GMM buttons have inner div[role="button"] that handles clicks
                    var innerButton = saveButton.querySelector( 'div[role="button"]' );
                    var clickTarget = innerButton || saveButton;
                    self.log( 'Saving location rename (clicking ' + ( innerButton ? 'inner button' : 'outer element' ) + ')' );
                    return TTDom.clickRealistic( clickTarget );
                })
                .then( function() {
                    return TTDom.wait( 500 );
                });
        },

        /**
         * Get the current location title from the info window.
         * @returns {string|null}
         */
        getLocationTitle: function() {
            var titleNode = this.getElement( 'TITLE_DIV' );
            return titleNode ? titleNode.textContent : null;
        },

        /**
         * Check if location info window is in edit mode.
         * @returns {boolean}
         */
        isEditMode: function() {
            var titleNode = this.getElement( 'TITLE_DIV' );
            return titleNode &&
                   titleNode.getAttribute( this.selectors.ATTR_CONTENT_EDITABLE ) === 'true';
        },

        /**
         * Get the current location GMM ID from the info window.
         * Looks up the location by title in the layer list.
         * @returns {string|null}
         */
        getCurrentLocationId: function() {
            var title = this.getLocationTitle();
            if ( !title ) {
                return null;
            }
            var result = this.findLocationByTitle( title );
            return result ? result.location.id : null;
        },

        /**
         * Get coordinates from the info window.
         * Parses the "lat, lng" format from the measurements element.
         * @returns {Object|null} { latitude, longitude } or null if not found/parseable.
         */
        getCoordinates: function() {
            var coordElement = this.getElement( 'COORDINATES_VALUE' );
            if ( !coordElement ) {
                return null;
            }

            var coordText = coordElement.textContent;
            if ( !coordText ) {
                return null;
            }

            // Format: "48.18581, 16.31276" (lat, lng)
            var parts = coordText.split( ',' );
            if ( parts.length !== 2 ) {
                this.error( 'Unexpected coordinate format: ' + coordText );
                return null;
            }

            var latitude = parseFloat( parts[0].trim() );
            var longitude = parseFloat( parts[1].trim() );

            if ( isNaN( latitude ) || isNaN( longitude ) ) {
                this.error( 'Failed to parse coordinates: ' + coordText );
                return null;
            }

            return {
                latitude: latitude,
                longitude: longitude
            };
        },

        /**
         * Find a section container by looking for a div with exact header text.
         * @private
         * @param {Element} container - Parent container to search within.
         * @param {string} headerText - Exact text of the header div.
         * @returns {Element|null} - Parent element of the header div, or null.
         */
        _findSectionByHeaderText: function( container, headerText ) {
            var allDivs = container.querySelectorAll( 'div' );
            for ( var i = 0; i < allDivs.length; i++ ) {
                if ( allDivs[i].textContent.trim() === headerText ) {
                    return allDivs[i].parentElement;
                }
            }
            return null;
        },

        /**
         * Extract contact information from GMM "Details from Google Maps" section.
         * Uses TTText utilities for pattern matching.
         * @param {Element} [infoPanel] - The GMM info panel element. If not provided,
         *                                uses the current INFO_CONTAINER.
         * @returns {Array} - Array of contact info objects with contact_type, value, label, is_primary.
         */
        getContactInfo: function( infoPanel ) {
            var self = this;
            var contacts = [];

            // Use provided panel or find current info container
            if ( !infoPanel ) {
                infoPanel = this.getElement( 'INFO_CONTAINER' );
            }

            if ( !infoPanel ) {
                return contacts;
            }

            // Find the "Details from Google Maps" section by header text
            var detailsSection = this._findSectionByHeaderText( infoPanel, 'Details from Google Maps' );
            if ( !detailsSection ) {
                return contacts;
            }

            // Get all direct child divs
            var children = detailsSection.querySelectorAll( ':scope > div' );

            children.forEach( function( child ) {
                var text = child.textContent.trim();

                // Skip header div and Remove button
                if ( text === 'Details from Google Maps' || text === 'Remove' ) {
                    return;
                }

                // Check for website (has anchor tag, exclude Google Maps links)
                var anchor = child.querySelector( 'a[href]' );
                if ( anchor ) {
                    var url = TTText.extractUrlFromAnchor( anchor, ['maps.google.com'] );
                    if ( url ) {
                        contacts.push({
                            contact_type: 'website',
                            value: url,
                            label: '',
                            is_primary: false
                        });
                        return;
                    }
                }

                if ( !text ) return;

                // Check for phone
                if ( TTText.isPhoneNumber( text ) ) {
                    contacts.push({
                        contact_type: 'phone',
                        value: text,
                        label: '',
                        is_primary: false
                    });
                    return;
                }

                // Check for address
                if ( TTText.isStreetAddress( text ) ) {
                    contacts.push({
                        contact_type: 'address',
                        value: text,
                        label: '',
                        is_primary: false
                    });
                    return;
                }
            });

            return contacts;
        },

        // =====================================================================
        // Style Operations
        // =====================================================================

        /**
         * Open the style popup for current location.
         * @returns {Promise<Element>} The style popup container.
         */
        openStylePopup: function() {
            var self = this;

            return this.waitForElement( 'STYLE_BUTTON' )
                .then( function( button ) {
                    self.log( 'Opening style popup' );
                    return TTDom.click( button );
                })
                .then( function() {
                    return self.waitForElement( 'STYLE_POPUP_CONTAINER' );
                });
        },

        /**
         * Set location color in style popup.
         * @param {string} colorRgb - Color value like "RGB (245, 124, 0)".
         * @returns {Promise<void>}
         */
        setColor: function( colorRgb ) {
            var self = this;
            var colorCells = TTDom.queryAll( this.selectors.STYLE_COLOR_CELLS );

            var colorElement = colorCells.find( function( el ) {
                return el.getAttribute( self.selectors.ATTR_ARIA_LABEL ) === colorRgb;
            });

            if ( !colorElement ) {
                this.error( 'Color not found: ' + colorRgb );
                return Promise.resolve();
            }

            this.log( 'Setting color: ' + colorRgb );
            return TTDom.clickRealistic( colorElement );
        },

        /**
         * Set location icon in style popup.
         * @param {string} iconCode - Icon code like "1535".
         * @returns {Promise<void>}
         */
        setIcon: function( iconCode ) {
            var self = this;
            var stylePopup = this.getElement( 'STYLE_POPUP_CONTAINER' );

            // Try to find in initial icons
            var iconElement = this._findIconElement( stylePopup, iconCode );
            if ( iconElement ) {
                this.log( 'Setting icon (initial): ' + iconCode );
                return TTDom.clickRealistic( iconElement );
            }

            // Not in initial set - need to open "more icons"
            this.log( 'Icon not in initial set, opening more icons: ' + iconCode );
            return this._setIconFromMoreIcons( iconCode );
        },

        /**
         * Find icon element by code within a container.
         * @private
         * @param {Element} container - Container to search.
         * @param {string} iconCode - Icon code.
         * @returns {Element|null}
         */
        _findIconElement: function( container, iconCode ) {
            var self = this;
            var elements = container.querySelectorAll( this.selectors.ICON_ELEMENT );

            return Array.from( elements ).find( function( el ) {
                return el.getAttribute( self.selectors.ATTR_ICON_CODE ) === iconCode;
            }) || null;
        },

        /**
         * Set icon from the "more icons" popup.
         * @private
         * @param {string} iconCode - Icon code.
         * @returns {Promise<void>}
         */
        _setIconFromMoreIcons: function( iconCode ) {
            var self = this;
            var stylePopup = this.getElement( 'STYLE_POPUP_CONTAINER' );
            var moreButton = stylePopup.querySelector( this.selectors.STYLE_MORE_ICONS_BUTTON );

            return TTDom.clickRealistic( moreButton )
                .then( function() {
                    return TTDom.wait( 1000 );
                })
                .then( function() {
                    var target = document.querySelector( self.selectors.MORE_ICONS_CATEGORY_TARGET );
                    if ( !target ) {
                        throw new Error( 'More icons dialog not found' );
                    }
                    var moreDialog = target.parentNode.parentNode;

                    var iconElement = self._findIconElement( moreDialog, iconCode );
                    if ( !iconElement ) {
                        throw new Error( 'Icon not found in more icons: ' + iconCode );
                    }

                    // Click the first child (the actual clickable element)
                    return TTDom.clickRealistic( iconElement.firstChild || iconElement );
                })
                .then( function() {
                    var target = document.querySelector( self.selectors.MORE_ICONS_CATEGORY_TARGET );
                    var moreDialog = target.parentNode.parentNode;
                    var okButton = moreDialog.querySelector( self.selectors.MORE_ICONS_OK_BUTTON );

                    return TTDom.clickRealistic( okButton );
                });
        },

        /**
         * Close the style popup.
         * @returns {Promise<void>}
         */
        closeStylePopup: function() {
            var closeButton = this.getElement( 'STYLE_CLOSE_BUTTON' );
            if ( !closeButton ) {
                return Promise.resolve();
            }
            this.log( 'Closing style popup' );
            return TTDom.clickRealistic( closeButton );
        },

        /**
         * Close the info window if it's open.
         * @returns {Promise<void>}
         */
        closeInfoWindow: function() {
            var closeButton = this.getElement( 'INFO_CLOSE_BUTTON' );
            if ( !closeButton ) {
                return Promise.resolve();
            }
            this.log( 'Closing info window' );
            return TTDom.clickRealistic( closeButton );
        },

        /**
         * Clear search results by clicking the close button in the search results pane.
         * This dismisses the search results pane and clears map markers.
         * @returns {Promise<void>}
         */
        clearSearchResults: function() {
            var closeButton = this.getElement( 'SEARCH_RESULTS_CLOSE' );
            if ( !closeButton ) {
                // No search results pane visible
                return Promise.resolve();
            }

            this.log( 'Clearing search results' );
            return TTDom.click( closeButton );
        },

        /**
         * Submit the current search query.
         * @returns {Promise<void>}
         */
        submitSearch: function() {
            var searchButton = document.querySelector( this.selectors.SEARCH_BUTTON );
            if ( !searchButton ) {
                return Promise.reject( new Error( 'Search button not found' ) );
            }
            this.log( 'Submitting search' );
            return TTDom.click( searchButton );
        },

        // =====================================================================
        // Map Title Operations
        // =====================================================================

        /**
         * Get the current map title.
         * @returns {string|null}
         */
        getMapTitle: function() {
            var titleNode = this.getElement( 'MAP_TITLE_TEXT' );
            return titleNode ? titleNode.textContent : null;
        },

        /**
         * Update the current map's title and description.
         * Clicks the title, waits for edit dialog, enters values, saves.
         * @param {Object} options - { title, description }
         * @param {string} options.title - New map title.
         * @param {string} [options.description] - New map description (optional).
         * @returns {Promise<void>}
         */
        renameMap: function( options ) {
            var self = this;
            var title = options.title;
            var description = options.description;

            return this.waitForElement( 'MAP_TITLE_TEXT' )
                .then( function( titleText ) {
                    self.log( 'Clicking map title to edit' );
                    return TTDom.clickRealistic( titleText );
                })
                .then( function() {
                    return self.waitForElement( 'MAP_TITLE_DIALOG' );
                })
                .then( function( dialog ) {
                    var titleInput = dialog.querySelector( self.selectors.MAP_TITLE_INPUT );
                    var descInput = dialog.querySelector( self.selectors.MAP_DESCRIPTION_INPUT );
                    var saveButton = dialog.querySelector( self.selectors.MAP_TITLE_SAVE_BUTTON );

                    if ( !titleInput || !saveButton ) {
                        throw new Error( 'Map title dialog elements not found' );
                    }

                    self.log( 'Setting map title: ' + title );
                    TTDom.setInputValue( titleInput, title );

                    if ( description && descInput ) {
                        self.log( 'Setting map description' );
                        TTDom.setInputValue( descInput, description );
                    }

                    return TTDom.clickRealistic( saveButton );
                })
                .then( function() {
                    self.log( 'Map updated: ' + title );
                });
        },

        // =====================================================================
        // High-Level Operations
        // =====================================================================

        /**
         * Add a location to a specific layer with styling.
         * Assumes the add-to-map dialog is currently open.
         * @param {Object} options - Configuration.
         * @param {string} options.layerTitle - Title for the layer.
         * @param {string} options.colorRgb - Color value like "RGB (245, 124, 0)".
         * @param {string} options.iconCode - Icon code like "1535".
         * @param {string} [options.customTitle] - Custom title to use (renames from Google's title).
         * @returns {Promise<Object>} Result with { gmmId, title, googleTitle, coordinates }.
         */
        addLocationToLayer: function( options ) {
            var self = this;
            var layerTitle = options.layerTitle;
            var colorRgb = options.colorRgb;
            var iconCode = options.iconCode;
            var customTitle = options.customTitle;
            var googleTitle;
            var finalTitle;
            var gmmLocationId;
            var coordinates;

            return this.getOrCreateLayer( layerTitle )
                .then( function( layer ) {
                    self.log( 'Selecting layer: ' + layerTitle );
                    return self.selectLayer( layer );
                })
                .then( function() {
                    return self.clickAddToMap();
                })
                .then( function() {
                    return self.waitForElement( 'TITLE_DIV' );
                })
                .then( function( titleNode ) {
                    googleTitle = titleNode.textContent;
                    self.log( 'Location added with Google title: ' + googleTitle );

                    // Find the location ID from the layer
                    var result = self.findLocationByTitle( googleTitle );
                    if ( !result ) {
                        throw new Error( 'Could not find added location: ' + googleTitle );
                    }
                    gmmLocationId = result.location.id;

                    // Extract coordinates while info window is open
                    coordinates = self.getCoordinates();
                    if ( coordinates ) {
                        self.log( 'Coordinates: ' + coordinates.latitude + ', ' + coordinates.longitude );
                    }

                    // Rename to custom title if provided and meaningfully different
                    // Skip rename for trivial differences (case, whitespace)
                    var needsRename = customTitle &&
                        customTitle.trim().toLowerCase() !== googleTitle.trim().toLowerCase();

                    if ( needsRename ) {
                        self.log( 'Renaming to custom title: ' + customTitle );
                        return self.renameCurrentLocation( customTitle )
                            .then( function() {
                                finalTitle = customTitle;
                            });
                    } else {
                        finalTitle = googleTitle;
                        return Promise.resolve();
                    }
                })
                .then( function() {
                    // Now style it
                    return self.openStylePopup();
                })
                .then( function() {
                    return self.setColor( colorRgb );
                })
                .then( function() {
                    return self.setIcon( iconCode );
                })
                .then( function() {
                    return self.closeStylePopup();
                })
                .then( function() {
                    // Scroll the layer pane back to top
                    var layerPane = self.getElement( 'LAYER_PANE' );
                    if ( layerPane ) {
                        layerPane.scrollIntoView();
                    }

                    return {
                        gmmId: gmmLocationId,
                        title: finalTitle,
                        googleTitle: googleTitle,
                        coordinates: coordinates
                    };
                });
        },

        /**
         * Get the number of search results in the sidebar pane.
         * @returns {number} Count of search result items.
         */
        getSearchResultCount: function() {
            var items = document.querySelectorAll( this.selectors.SEARCH_RESULTS_ITEMS );
            return items.length;
        },

        /**
         * Search for a location and add it to the map.
         * @param {string} searchText - Text to search for.
         * @param {Object} options - Style options { layerTitle, colorRgb, iconCode, customTitle }.
         * @returns {Promise<Object>} Result with { gmmId, title, googleTitle, coordinates, resultCount, warning }.
         *   - Returns { error: 'no_results' } if no search results found.
         *   - Returns { error: 'no_dialog', resultCount } if results found but no info dialog opened.
         *   - Returns { error: 'too_many_results', resultCount } if 3+ results (too ambiguous).
         *   - Returns { ..., warning: 'multiple_results', resultCount } if 2 results but one was selected.
         */
        searchAndAddLocation: function( searchText, options ) {
            var self = this;

            var searchField = this.getElement( 'SEARCH_FIELD' );
            if ( !searchField ) {
                return Promise.reject( new Error( 'Search field not found' ) );
            }

            TTDom.setInputValue( searchField, searchText );

            var searchButton = document.querySelector( this.selectors.SEARCH_BUTTON );
            if ( !searchButton ) {
                return Promise.reject( new Error( 'Search button not found' ) );
            }

            var resultCount = 0;

            return TTDom.click( searchButton )
                .then( function() {
                    // Wait for search results to load in sidebar
                    return TTDom.wait( 1500 );
                })
                .then( function() {
                    // Count results in sidebar
                    resultCount = self.getSearchResultCount();
                    self.log( 'Search results: ' + resultCount );

                    if ( resultCount === 0 ) {
                        // No results found
                        return Promise.resolve( { error: 'no_results' } );
                    }

                    // Too many results - reject as ambiguous
                    if ( resultCount >= 3 ) {
                        self.log( 'Too many results (' + resultCount + '), rejecting as ambiguous' );
                        return Promise.resolve( { error: 'too_many_results', resultCount: resultCount } );
                    }

                    // Try to find add-to-map button (indicates info dialog opened)
                    // Use short timeout - if not there quickly, it's not coming
                    return TTDom.waitForElement(
                        self.selectors.ADD_TO_MAP_BUTTON,
                        { timeout: 2000, retryMs: 200 }
                    ).catch( function() {
                        // Info dialog did not open
                        return null;
                    });
                })
                .then( function( buttonOrResult ) {
                    // Check if we returned early with an error
                    if ( buttonOrResult && buttonOrResult.error ) {
                        return buttonOrResult;
                    }

                    // buttonOrResult is either the button element or null
                    if ( !buttonOrResult ) {
                        // Info dialog didn't auto-open - try clicking first search result
                        self.log( 'Info dialog did not auto-open, clicking first search result' );
                        var firstResult = document.querySelector( self.selectors.SEARCH_RESULTS_ITEMS );
                        if ( !firstResult ) {
                            self.log( 'No search result items found to click' );
                            return { error: 'no_dialog', resultCount: resultCount };
                        }

                        return TTDom.clickRealistic( firstResult )
                            .then( function() {
                                // Wait for add-to-map button after clicking result
                                return TTDom.waitForElement(
                                    self.selectors.ADD_TO_MAP_BUTTON,
                                    { timeout: 3000, retryMs: 200 }
                                ).catch( function() {
                                    return null;
                                });
                            })
                            .then( function( button ) {
                                if ( !button ) {
                                    self.log( 'Info dialog still did not open after clicking result' );
                                    return { error: 'no_dialog', resultCount: resultCount };
                                }
                                // Dialog opened after click - proceed with adding
                                return self.addLocationToLayer( options )
                                    .then( function( result ) {
                                        if ( resultCount === 2 ) {
                                            result.warning = 'multiple_results';
                                            result.resultCount = resultCount;
                                        }
                                        return result;
                                    });
                            });
                    }

                    // Proceed with adding (1 or 2 results)
                    return self.addLocationToLayer( options )
                        .then( function( result ) {
                            // If 2 results, flag as warning (Google picked one)
                            if ( resultCount === 2 ) {
                                result.warning = 'multiple_results';
                                result.resultCount = resultCount;
                            }
                            return result;
                        });
                });
        }
    }
});
