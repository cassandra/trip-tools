/*
 * Trip Tools Chrome Extension - Options Page Script
 * Handles options page initialization and settings management.
 */

document.addEventListener( 'DOMContentLoaded', function() {
    initializeOptions();
});

function initializeOptions() {
    applyDevModeStyles();
    loadSettings();
    setupEventListeners();
    checkAuthStatus();
    listenForAuthStateChanges();
}

function applyDevModeStyles() {
    if ( TT.CONFIG.IS_DEVELOPMENT ) {
        var devBanner = document.getElementById( TT.DOM.ID_DEV_BANNER );
        if ( devBanner ) {
            devBanner.classList.remove( TT.DOM.CLASS_HIDDEN );
        }
    }
}

function listenForAuthStateChanges() {
    chrome.runtime.onMessage.addListener( function( message ) {
        if ( message.type === TT.MESSAGE.TYPE_AUTH_STATE_CHANGED ) {
            if ( message.data.authorized ) {
                showAuthorizedState( message.data.uuid );
            } else {
                showNotAuthorizedState();
            }
        }
    });
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

    displayVersion();
}

function displayVersion() {
    var versionSpan = document.getElementById( TT.DOM.ID_OPTIONS_VERSION );
    if ( versionSpan ) {
        var versionText = 'v' + TT.CONFIG.EXTENSION_VERSION;
        if ( TT.CONFIG.IS_DEVELOPMENT ) {
            versionText += ' (DEV)';
        }
        versionSpan.textContent = versionText;

        // Also show config version if available
        TTClientConfig.getVersion()
            .then( function( configVersion ) {
                if ( configVersion ) {
                    // Show first 8 chars of MD5 hash for brevity
                    versionSpan.textContent = versionText + ' | cfg:' + configVersion.substring( 0, 8 );
                }
            });
    }
}

