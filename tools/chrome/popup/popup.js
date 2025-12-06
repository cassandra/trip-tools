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
}

function displayVersion() {
    var versionSpan = document.getElementById( TT.DOM.ID_VERSION );
    if ( versionSpan ) {
        var versionText = 'v' + TT.CONFIG.EXTENSION_VERSION;
        if ( TT.CONFIG.IS_DEVELOPMENT ) {
            versionText += ' (DEV)';
        }
        versionSpan.textContent = versionText;
    }

    if ( TT.CONFIG.IS_DEVELOPMENT ) {
        var header = document.querySelector( '.tt-popup-header' );
        if ( header ) {
            header.classList.add( TT.DOM.CLASS_DEV_MODE );
        }

        var headerIcon = document.getElementById( TT.DOM.ID_HEADER_ICON );
        if ( headerIcon ) {
            headerIcon.src = TT.CONFIG.ICON_DEV_48;
        }
    }
}

function checkBackgroundConnection() {
    var indicator = document.getElementById( TT.DOM.ID_STATUS_INDICATOR );
    var statusText = document.getElementById( TT.DOM.ID_STATUS_TEXT );

    TTMessaging.ping()
        .then( function( response ) {
            if ( response && response.success ) {
                indicator.classList.remove( TT.DOM.CLASS_DISCONNECTED );
                indicator.classList.add( TT.DOM.CLASS_CONNECTED );
                var uptimeSec = Math.floor( response.data.uptime / 1000 );
                statusText.textContent = 'Connected (uptime: ' + uptimeSec + 's)';
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
        entryDiv.innerHTML = '<span class="tt-debug-timestamp">' + timestamp + '</span>' +
                            '<span class="' + levelClass + '">' + entry.message + '</span>';

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
