/*
 * Trip Tools Chrome Extension - Popup Script
 * Handles popup UI initialization and user interactions.
 */

document.addEventListener( 'DOMContentLoaded', function() {
    initializePopup();
});

function initializePopup() {
    displayVersion();
    checkBackgroundConnection();
    loadSettings();
    setupEventListeners();
    loadDebugLog();
    checkAuthStatus();
    listenForAuthStateChanges();
}

function listenForAuthStateChanges() {
    chrome.runtime.onMessage.addListener( function( message ) {
        if ( message.type === TT.MESSAGE.TYPE_AUTH_STATE_CHANGED ) {
            if ( message.data.authorized ) {
                showAuthorizedState( message.data.email, message.data.serverStatus );
            } else {
                showNotAuthorizedState();
            }
        }
    });
}

function displayVersion() {
    var defaultDeveloperMode = TT.CONFIG.IS_DEVELOPMENT;

    TTStorage.get( TT.STORAGE.KEY_DEVELOPER_MODE, defaultDeveloperMode )
        .then( function( developerModeEnabled ) {
            var versionSpan = document.getElementById( TT.DOM.ID_VERSION );
            if ( versionSpan ) {
                if ( developerModeEnabled ) {
                    var versionText = 'v' + TT.CONFIG.EXTENSION_VERSION;
                    if ( TT.CONFIG.IS_DEVELOPMENT ) {
                        versionText += ' (DEV)';
                    }
                    versionSpan.textContent = versionText;
                } else {
                    versionSpan.textContent = '';
                }
            }

            if ( TT.CONFIG.IS_DEVELOPMENT ) {
                var header = document.querySelector( '.' + TT.DOM.CLASS_POPUP_HEADER );
                if ( header ) {
                    header.classList.add( TT.DOM.CLASS_DEV_MODE );
                }

                var headerIcon = document.getElementById( TT.DOM.ID_HEADER_ICON );
                if ( headerIcon ) {
                    headerIcon.src = TT.CONFIG.ICON_DEV_48;
                }
            }
        });
}

function checkBackgroundConnection() {
    var indicator = document.getElementById( TT.DOM.ID_STATUS_INDICATOR );
    var statusText = document.getElementById( TT.DOM.ID_STATUS_TEXT );

    TTMessaging.ping()
        .then( function( response ) {
            if ( response && response.success ) {
                // Store uptime for later use when we know auth status
                window.ttBackgroundUptime = response.data.uptime;
                addLocalDebugEntry( 'info', 'Background connection established' );
            } else {
                setDisconnectedStatus( indicator, statusText );
            }
        })
        .catch( function( error ) {
            setDisconnectedStatus( indicator, statusText );
            addLocalDebugEntry( 'error', 'Connection failed: ' + error.message );
        });
}

function setDisconnectedStatus( indicator, statusText ) {
    indicator.classList.remove( TT.DOM.CLASS_CONNECTED );
    indicator.classList.add( TT.DOM.CLASS_DISCONNECTED );
    statusText.textContent = 'Disconnected';
}

function loadSettings() {
    TTStorage.get( TT.STORAGE.KEY_SELECT_DECORATE_ENABLED, true )
        .then( function( enabled ) {
            var toggle = document.getElementById( TT.DOM.ID_DECORATE_TOGGLE );
            if ( toggle ) {
                toggle.checked = enabled;
            }
        });

    loadDebugPanelVisibility();
}

function loadDebugPanelVisibility() {
    var defaultDeveloperMode = TT.CONFIG.IS_DEVELOPMENT;

    TTStorage.get( TT.STORAGE.KEY_DEVELOPER_MODE, defaultDeveloperMode )
        .then( function( developerModeEnabled ) {
            if ( !developerModeEnabled ) {
                return false;
            }
            return TTStorage.get( TT.STORAGE.KEY_DEBUG_PANEL_ENABLED, true );
        })
        .then( function( showDebugPanel ) {
            var panel = document.getElementById( TT.DOM.ID_DEBUG_PANEL );
            if ( panel ) {
                if ( showDebugPanel ) {
                    panel.classList.remove( TT.DOM.CLASS_HIDDEN );
                } else {
                    panel.classList.add( TT.DOM.CLASS_HIDDEN );
                }
            }
        });
}

function setupEventListeners() {
    setupQuickSettingsListeners();
    setupAuthEventListeners();

    var decorateToggle = document.getElementById( TT.DOM.ID_DECORATE_TOGGLE );
    if ( decorateToggle ) {
        decorateToggle.addEventListener( 'change', function() {
            TTStorage.set( TT.STORAGE.KEY_SELECT_DECORATE_ENABLED, this.checked );
            addLocalDebugEntry( 'info', 'Decoration toggled: ' + this.checked );
        });
    }

    var debugHeader = document.getElementById( TT.DOM.ID_DEBUG_HEADER );
    if ( debugHeader ) {
        debugHeader.addEventListener( 'click', function() {
            var content = document.getElementById( TT.DOM.ID_DEBUG_CONTENT );
            var arrow = document.getElementById( TT.DOM.ID_DEBUG_ARROW );
            if ( content.classList.contains( TT.DOM.CLASS_HIDDEN ) ) {
                content.classList.remove( TT.DOM.CLASS_HIDDEN );
                arrow.innerHTML = '&#9660;';
            } else {
                content.classList.add( TT.DOM.CLASS_HIDDEN );
                arrow.innerHTML = '&#9654;';
            }
        });
    }

    setupStubButtonListeners();
}

