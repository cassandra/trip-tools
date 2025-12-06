/*
 * Trip Tools Chrome Extension - Options Page Script
 * Handles options page initialization and settings management.
 */

document.addEventListener( 'DOMContentLoaded', function() {
    initializeOptions();
});

function initializeOptions() {
    loadSettings();
    setupEventListeners();
}

function getDefaultServerUrl() {
    if ( TT.CONFIG.IS_DEVELOPMENT ) {
        return TT.CONFIG.DEFAULT_SERVER_URL_DEV;
    }
    return TT.CONFIG.DEFAULT_SERVER_URL_PROD;
}

function getDefaultDeveloperMode() {
    return TT.CONFIG.IS_DEVELOPMENT;
}

function loadSettings() {
    var defaultDeveloperMode = getDefaultDeveloperMode();
    var defaultServerUrl = getDefaultServerUrl();

    TTStorage.get( TT.STORAGE.KEY_DEVELOPER_MODE, defaultDeveloperMode )
        .then( function( enabled ) {
            var toggle = document.getElementById( TT.DOM.ID_OPTIONS_DEVELOPER_MODE_TOGGLE );
            if ( toggle ) {
                toggle.checked = enabled;
            }
            updateDeveloperSectionVisibility( enabled );
        });

    TTStorage.get( TT.STORAGE.KEY_SERVER_URL, defaultServerUrl )
        .then( function( url ) {
            var input = document.getElementById( TT.DOM.ID_OPTIONS_SERVER_URL );
            if ( input ) {
                input.value = url;
            }
        });

    TTStorage.get( TT.STORAGE.KEY_DEBUG_PANEL_ENABLED, true )
        .then( function( enabled ) {
            var toggle = document.getElementById( TT.DOM.ID_OPTIONS_DEBUG_PANEL_TOGGLE );
            if ( toggle ) {
                toggle.checked = enabled;
            }
        });
}

function setupEventListeners() {
    var developerModeToggle = document.getElementById( TT.DOM.ID_OPTIONS_DEVELOPER_MODE_TOGGLE );
    if ( developerModeToggle ) {
        developerModeToggle.addEventListener( 'change', function() {
            var enabled = this.checked;
            TTStorage.set( TT.STORAGE.KEY_DEVELOPER_MODE, enabled )
                .then( function() {
                    updateDeveloperSectionVisibility( enabled );
                    if ( enabled ) {
                        setDefaultsForDeveloperMode();
                    }
                    showSaveStatus();
                });
        });
    }

    var serverUrlInput = document.getElementById( TT.DOM.ID_OPTIONS_SERVER_URL );
    if ( serverUrlInput ) {
        serverUrlInput.addEventListener( 'change', function() {
            TTStorage.set( TT.STORAGE.KEY_SERVER_URL, this.value )
                .then( function() {
                    showSaveStatus();
                });
        });
    }

    var debugPanelToggle = document.getElementById( TT.DOM.ID_OPTIONS_DEBUG_PANEL_TOGGLE );
    if ( debugPanelToggle ) {
        debugPanelToggle.addEventListener( 'change', function() {
            TTStorage.set( TT.STORAGE.KEY_DEBUG_PANEL_ENABLED, this.checked )
                .then( function() {
                    showSaveStatus();
                });
        });
    }
}

function updateDeveloperSectionVisibility( enabled ) {
    var section = document.getElementById( TT.DOM.ID_OPTIONS_DEVELOPER_SECTION );
    if ( section ) {
        if ( enabled ) {
            section.classList.remove( TT.DOM.CLASS_HIDDEN );
        } else {
            section.classList.add( TT.DOM.CLASS_HIDDEN );
        }
    }
}

function setDefaultsForDeveloperMode() {
    var debugPanelToggle = document.getElementById( TT.DOM.ID_OPTIONS_DEBUG_PANEL_TOGGLE );
    if ( debugPanelToggle ) {
        debugPanelToggle.checked = true;
        TTStorage.set( TT.STORAGE.KEY_DEBUG_PANEL_ENABLED, true );
    }
}

function showSaveStatus() {
    var status = document.getElementById( TT.DOM.ID_OPTIONS_SAVE_STATUS );
    if ( status ) {
        status.textContent = 'Settings saved.';
        setTimeout( function() {
            status.textContent = '';
        }, 2000 );
    }
}
