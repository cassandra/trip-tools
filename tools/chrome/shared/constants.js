/*
 * Trip Tools Chrome Extension - Constants
 * All magic strings centralized here per project coding standards.
 * This file establishes the TT namespace used throughout the extension.
 */

var TT = TT || {};

TT.CONFIG = {
    EXTENSION_NAME: 'Trip Tools Extension',
    EXTENSION_VERSION: '0.1.0',
    IS_DEVELOPMENT: true,
    DEBUG_LOG_MAX_ENTRIES: 50,
    DEFAULT_SERVER_URL_DEV: 'http://localhost:6777',
    DEFAULT_SERVER_URL_PROD: 'https://triptools.net',
    ICON_PROD_48: '../images/icon-48.png',
    ICON_DEV_48: '../images/icon-on-secondary-48.png',
    EXTENSION_AUTHORIZE_PATH: '/user/extensions/',
    TRIP_CREATE_PATH: '/trips/create',
    API_ME_ENDPOINT: '/api/v1/me/',
    API_TOKENS_ENDPOINT: '/api/v1/tokens/',
    API_TRIPS_ENDPOINT: '/api/v1/trips/',
    API_EXTENSION_STATUS_ENDPOINT: '/api/v1/extension/status/',
    API_CLIENT_CONFIG_ENDPOINT: '/api/v1/client-config/',
    API_LOCATIONS_ENDPOINT: '/api/v1/locations/',
    AUTH_VALIDATION_DEBOUNCE_POPUP_MS: 2000,
    AUTH_VALIDATION_TIMEOUT_MS: 5000,
    // Google My Maps default layer name (used for repurposing empty layers)
    GMM_DEFAULT_LAYER_NAME: 'Untitled layer',
    // "Other" layer for locations without valid category
    GMM_OTHER_LAYER_NAME: 'Other',
    // Grey color from GMM's palette (aria-label value)
    GMM_OTHER_LAYER_COLOR: 'RGB (117, 117, 117)',
    GMM_OTHER_LAYER_ICON: '1594',
    // GMM map index cache TTL (1 hour)
    GMM_MAP_INDEX_TTL_MS: 60 * 60 * 1000,
    // Pinned trip stale threshold (30 days)
    PIN_STALE_THRESHOLD_DAYS: 30
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
    KEY_AUTH_STATE: 'tt_authState',
    // Sync infrastructure
    KEY_SYNC_AS_OF: 'tt_syncAsOf',
    KEY_ACTIVE_TRIP_UUID: 'tt_activeTripUuid',
    // Trip working set
    KEY_WORKING_SET_TRIPS: 'tt_workingSetTrips',
    // Client config
    KEY_CLIENT_CONFIG: 'tt_clientConfig',
    KEY_CLIENT_CONFIG_VERSION: 'tt_clientConfigVersion',
    KEY_CLIENT_CONFIG_STALE: 'tt_clientConfigStale',
    // Location sync metadata (per-trip)
    KEY_LOCATION_SYNC_PREFIX: 'tt_locationSync_',
    // GMM map index (gmm_map_id -> trip_uuid mapping)
    KEY_GMM_MAP_INDEX: 'tt_gmmMapIndex',
    // Dismissed unlinked GMM map dialogs (user chose "Dismiss")
    KEY_DISMISSED_UNLINKED_GMM_MAPS: 'tt_dismissedUnlinkedGmmMaps',
    // Pinned current trip
    KEY_PINNED_TRIP_UUID: 'tt_pinnedTripUuid',
    KEY_PIN_TIMESTAMP: 'tt_pinTimestamp'
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
    TYPE_DISCONNECT: 'tt_disconnect',
    // Trip management
    TYPE_GET_TRIPS_WORKING_SET: 'tt_getTripsWorkingSet',
    TYPE_SET_ACTIVE_TRIP: 'tt_setActiveTrip',
    TYPE_GET_ALL_TRIPS: 'tt_getAllTrips',
    TYPE_CREATE_AND_ACTIVATE_TRIP: 'tt_createAndActivateTrip',
    // Location management (GMM content script <-> background)
    TYPE_SAVE_LOCATION: 'tt_saveLocation',
    TYPE_GET_LOCATION: 'tt_getLocation',
    TYPE_UPDATE_LOCATION: 'tt_updateLocation',
    TYPE_DELETE_LOCATION: 'tt_deleteLocation',
    // Client config (content script <-> background)
    TYPE_GET_LOCATION_CATEGORIES: 'tt_getLocationCategories',
    // GMM content script commands
    TYPE_GMM_SEARCH_AND_ADD: 'tt_gmmSearchAndAdd',
    TYPE_GMM_GET_MAP_INFO: 'tt_gmmGetMapInfo',
    // GMM map management
    TYPE_GMM_CREATE_MAP: 'tt_gmmCreateMap',
    TYPE_GMM_OPEN_MAP: 'tt_gmmOpenMap',
    TYPE_GMM_RENAME_MAP: 'tt_gmmRenameMap',
    TYPE_GMM_LINK_MAP: 'tt_gmmLinkMap',
    TYPE_GMM_UNLINK_MAP: 'tt_gmmUnlinkMap',
    // Location sync
    TYPE_GMM_SYNC_LOCATIONS: 'tt_gmmSyncLocations',
    TYPE_GET_TRIP_LOCATIONS: 'tt_getTripLocations',
    // Trip context
    TYPE_GET_ACTIVE_TRIP: 'tt_getActiveTrip',
    // GMM map linkage check
    TYPE_IS_GMM_MAP_LINKED: 'tt_isGmmMapLinked',
    // Pin management
    TYPE_SET_PINNED_TRIP: 'tt_setPinnedTrip',
    TYPE_RESET_PIN_TIMESTAMP: 'tt_resetPinTimestamp'
};