function setupStubButtonListeners() {
    var stubButtons = document.querySelectorAll( '.' + TT.DOM.CLASS_BTN_STUB );
    stubButtons.forEach( function( button ) {
        button.addEventListener( 'click', function() {
            addLocalDebugEntry( 'info', 'Stub button clicked: ' + this.id );
        });
    });
}

function setupQuickSettingsListeners() {
    var settingsBtn = document.getElementById( TT.DOM.ID_SETTINGS_BTN );
    if ( settingsBtn ) {
        settingsBtn.addEventListener( 'click', function() {
            showQuickSettings();
        });
    }

    var backBtn = document.getElementById( TT.DOM.ID_QUICK_SETTINGS_BACK );
    if ( backBtn ) {
        backBtn.addEventListener( 'click', function() {
            hideQuickSettings();
        });
    }

    var allOptionsLink = document.getElementById( TT.DOM.ID_ALL_OPTIONS_LINK );
    if ( allOptionsLink ) {
        allOptionsLink.addEventListener( 'click', function( e ) {
            e.preventDefault();
            chrome.runtime.openOptionsPage();
        });
    }
}

function showQuickSettings() {
    var panel = document.getElementById( TT.DOM.ID_QUICK_SETTINGS );
    if ( panel ) {
        panel.classList.remove( TT.DOM.CLASS_HIDDEN );
        requestAnimationFrame( function() {
            panel.classList.add( TT.DOM.CLASS_VISIBLE );
        });
    }

    var header = document.getElementById( TT.DOM.ID_QUICK_SETTINGS_HEADER );
    if ( header && TT.CONFIG.IS_DEVELOPMENT ) {
        header.classList.add( TT.DOM.CLASS_DEV_MODE );
    }
}

function hideQuickSettings() {
    var panel = document.getElementById( TT.DOM.ID_QUICK_SETTINGS );
    if ( panel ) {
        panel.classList.remove( TT.DOM.CLASS_VISIBLE );
        panel.addEventListener( 'transitionend', function handler() {
            panel.classList.add( TT.DOM.CLASS_HIDDEN );
            panel.removeEventListener( 'transitionend', handler );
        });
    }
}

function loadDebugLog() {
    TTStorage.get( TT.STORAGE.KEY_DEBUG_LOG, [] )
        .then( function( log ) {
            renderDebugLog( log );
        });

    addLocalDebugEntry( 'info', 'Extension popup loaded' );
}

function renderDebugLog( log ) {
    var logContainer = document.getElementById( TT.DOM.ID_DEBUG_LOG );
    if ( !logContainer ) {
        return;
    }

    logContainer.innerHTML = '';
    var displayLog = log.slice( 0, 10 );
    displayLog.forEach( function( entry ) {
        var entryDiv = document.createElement( 'div' );
        entryDiv.className = 'tt-debug-entry';

        var timestamp = new Date( entry.timestamp ).toLocaleTimeString();
        var levelClass = 'tt-debug-level-' + entry.level;

        // Use textContent to prevent XSS from debug log entries
        var timestampSpan = document.createElement( 'span' );
        timestampSpan.className = 'tt-debug-timestamp';
        timestampSpan.textContent = timestamp;

        var messageSpan = document.createElement( 'span' );
        messageSpan.className = levelClass;
        messageSpan.textContent = entry.message;

        entryDiv.appendChild( timestampSpan );
        entryDiv.appendChild( messageSpan );

        logContainer.appendChild( entryDiv );
    });
}

function addLocalDebugEntry( level, message ) {
    TTStorage.get( TT.STORAGE.KEY_DEBUG_LOG, [] )
        .then( function( log ) {
            var entry = {
                timestamp: Date.now(),
                level: level,
                message: message
            };
            log.unshift( entry );
            if ( log.length > TT.CONFIG.DEBUG_LOG_MAX_ENTRIES ) {
                log = log.slice( 0, TT.CONFIG.DEBUG_LOG_MAX_ENTRIES );
            }
            return TTStorage.set( TT.STORAGE.KEY_DEBUG_LOG, log );
        })
        .then( function() {
            return TTStorage.get( TT.STORAGE.KEY_DEBUG_LOG, [] );
        })
        .then( function( log ) {
            renderDebugLog( log );
        });
}