function setupEventListeners() {
    setupAuthEventListeners();

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

function checkAuthStatus() {
    TTMessaging.send( TT.MESSAGE.TYPE_AUTH_STATUS_REQUEST, {} )
        .then( function( response ) {
            if ( response && response.success && response.data.authorized ) {
                showAuthorizedState( response.data.uuid );
            } else {
                showNotAuthorizedState();
            }
        })
        .catch( function() {
            showNotAuthorizedState();
        });
}

function showAuthorizedState( uuid ) {
    var authorizedSection = document.getElementById( TT.DOM.ID_OPTIONS_AUTH_AUTHORIZED );
    var notAuthorizedSection = document.getElementById( TT.DOM.ID_OPTIONS_AUTH_NOT_AUTHORIZED );
    var uuidSpan = document.getElementById( TT.DOM.ID_OPTIONS_AUTH_UUID );

    if ( authorizedSection ) {
        authorizedSection.classList.remove( TT.DOM.CLASS_HIDDEN );
    }
    if ( notAuthorizedSection ) {
        notAuthorizedSection.classList.add( TT.DOM.CLASS_HIDDEN );
    }
    if ( uuidSpan ) {
        // Display truncated UUID for diagnostics (first 8 chars)
        var displayUuid = uuid ? uuid.substring( 0, 8 ) + '...' : '';
        uuidSpan.textContent = displayUuid;
        uuidSpan.title = uuid || '';  // Full UUID on hover
    }

    clearTokenValidationStatus();
}

function showNotAuthorizedState() {
    var authorizedSection = document.getElementById( TT.DOM.ID_OPTIONS_AUTH_AUTHORIZED );
    var notAuthorizedSection = document.getElementById( TT.DOM.ID_OPTIONS_AUTH_NOT_AUTHORIZED );

    if ( authorizedSection ) {
        authorizedSection.classList.add( TT.DOM.CLASS_HIDDEN );
    }
    if ( notAuthorizedSection ) {
        notAuthorizedSection.classList.remove( TT.DOM.CLASS_HIDDEN );
    }

    clearTokenValidationStatus();
}

function setupAuthEventListeners() {
    var authorizeBtn = document.getElementById( TT.DOM.ID_OPTIONS_AUTHORIZE_BTN );
    if ( authorizeBtn ) {
        authorizeBtn.addEventListener( 'click', function() {
            TTAuth.openAuthorizePage();
        });
    }

    var disconnectBtn = document.getElementById( TT.DOM.ID_OPTIONS_DISCONNECT_BTN );
    if ( disconnectBtn ) {
        disconnectBtn.addEventListener( 'click', function() {
            handleDisconnect();
        });
    }

    var validateBtn = document.getElementById( TT.DOM.ID_OPTIONS_VALIDATE_TOKEN_BTN );
    if ( validateBtn ) {
        validateBtn.addEventListener( 'click', function() {
            handleManualTokenValidation();
        });
    }

    var tokenInput = document.getElementById( TT.DOM.ID_OPTIONS_MANUAL_TOKEN_INPUT );
    if ( tokenInput ) {
        tokenInput.addEventListener( 'keypress', function( e ) {
            if ( e.key === 'Enter' ) {
                handleManualTokenValidation();
            }
        });
    }
}

function handleDisconnect() {
    showTokenValidationStatus( TT.STRINGS.AUTH_STATUS_DISCONNECTING, 'info' );

    TTMessaging.send( TT.MESSAGE.TYPE_DISCONNECT, {} )
        .then( function( response ) {
            if ( response && response.success ) {
                // Auth state change is handled by listenForAuthStateChanges()
                showTokenValidationStatus( TT.STRINGS.AUTH_SUCCESS_DISCONNECTED, 'success' );
            } else {
                var errorMsg = response && response.error
                    ? response.error
                    : TT.STRINGS.AUTH_ERROR_DISCONNECT_FAILED;
                showTokenValidationStatus( errorMsg, 'error' );
            }
        })
        .catch( function() {
            showTokenValidationStatus( TT.STRINGS.AUTH_ERROR_NETWORK, 'error' );
        });
}

function handleManualTokenValidation() {
    var tokenInput = document.getElementById( TT.DOM.ID_OPTIONS_MANUAL_TOKEN_INPUT );
    if ( !tokenInput ) {
        return;
    }

    var token = tokenInput.value.trim();
    if ( !token ) {
        showTokenValidationStatus( TT.STRINGS.AUTH_ERROR_INVALID_FORMAT, 'error' );
        return;
    }

    if ( !TTAuth.isValidTokenFormat( token ) ) {
        showTokenValidationStatus( TT.STRINGS.AUTH_ERROR_INVALID_FORMAT, 'error' );
        return;
    }

    showTokenValidationStatus( TT.STRINGS.AUTH_STATUS_CHECKING, 'info' );

    TTMessaging.send( TT.MESSAGE.TYPE_TOKEN_RECEIVED, { token: token } )
        .then( function( response ) {
            if ( response && response.success && response.data.authorized ) {
                // Auth state change is handled by listenForAuthStateChanges()
                showTokenValidationStatus( TT.STRINGS.AUTH_SUCCESS_VALIDATED, 'success' );
                tokenInput.value = '';
            } else {
                var errorMsg = response && response.data && response.data.error
                    ? response.data.error
                    : TT.STRINGS.AUTH_ERROR_INVALID_TOKEN;
                showTokenValidationStatus( errorMsg, 'error' );
            }
        })
        .catch( function() {
            showTokenValidationStatus( TT.STRINGS.AUTH_ERROR_NETWORK, 'error' );
        });
}

function showTokenValidationStatus( message, type ) {
    var statusDiv = document.getElementById( TT.DOM.ID_OPTIONS_TOKEN_VALIDATION_STATUS );
    if ( statusDiv ) {
        statusDiv.textContent = message;
        statusDiv.className = TT.DOM.CLASS_TOKEN_VALIDATION_STATUS;
        if ( type ) {
            statusDiv.classList.add( 'tt-validation-' + type );
        }
    }
}

function clearTokenValidationStatus() {
    var statusDiv = document.getElementById( TT.DOM.ID_OPTIONS_TOKEN_VALIDATION_STATUS );
    if ( statusDiv ) {
        statusDiv.textContent = '';
        statusDiv.className = TT.DOM.CLASS_TOKEN_VALIDATION_STATUS;
    }
}