TT.DOM = {
    ID_POPUP_CONTAINER: 'tt-popup-container',
    ID_HEADER_ICON: 'tt-header-icon',
    ID_STATUS_INDICATOR: 'tt-status-indicator',
    ID_STATUS_TEXT: 'tt-status-text',
    // Trip section
    ID_TRIP_SECTION: 'tt-trip-section',
    ID_TRIP_LIST: 'tt-trip-list',
    ID_TRIP_LOADING: 'tt-trip-loading',
    ID_TRIP_EMPTY: 'tt-trip-empty',
    ID_NEW_TRIP_BTN: 'tt-new-trip-btn',
    // Maps section (stub)
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
    CLASS_RATE_LIMITED: 'tt-rate-limited',
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
    ID_OPTIONS_VERSION: 'tt-options-version',
    CLASS_POPUP_HEADER: 'tt-popup-header',
    CLASS_TOKEN_VALIDATION_STATUS: 'tt-token-validation-status',
    // Trip UI (legacy - to be removed)
    ID_ACTIVE_TRIP: 'tt-active-trip',
    ID_ACTIVE_TRIP_TITLE: 'tt-active-trip-title',
    ID_OTHER_TRIPS: 'tt-other-trips',
    ID_OTHER_TRIPS_LIST: 'tt-other-trips-list',
    CLASS_TRIP_LOADING: 'tt-trip-loading',
    CLASS_TRIP_EMPTY: 'tt-trip-empty',
    CLASS_SWITCH_TRIP_BTN: 'tt-switch-trip-btn',
    // Working Set UI (unified trip list)
    ID_WORKING_SET: 'tt-working-set',
    ID_STALE_PIN_WARNING: 'tt-stale-pin-warning',
    ID_STALE_PIN_DISMISS: 'tt-stale-pin-dismiss',
    CLASS_TRIP_ROW: 'tt-trip-row',
    CLASS_TRIP_CURRENT: 'tt-current',
    CLASS_PIN_CONTROL: 'tt-pin-control',
    // More Trips Panel
    ID_MORE_TRIPS_BTN: 'tt-more-trips-btn',
    ID_MORE_TRIPS_PANEL: 'tt-more-trips-panel',
    ID_MORE_TRIPS_BACK: 'tt-more-trips-back',
    ID_MORE_TRIPS_LIST: 'tt-more-trips-list',
    ID_MORE_TRIPS_LOADING: 'tt-more-trips-loading',
    ID_MORE_TRIPS_ERROR: 'tt-more-trips-error',
    // GMM Map Status
    ID_ACTIVE_TRIP_ROW: 'tt-active-trip-row',
    ID_GMM_STATUS: 'tt-gmm-status',
    CLASS_GMM_LINKED: 'tt-gmm-linked',
    CLASS_GMM_UNLINKED: 'tt-gmm-unlinked',
    // Creating Map Progress Dialog
    ID_CREATING_MAP_DIALOG: 'tt-creating-map-dialog',
    ID_CREATING_MAP_STATUS: 'tt-creating-map-status',
    // Trip Details Panel
    ID_TRIP_DETAILS_BTN: 'tt-trip-details-btn',
    ID_TRIP_DETAILS_PANEL: 'tt-trip-details-panel',
    ID_TRIP_DETAILS_BACK: 'tt-trip-details-back',
    ID_TRIP_DETAILS_TITLE: 'tt-trip-details-title',
    ID_TRIP_DETAILS_DESCRIPTION: 'tt-trip-details-description',
    ID_TRIP_DETAILS_UUID: 'tt-trip-details-uuid',
    ID_TRIP_DETAILS_GMM_ID: 'tt-trip-details-gmm-id',
    ID_TRIP_DETAILS_GMM_ROW: 'tt-trip-details-gmm-row',
    ID_TRIP_DETAILS_ACTIONS: 'tt-trip-details-actions',
    ID_TRIP_DETAILS_SYNC_BTN: 'tt-trip-details-sync-btn',
    ID_TRIP_DETAILS_UNLINK_BTN: 'tt-trip-details-unlink-btn',
    // Trip Details Panel - Unlinked Trip Actions
    ID_TRIP_DETAILS_ACTIONS_UNLINKED: 'tt-trip-details-actions-unlinked',
    ID_TRIP_DETAILS_CREATE_MAP_BTN: 'tt-trip-details-create-map-btn',
    ID_TRIP_DETAILS_LINK_CURRENT_BTN: 'tt-trip-details-link-current-btn',
    ID_TRIP_DETAILS_LINK_HINT: 'tt-trip-details-link-hint',
    // Create Trip Panel
    ID_CREATE_TRIP_PANEL: 'tt-create-trip-panel',
    ID_CREATE_TRIP_BACK: 'tt-create-trip-back-btn',
    ID_CREATE_TRIP_TITLE_INPUT: 'tt-create-trip-title',
    ID_CREATE_TRIP_DESC_INPUT: 'tt-create-trip-description',
    ID_CREATE_TRIP_ERROR: 'tt-create-trip-error',
    ID_CREATE_TRIP_CANCEL: 'tt-create-trip-cancel-btn',
    ID_CREATE_TRIP_SUBMIT: 'tt-create-trip-submit-btn',
    // Create Trip - Link Map Choice
    ID_CREATE_TRIP_LINK_CHOICE: 'tt-create-trip-link-choice',
    ID_CREATE_TRIP_LINK_NO: 'tt-create-trip-link-no',
    ID_CREATE_TRIP_LINK_YES: 'tt-create-trip-link-yes',
    // Link Map Button and Panel
    ID_LINK_MAP_BTN: 'tt-link-map-btn',
    ID_LINK_MAP_PANEL: 'tt-link-map-panel',
    ID_LINK_MAP_BACK: 'tt-link-map-back',
    ID_LINK_MAP_LOADING: 'tt-link-map-loading',
    ID_LINK_MAP_ERROR: 'tt-link-map-error',
    ID_LINK_MAP_LIST: 'tt-link-map-list',
    ID_LINK_MAP_EMPTY: 'tt-link-map-empty',
    // Link Success Panel
    ID_LINK_SUCCESS_PANEL: 'tt-link-success-panel',
    ID_LINK_SUCCESS_TITLE: 'tt-link-success-title',
    ID_LINK_SUCCESS_RELOAD: 'tt-link-success-reload',
    ID_LINK_SUCCESS_DISMISS: 'tt-link-success-dismiss'
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
    STATUS_TIMEOUT: 'timeout',
    STATUS_RATE_LIMITED: 'rate_limited'
};

/*
 * Sync infrastructure constants.
 * Used for client-server data synchronization.
 */
TT.SYNC = {
    // Response envelope fields
    FIELD_DATA: 'data',
    FIELD_SYNC: 'sync',
    FIELD_AS_OF: 'as_of',
    FIELD_UPDATES: 'updates',   // Trip sync: full trip data keyed by UUID
    FIELD_VERSIONS: 'versions', // Location sync: version-only pattern
    FIELD_DELETED: 'deleted',
    // Object types (must match server SyncObjectType enum)
    OBJECT_TYPE_TRIP: 'trip',
    OBJECT_TYPE_LOCATION: 'location'
};

TT.HEADERS = {
    SYNC_SINCE: 'X-Sync-Since',
    SYNC_TRIP: 'X-Sync-Trip'
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
    STATUS_TIMEOUT: 'Connection timeout',
    STATUS_RATE_LIMITED: 'Rate limited',
    // Trip UI
    TRIP_SECTION_HEADER: 'Active Trip',
    TRIP_LOADING: 'Loading trips...',
    TRIP_EMPTY: 'No trips available.',
    TRIP_ERROR: 'Unable to load trips.'
};
