/*
 * Trip Tools Chrome Extension - Constants
 * All magic strings centralized here per project coding standards.
 * This file establishes the TT namespace used throughout the extension.
 */

var TT = TT || {};

TT.CONFIG = {
    EXTENSION_NAME: 'Trip Tools',
    EXTENSION_VERSION: '0.1.0',
    IS_DEVELOPMENT: true,
    DEBUG_LOG_MAX_ENTRIES: 50,
    DEFAULT_SERVER_URL_DEV: 'http://localhost:6777',
    DEFAULT_SERVER_URL_PROD: 'https://triptools.net',
    ICON_PROD_48: '../images/icon-48.png',
    ICON_DEV_48: '../images/icon-on-secondary-48.png'
};

TT.STORAGE = {
    KEY_MAP_INFO_LIST: 'tt_mapInfoList',
    KEY_SELECT_DECORATE_ENABLED: 'tt_selectDecorateEnabled',
    KEY_DEVELOPER_MODE: 'tt_developerMode',
    KEY_DEBUG_PANEL_ENABLED: 'tt_debugPanelEnabled',
    KEY_SERVER_URL: 'tt_serverUrl',
    KEY_EXTENSION_STATE: 'tt_extensionState',
    KEY_DEBUG_LOG: 'tt_debugLog'
};

TT.MESSAGE = {
    TYPE_PING: 'tt_ping',
    TYPE_PONG: 'tt_pong',
    TYPE_GET_STATE: 'tt_getState',
    TYPE_STATE_RESPONSE: 'tt_stateResponse',
    TYPE_LOG: 'tt_log',
    TYPE_ERROR: 'tt_error'
};

TT.DOM = {
    ID_POPUP_CONTAINER: 'tt-popup-container',
    ID_HEADER_ICON: 'tt-header-icon',
    ID_VERSION: 'tt-version',
    ID_STATUS_INDICATOR: 'tt-status-indicator',
    ID_STATUS_TEXT: 'tt-status-text',
    ID_MAPS_SECTION: 'tt-maps-section',
    ID_MAPS_LIST: 'tt-maps-list',
    ID_ADD_MAP_BTN: 'tt-add-map-btn',
    ID_REFRESH_MAPS_BTN: 'tt-refresh-maps-btn',
    ID_ACTIONS_SECTION: 'tt-actions-section',
    ID_OPEN_MYMAPS_BTN: 'tt-open-mymaps-btn',
    ID_SYNC_BTN: 'tt-sync-btn',
    ID_SETTINGS_SECTION: 'tt-settings-section',
    ID_DECORATE_TOGGLE: 'tt-decorate-toggle',
    ID_DEBUG_PANEL: 'tt-debug-panel',
    ID_DEBUG_HEADER: 'tt-debug-header',
    ID_DEBUG_ARROW: 'tt-debug-arrow',
    ID_DEBUG_CONTENT: 'tt-debug-content',
    ID_DEBUG_LOG: 'tt-debug-log',
    CLASS_BTN: 'tt-btn',
    CLASS_BTN_PRIMARY: 'tt-btn-primary',
    CLASS_BTN_SECONDARY: 'tt-btn-secondary',
    CLASS_BTN_STUB: 'tt-btn-stub',
    CLASS_SECTION: 'tt-section',
    CLASS_SECTION_HEADER: 'tt-section-header',
    CLASS_CONNECTED: 'tt-connected',
    CLASS_DISCONNECTED: 'tt-disconnected',
    CLASS_HIDDEN: 'tt-hidden',
    CLASS_DEV_MODE: 'tt-dev-mode',
    ID_OPTIONS_DEVELOPER_MODE_TOGGLE: 'tt-options-developer-mode-toggle',
    ID_OPTIONS_DEVELOPER_SECTION: 'tt-options-developer-section',
    ID_OPTIONS_SERVER_URL: 'tt-options-server-url',
    ID_OPTIONS_DEBUG_PANEL_TOGGLE: 'tt-options-debug-panel-toggle',
    ID_OPTIONS_SAVE_STATUS: 'tt-options-save-status',
    ID_SETTINGS_BTN: 'tt-settings-btn',
    ID_QUICK_SETTINGS: 'tt-quick-settings',
    ID_QUICK_SETTINGS_BACK: 'tt-quick-settings-back',
    ID_QUICK_SETTINGS_HEADER: 'tt-quick-settings-header',
    ID_ALL_OPTIONS_LINK: 'tt-all-options-link',
    CLASS_VISIBLE: 'tt-visible'
};

TT.URL = {
    GMM_DOMAIN: 'www.google.com',
    GMM_HOME_PATH: '/maps/d',
    GMM_EDIT_PATH: '/maps/d/edit',
    GMM_MAP_ID_PARAM: 'mid'
};

TT.CONTENT_SITES = {
    BOOKING_COM: 'www.booking.com',
    TRIPADVISOR: 'www.tripadvisor.com',
    GOOGLE_TRAVEL: 'www.google.com/travel',
    GOOGLE_MY_MAPS: 'www.google.com/maps/d'
};
