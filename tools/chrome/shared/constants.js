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
    ICON_DEV_48: '../images/icon-on-secondary-48.png',
    EXTENSION_AUTHORIZE_PATH: '/user/extensions/authorize/',
    API_ME_ENDPOINT: '/api/v1/me/',
    API_TOKENS_ENDPOINT: '/api/v1/tokens/',
    AUTH_VALIDATION_DEBOUNCE_MS: 2000,
    AUTH_VALIDATION_TIMEOUT_MS: 5000
};

TT.STORAGE = {
    KEY_MAP_INFO_LIST: 'tt_mapInfoList',
    KEY_SELECT_DECORATE_ENABLED: 'tt_selectDecorateEnabled',
    KEY_DEVELOPER_MODE: 'tt_developerMode',
    KEY_DEBUG_PANEL_ENABLED: 'tt_debugPanelEnabled',
    KEY_SERVER_URL: 'tt_serverUrl',
    KEY_EXTENSION_STATE: 'tt_extensionState',
    KEY_DEBUG_LOG: 'tt_debugLog',
    KEY_API_TOKEN: 'tt_apiToken',
    KEY_USER_EMAIL: 'tt_userEmail',
    KEY_AUTH_STATE: 'tt_authState'
};

TT.MESSAGE = {
    TYPE_PING: 'tt_ping',
    TYPE_PONG: 'tt_pong',
    TYPE_GET_STATE: 'tt_getState',
    TYPE_STATE_RESPONSE: 'tt_stateResponse',
    TYPE_LOG: 'tt_log',
    TYPE_ERROR: 'tt_error',
    TYPE_TOKEN_RECEIVED: 'tt_tokenReceived',
    TYPE_AUTH_STATUS_REQUEST: 'tt_authStatusRequest',
    TYPE_AUTH_STATUS_RESPONSE: 'tt_authStatusResponse',
    TYPE_AUTH_STATE_CHANGED: 'tt_authStateChanged',
    TYPE_DISCONNECT: 'tt_disconnect'
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
    CLASS_OFFLINE: 'tt-offline',
    CLASS_SERVER_ERROR: 'tt-server-error',
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
    CLASS_VISIBLE: 'tt-visible',
    ID_AUTH_SECTION: 'tt-auth-section',
    ID_AUTH_STATUS: 'tt-auth-status',
    ID_AUTHORIZE_BTN: 'tt-authorize-btn',
    ID_DEBUG_AUTH_INFO: 'tt-debug-auth-info',
    ID_OPTIONS_AUTH_SECTION: 'tt-options-auth-section',
    ID_OPTIONS_AUTH_AUTHORIZED: 'tt-options-auth-authorized',
    ID_OPTIONS_AUTH_NOT_AUTHORIZED: 'tt-options-auth-not-authorized',
    ID_OPTIONS_AUTH_EMAIL: 'tt-options-auth-email',
    ID_OPTIONS_DISCONNECT_BTN: 'tt-options-disconnect-btn',
    ID_OPTIONS_AUTHORIZE_BTN: 'tt-options-authorize-btn',
    ID_OPTIONS_MANUAL_TOKEN_INPUT: 'tt-options-manual-token-input',
    ID_OPTIONS_VALIDATE_TOKEN_BTN: 'tt-options-validate-token-btn',
    ID_OPTIONS_TOKEN_VALIDATION_STATUS: 'tt-options-token-validation-status',
    CLASS_POPUP_HEADER: 'tt-popup-header',
    CLASS_TOKEN_VALIDATION_STATUS: 'tt-token-validation-status'
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

/*
 * Server-synced constants.
 * These values MUST match TtConst in src/tt/environment/constants.py
 * and the corresponding CSS in src/tt/static/css/main.css
 * Variable names are intentionally identical for cross-repo searchability.
 */
TT.SERVER_SYNC = {
    // Body classes added by content script for extension state
    EXT_STATE_CLASS_AUTHORIZED: 'tt-ext-authorized',
    EXT_STATE_CLASS_NOT_AUTHORIZED: 'tt-ext-not-authorized',
    // PostMessage types for extension<->page communication
    EXT_POSTMESSAGE_DATA_TYPE: 'tt_extension_data',
    EXT_POSTMESSAGE_ACK_TYPE: 'tt_extension_ack',
    // DOM element ID for token handoff
    EXT_TOKEN_DATA_ELEMENT_ID: 'extension-token-data'
};

TT.AUTH = {
    STATE_AUTHORIZED: 'authorized',
    STATE_NOT_AUTHORIZED: 'not_authorized',
    STATE_PENDING: 'pending',
    POSTMESSAGE_TYPE: 'tt_extension_token',
    TOKEN_NAME_PREFIX: 'Chrome Extension',
    STATUS_ONLINE: 'online',
    STATUS_OFFLINE: 'offline',
    STATUS_SERVER_ERROR: 'server_error',
    STATUS_TIMEOUT: 'timeout'
};

TT.STRINGS = {
    AUTH_BUTTON_AUTHORIZE: 'Authorize Extension',
    AUTH_BUTTON_DISCONNECT: 'Disconnect',
    AUTH_BUTTON_VALIDATE: 'Validate',
    AUTH_STATUS_AUTHORIZED: 'Authorized',
    AUTH_STATUS_NOT_AUTHORIZED: 'Not Authorized',
    AUTH_STATUS_AUTHORIZED_AS: 'Authorized as',
    AUTH_STATUS_CHECKING: 'Checking authorization...',
    AUTH_ERROR_INVALID_TOKEN: 'Token is invalid or expired. Please re-authorize.',
    AUTH_ERROR_INVALID_FORMAT: 'Invalid token format. Token should start with "tt_".',
    AUTH_ERROR_NETWORK: 'Unable to connect to Trip Tools server.',
    AUTH_SUCCESS_VALIDATED: 'Token validated successfully!',
    AUTH_SUCCESS_DISCONNECTED: 'Disconnected from Trip Tools.',
    AUTH_STATUS_DISCONNECTING: 'Disconnecting...',
    AUTH_ERROR_DISCONNECT_FAILED: 'Failed to disconnect. Please try again.',
    AUTH_PROMPT_CONNECT: 'Connect to your Trip Tools account for full functionality.',
    AUTH_PROMPT_MANUAL: 'Or enter your API token manually:',
    AUTH_REQUIRES_AUTHORIZATION: 'Requires authorization',
    AUTH_SERVER_UNAVAILABLE: 'Server unavailable',
    DEBUG_USER_EMAIL: 'User',
    DEBUG_AUTH_STATUS: 'Auth',
    DEBUG_TOKEN_PRESENT: 'Token present',
    DEBUG_TOKEN_ABSENT: 'No token',
    STATUS_ONLINE: 'Connected',
    STATUS_OFFLINE: 'Offline',
    STATUS_SERVER_ERROR: 'Server error',
    STATUS_TIMEOUT: 'Connection timeout'
};
