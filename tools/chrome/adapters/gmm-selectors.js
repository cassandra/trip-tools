/*
 * Google My Maps DOM Selectors
 * Centralized selector configuration for GMM manipulation.
 * Update this file when Google changes their UI.
 *
 * Selector naming convention:
 * - IDs use the actual element ID (e.g., ADD_TO_MAP_BUTTON = '#addtomap-button')
 * - Containers use _CONTAINER suffix
 * - Buttons use _BUTTON suffix
 * - Attributes use _ATTR suffix with the attribute name as value
 */

var TTGmmSelectors = {
    // Version identifier for tracking UI changes
    VERSION: '2024-12',

    // =========================================================================
    // Map Title (for renaming)
    // =========================================================================

    // Map title in header - clickable element with data-tooltip and aria-label
    MAP_TITLE_CONTAINER: '#map-title-desc-bar',
    MAP_TITLE_TEXT: '#map-title-desc-bar > div[data-tooltip][aria-label]',
    // Edit map title/description dialog (id="update-map")
    MAP_TITLE_DIALOG: '#update-map',
    MAP_TITLE_INPUT: 'input[type="text"]',
    MAP_DESCRIPTION_INPUT: 'textarea',
    MAP_TITLE_SAVE_BUTTON: 'button[name="save"]',

    // =========================================================================
    // Dialog Detection
    // =========================================================================

    DIALOG: 'div[role="dialog"]',

    // =========================================================================
    // Add to Map Flow
    // =========================================================================

    ADD_TO_MAP_BUTTON: '#addtomap-button',
    SEARCH_FIELD: '#mapsprosearch-field',
    SEARCH_BUTTON: '#mapsprosearch-button div',

    // =========================================================================
    // Location Info Window
    // =========================================================================

    INFO_CONTAINER: '#map-infowindow-container',
    EDIT_BUTTON: '#map-infowindow-edit-button',
    STYLE_BUTTON: '#map-infowindow-style-button',
    TITLE_DIV: '#map-infowindow-attr-name-value',
    NOTES_DIV: '#map-infowindow-attr-description-value',
    NOTES_CONTAINER: '#map-infowindow-attr-description-container',
    EDIT_SAVE_BUTTON: '#map-infowindow-done-editing-button',

    // Coordinates display (bottom-left of info window dialog)
    // Format: "48.18581, 16.31276" (lat, lng)
    COORDINATES_CONTAINER: '#infowindow-measurements',
    COORDINATES_VALUE: '#infowindow-measurements li',

    // =========================================================================
    // Style Popup
    // =========================================================================

    STYLE_POPUP_CONTAINER: '#stylepopup-container',
    STYLE_CLOSE_BUTTON: '#stylepopup-close',
    STYLE_COLOR_CELLS: '#stylepopup-color td > div',
    STYLE_MORE_ICONS_BUTTON: '#stylepopup-moreicons-button',

    // Icon elements use iconcode attribute
    ICON_ELEMENT: 'div[iconcode]',

    // More icons dialog
    MORE_ICONS_CATEGORY_TARGET: '#iconspopup-category-target-1',
    MORE_ICONS_OK_BUTTON: 'button[name="ok"]',

    // =========================================================================
    // Layer Management
    // =========================================================================

    // Layer list container
    LAYER_PANE: '#featurelist-pane',
    LAYER_SCROLLABLE_CONTAINER: '#featurelist-scrollable-container',

    // Individual layers have layerid attribute
    LAYER_ITEM: '#featurelist-scrollable-container div[layerid]',

    // Layer controls
    ADD_LAYER_BUTTON: '#map-action-add-layer',
    LAYER_OPTIONS_MENU: '#layerview-menu',
    LAYER_UPDATE_DIALOG: '#update-layer-name',
    LAYER_NAME_INPUT: 'input[type="text"]',
    LAYER_SAVE_BUTTON: 'button[name="save"]',

    // =========================================================================
    // Location Items (within layers)
    // =========================================================================

    // Location items have fl_id attribute
    LOCATION_ITEM: 'div[fl_id]',

    // =========================================================================
    // Attribute Names (for getAttribute calls)
    // =========================================================================

    ATTR_LAYER_ID: 'layerid',
    ATTR_LOCATION_ID: 'fl_id',
    ATTR_ICON_CODE: 'iconcode',
    ATTR_ARIA_LABEL: 'aria-label',

    // Layer menu item attribute
    ATTR_LAYER_MENU_ITEM: 'item',
    VALUE_LAYER_MENU_RENAME: 'rename-layer',

    // =========================================================================
    // Content Editable Check
    // =========================================================================

    ATTR_CONTENT_EDITABLE: 'contenteditable'
};