function checkAuthStatus() {
    TTMessaging.send( TT.MESSAGE.TYPE_AUTH_STATUS_REQUEST, {} )
        .then( function( response ) {
            if ( response && response.success && response.data.authorized ) {
                showAuthorizedState( response.data.email, response.data.serverStatus );
            } else {
                showNotAuthorizedState();
            }
        })
        .catch( function( error ) {
            showNotAuthorizedState();
            addLocalDebugEntry( 'error', 'Auth check failed: ' + error.message );
        });
}

function showAuthorizedState( email, serverStatus ) {
    var authSection = document.getElementById( TT.DOM.ID_AUTH_SECTION );
    if ( authSection ) {
        authSection.classList.add( TT.DOM.CLASS_HIDDEN );
    }

    // Update status bar based on server status
    var indicator = document.getElementById( TT.DOM.ID_STATUS_INDICATOR );
    var statusText = document.getElementById( TT.DOM.ID_STATUS_TEXT );
    if ( indicator && statusText ) {
        // Remove all state classes
        indicator.classList.remove(
            TT.DOM.CLASS_CONNECTED,
            TT.DOM.CLASS_DISCONNECTED,
            TT.DOM.CLASS_OFFLINE,
            TT.DOM.CLASS_SERVER_ERROR
        );

        switch ( serverStatus ) {
            case TT.AUTH.STATUS_OFFLINE:
                indicator.classList.add( TT.DOM.CLASS_OFFLINE );
                statusText.textContent = TT.STRINGS.STATUS_OFFLINE;
                break;
            case TT.AUTH.STATUS_SERVER_ERROR:
                indicator.classList.add( TT.DOM.CLASS_SERVER_ERROR );
                statusText.textContent = TT.STRINGS.STATUS_SERVER_ERROR;
                break;
            case TT.AUTH.STATUS_TIMEOUT:
                indicator.classList.add( TT.DOM.CLASS_SERVER_ERROR );
                statusText.textContent = TT.STRINGS.STATUS_TIMEOUT;
                break;
            default:
                indicator.classList.add( TT.DOM.CLASS_CONNECTED );
                var uptimeSec = Math.floor( ( window.ttBackgroundUptime || 0 ) / 1000 );
                statusText.textContent = TT.STRINGS.STATUS_ONLINE + ' (uptime: ' + uptimeSec + 's)';
        }
    }

    updateDebugAuthInfo( email );
}

function showNotAuthorizedState() {
    var authSection = document.getElementById( TT.DOM.ID_AUTH_SECTION );
    if ( authSection ) {
        authSection.classList.remove( TT.DOM.CLASS_HIDDEN );

        var authStatus = document.getElementById( TT.DOM.ID_AUTH_STATUS );
        if ( authStatus ) {
            authStatus.textContent = TT.STRINGS.AUTH_PROMPT_CONNECT;
        }
    }

    // Update status bar to show not connected
    var indicator = document.getElementById( TT.DOM.ID_STATUS_INDICATOR );
    var statusText = document.getElementById( TT.DOM.ID_STATUS_TEXT );
    if ( indicator && statusText ) {
        indicator.classList.remove( TT.DOM.CLASS_CONNECTED );
        indicator.classList.add( TT.DOM.CLASS_DISCONNECTED );
        statusText.textContent = 'Not connected';
    }

    updateDebugAuthInfo( null );
}

function setupAuthEventListeners() {
    var authorizeBtn = document.getElementById( TT.DOM.ID_AUTHORIZE_BTN );
    if ( authorizeBtn ) {
        authorizeBtn.addEventListener( 'click', function() {
            openAuthorizePage();
        });
    }
}

function openAuthorizePage() {
    var defaultUrl = TT.CONFIG.IS_DEVELOPMENT
        ? TT.CONFIG.DEFAULT_SERVER_URL_DEV
        : TT.CONFIG.DEFAULT_SERVER_URL_PROD;

    TTStorage.get( TT.STORAGE.KEY_SERVER_URL, defaultUrl )
        .then( function( serverUrl ) {
            var authUrl = serverUrl + TT.CONFIG.EXTENSION_AUTHORIZE_PATH;
            chrome.tabs.create( { url: authUrl } );
        });
}

function updateDebugAuthInfo( email ) {
    var authInfo = document.getElementById( TT.DOM.ID_DEBUG_AUTH_INFO );
    if ( !authInfo ) {
        return;
    }

    // Clear existing content
    authInfo.innerHTML = '';

    var entryDiv = document.createElement( 'div' );
    entryDiv.className = 'tt-debug-entry';

    var messageSpan = document.createElement( 'span' );

    if ( email ) {
        messageSpan.className = 'tt-debug-level-info';
        // Use textContent to prevent XSS from email values
        messageSpan.textContent = TT.STRINGS.DEBUG_USER_EMAIL + ': ' + email;
    } else {
        messageSpan.className = 'tt-debug-level-warning';
        messageSpan.textContent = TT.STRINGS.AUTH_STATUS_NOT_AUTHORIZED;
    }

    entryDiv.appendChild( messageSpan );
    authInfo.appendChild( entryDiv );
}
