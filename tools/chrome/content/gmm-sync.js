/*
 * Trip Tools Chrome Extension - GMM Location Sync
 * Handles location synchronization between GMM and Trip Tools server.
 */

( function() {
    'use strict';

    var TT_SYNC_DIALOG_CLASS = 'tt-sync-dialog';

    // Distance threshold for coordinate validation (meters)
    var COORDINATE_DISTANCE_THRESHOLD_M = 1000;

    // Cancellation state for sync execute phase
    var _executeStopRequested = false;

    // Fix mode context - stores the server location being fixed
    var _fixContext = null;

    // Current trip data - stored for post-fix comparison
    var _currentTripData = null;

    // Warning types for post-sync review
    var WARNING_TYPE = {
        NO_CATEGORY: 'no_category',
        UNKNOWN_CATEGORY: 'unknown_category',
        MULTIPLE_RESULTS: 'multiple_results',
        COORDINATE_MISMATCH: 'coordinate_mismatch',
        LAYER_LIMIT: 'layer_limit'
    };

    // Error types for sync failures
    var ERROR_TYPE = {
        NO_RESULTS: 'no_results',
        NO_DIALOG: 'no_dialog',
        TOO_MANY_RESULTS: 'too_many_results'
    };

    // Human-readable warning messages
    var WARNING_MESSAGES = {};
    WARNING_MESSAGES[WARNING_TYPE.NO_CATEGORY] = "Added to 'Other' layer - move to correct layer";
    WARNING_MESSAGES[WARNING_TYPE.UNKNOWN_CATEGORY] = "Unknown category - added to 'Other' layer";
    WARNING_MESSAGES[WARNING_TYPE.MULTIPLE_RESULTS] = "Multiple matches found - verify location is correct";
    WARNING_MESSAGES[WARNING_TYPE.COORDINATE_MISMATCH] = "Location may not match - verify location is correct";
    WARNING_MESSAGES[WARNING_TYPE.LAYER_LIMIT] = "Could not create 'Other' layer - added to first layer";

    // Human-readable error messages
    var ERROR_MESSAGES = {};
    ERROR_MESSAGES[ERROR_TYPE.NO_RESULTS] = "No search results found";
    ERROR_MESSAGES[ERROR_TYPE.NO_DIALOG] = "Multiple matches found, none selected";
    ERROR_MESSAGES[ERROR_TYPE.TOO_MANY_RESULTS] = "Too many matches - search manually";

    /**
     * Calculate distance between two points using Haversine formula.
     * @param {number} lat1 - Latitude of first point.
     * @param {number} lon1 - Longitude of first point.
     * @param {number} lat2 - Latitude of second point.
     * @param {number} lon2 - Longitude of second point.
     * @returns {number} Distance in meters.
     */
    function calculateDistanceMeters( lat1, lon1, lat2, lon2 ) {
        var R = 6371000; // Earth's radius in meters
        var dLat = ( lat2 - lat1 ) * Math.PI / 180;
        var dLon = ( lon2 - lon1 ) * Math.PI / 180;
        var a = Math.sin( dLat / 2 ) * Math.sin( dLat / 2 ) +
                Math.cos( lat1 * Math.PI / 180 ) * Math.cos( lat2 * Math.PI / 180 ) *
                Math.sin( dLon / 2 ) * Math.sin( dLon / 2 );
        var c = 2 * Math.atan2( Math.sqrt( a ), Math.sqrt( 1 - a ) );
        return R * c;
    }

    /**
     * Initialize sync functionality.
     * Sets up message listener for sync requests.
     */
    function initSync() {
        console.log( '[TT GMM Sync] Initializing sync module' );
        chrome.runtime.onMessage.addListener( handleSyncMessage );
    }

    /**
     * Handle incoming sync messages from background/popup.
     * @param {Object} message - The message object.
     * @param {Object} sender - Message sender info.
     * @param {Function} sendResponse - Response callback.
     * @returns {boolean} True to indicate async response.
     */
    function handleSyncMessage( message, sender, sendResponse ) {
        if ( message.type === TT.MESSAGE.TYPE_GMM_SYNC_LOCATIONS ) {
            console.log( '[TT GMM Sync] Received sync request:', message.data );
            performSync( message.data )
                .then( function( result ) {
                    sendResponse( { success: true, data: result } );
                })
                .catch( function( error ) {
                    sendResponse( { success: false, error: error.message } );
                });
            return true; // Async response
        }
        return false;
    }

    // Track if a sync is currently in progress to prevent duplicate requests
    var _syncInProgress = false;

    /**
     * Perform the sync operation: fetch data, compare, show dialog, execute.
     * @param {Object} data - Sync request data (tripUuid, tripTitle, mapId).
     * @returns {Promise<Object>} Result of sync operation.
     */
    function performSync( data ) {
        // Guard against duplicate sync requests (e.g., from service worker retries after page reload)
        if ( _syncInProgress ) {
            console.log( '[TT GMM Sync] Sync already in progress, ignoring duplicate request' );
            return Promise.resolve( { cancelled: true, reason: 'sync_in_progress' } );
        }

        _syncInProgress = true;
        _currentTripData = data;  // Store for fix mode
        console.log( '[TT Sync Compare] Fetching locations...' );

        return Promise.all( [
            fetchServerLocations( data.tripUuid ),
            getGmmLocations()
        ])
        .then( function( results ) {
            var serverLocations = results[0];
            var gmmLocations = results[1];

            console.log( '[TT Sync Compare] Server locations:', serverLocations.length );
            console.log( '[TT Sync Compare] GMM locations:', gmmLocations.length );

            var diff = compareLocations( serverLocations, gmmLocations );

            console.log( '[TT Sync Compare] Diff results:', {
                serverOnly: diff.serverOnly.length,
                gmmOnly: diff.gmmOnly.length,
                inBoth: diff.inBoth.length
            });

            return showSyncCompareDialog( data, diff );
        })
        .then( function( dialogResult ) {
            if ( dialogResult.cancelled ) {
                console.log( '[TT GMM Sync] Sync cancelled by user' );
                return { cancelled: true };
            }

            console.log( '[TT Sync Execute] Starting with decisions:', dialogResult.decisions );
            return executeSyncDecisions( data.tripUuid, dialogResult.decisions );
        })
        .then( function( results ) {
            if ( results.cancelled ) {
                return results;
            }

            // Show execute results dialog (don't wait for it to close)
            showSyncExecuteResultsDialog( results );
            return results;
        })
        .finally( function() {
            _syncInProgress = false;
        });
    }

    /**
     * Check if sync execute was stopped and throw if so.
     * @private
     */
    function checkExecuteStopped() {
        if ( _executeStopRequested ) {
            throw new Error( 'Sync execute stopped by user' );
        }
    }

    /**
     * Execute sync decisions from the dialog.
     * @param {string} tripUuid - Trip UUID.
     * @param {Object} decisions - Map of itemId to { action, source, location/server/gmm }.
     * @returns {Promise<Object>} Sync results with three-tier structure.
     */
    function executeSyncDecisions( tripUuid, decisions ) {
        var gmmToServerKeep = [];
        var gmmToDiscard = [];
        var serverToGmmKeep = [];
        var serverToDiscard = [];
        var matchesToLink = [];      // { server, gmm } - title matches to link
        var matchesToSeparate = [];  // { server, gmm } - title matches NOT to link

        // Categorize decisions
        Object.keys( decisions ).forEach( function( itemId ) {
            var decision = decisions[itemId];
            if ( decision.source === 'gmm' && decision.action === 'keep' ) {
                gmmToServerKeep.push( decision.location );
            } else if ( decision.source === 'gmm' && decision.action === 'discard' ) {
                gmmToDiscard.push( decision.location );
            } else if ( decision.source === 'server' && decision.action === 'keep' ) {
                serverToGmmKeep.push( decision.location );
            } else if ( decision.source === 'server' && decision.action === 'discard' ) {
                serverToDiscard.push( decision.location );
            } else if ( decision.source === 'match' && decision.action === 'link' ) {
                matchesToLink.push( { server: decision.server, gmm: decision.gmm } );
            } else if ( decision.source === 'match' && decision.action === 'dont_link' ) {
                matchesToSeparate.push( { server: decision.server, gmm: decision.gmm } );
            }
        });

        // For "don't link" matches, add both locations to their respective queues
        matchesToSeparate.forEach( function( match ) {
            serverToGmmKeep.push( match.server );
            gmmToServerKeep.push( match.gmm );
        });

        console.log( '[TT Sync Execute] GMM->Server (keep):', gmmToServerKeep.length );
        console.log( '[TT Sync Execute] GMM (discard):', gmmToDiscard.length );
        console.log( '[TT Sync Execute] Server->GMM (keep):', serverToGmmKeep.length );
        console.log( '[TT Sync Execute] Server (discard):', serverToDiscard.length );
        console.log( '[TT Sync Execute] Title matches to link:', matchesToLink.length );

        // Three-tier results structure
        var results = {
            // Successes: linked with no warnings
            addedToServer: [],      // { gmm, server } - GMM -> Server
            addedToGmm: [],         // { server, gmm } - Server -> GMM (no warnings)
            linkedByTitle: [],      // { server, gmm } - linked via title match (no GMM manipulation)
            deletedFromServer: [],  // Server locations discarded
            deletedFromGmm: [],     // GMM locations discarded

            // Warnings: linked but need review
            warnings: [],           // { server, gmm, warnings: [] } - Server -> GMM with warnings

            // Failures: could not link
            failures: [],           // { server, error, resultCount? }

            // Unexpected errors (catch-all)
            errors: [],             // { location, error }

            // Cancellation flag
            stopped: false
        };

        // Reset cancellation state and enter sync execute mode
        _executeStopRequested = false;
        TTOperationMode.enter( TTOperationMode.Mode.GMM_SYNC_EXECUTE, {
            onStop: function() {
                console.log( '[TT Sync Execute] Stop requested' );
                _executeStopRequested = true;
            }
        });

        // Execute syncs sequentially (need to click each location)
        var syncPromise = Promise.resolve();

        // Title matches to link: just update gmm_id on server (no GMM manipulation)
        matchesToLink.forEach( function( match ) {
            syncPromise = syncPromise.then( function() {
                checkExecuteStopped();
                console.log( '[TT Sync Execute] Linking by title:', match.server.title );
                return updateServerLocationGmmId( match.server.uuid, match.gmm.fl_id )
                    .then( function() {
                        results.linkedByTitle.push( { server: match.server, gmm: match.gmm } );
                    })
                    .catch( function( error ) {
                        console.error( '[TT Sync Execute] Error linking by title:', match.server.title, error );
                        results.errors.push( { location: match.server, error: error.message } );
                    });
            });
        });

        // GMM -> Server (keep): add to server
        gmmToServerKeep.forEach( function( gmmLoc ) {
            syncPromise = syncPromise.then( function() {
                checkExecuteStopped();
                return syncGmmLocationToServer( tripUuid, gmmLoc )
                    .then( function( serverLoc ) {
                        results.addedToServer.push( { gmm: gmmLoc, server: serverLoc } );
                    })
                    .catch( function( error ) {
                        console.error( '[TT GMM Sync] Error syncing to server:', gmmLoc.title, error );
                        results.errors.push( { location: gmmLoc, error: error.message } );
                    });
            });
        });

        // GMM (discard): delete from GMM
        gmmToDiscard.forEach( function( gmmLoc ) {
            syncPromise = syncPromise.then( function() {
                checkExecuteStopped();
                return deleteGmmLocation( gmmLoc.fl_id )
                    .then( function() {
                        results.deletedFromGmm.push( gmmLoc );
                    })
                    .catch( function( error ) {
                        console.error( '[TT GMM Sync] Error deleting from GMM:', gmmLoc.title, error );
                        results.errors.push( { location: gmmLoc, error: error.message } );
                    });
            });
        });

        // Server -> GMM (keep): add to GMM
        serverToGmmKeep.forEach( function( serverLoc ) {
            syncPromise = syncPromise.then( function() {
                checkExecuteStopped();
                return syncServerLocationToGmm( serverLoc )
                    .then( function( syncResult ) {
                        if ( syncResult.success ) {
                            if ( syncResult.warnings && syncResult.warnings.length > 0 ) {
                                // Success with warnings - goes to warnings tier
                                results.warnings.push({
                                    server: serverLoc,
                                    gmm: syncResult.gmm,
                                    warnings: syncResult.warnings
                                });
                            } else {
                                // Clean success - goes to success tier
                                results.addedToGmm.push({
                                    server: serverLoc,
                                    gmm: syncResult.gmm
                                });
                            }
                        } else {
                            // Failure - goes to failures tier
                            results.failures.push({
                                server: serverLoc,
                                error: syncResult.error,
                                resultCount: syncResult.resultCount
                            });
                        }
                    })
                    .catch( function( error ) {
                        console.error( '[TT GMM Sync] Error syncing to GMM:', serverLoc.title, error );
                        results.errors.push( { location: serverLoc, error: error.message } );
                    });
            });
        });

        // Server (discard): delete from server
        serverToDiscard.forEach( function( serverLoc ) {
            syncPromise = syncPromise.then( function() {
                checkExecuteStopped();
                return deleteServerLocation( serverLoc.uuid )
                    .then( function() {
                        results.deletedFromServer.push( serverLoc );
                    })
                    .catch( function( error ) {
                        console.error( '[TT GMM Sync] Error deleting from server:', serverLoc.title, error );
                        results.errors.push( { location: serverLoc, error: error.message } );
                    });
            });
        });

        return syncPromise
            .then( function() {
                console.log( '[TT Sync Execute] Complete:', results );
                return results;
            })
            .catch( function( error ) {
                if ( error.message === 'Sync execute stopped by user' ) {
                    console.log( '[TT Sync Execute] Stopped by user' );
                    results.stopped = true;
                    return results;
                }
                throw error;
            })
            .finally( function() {
                // Always exit operation mode when done
                TTOperationMode.exit();
            });
    }

    /**
     * Delete a location from GMM.
     * @param {string} gmmId - GMM location ID (fl_id).
     * @returns {Promise<void>}
     */
    function deleteGmmLocation( gmmId ) {
        console.log( '[TT GMM Sync] Deleting GMM location:', gmmId );
        return TTGmmAdapter.deleteLocationById( gmmId )
            .then( function() {
                return TTGmmAdapter.closeInfoWindow();
            });
    }

    /**
     * Handle UNDO button click in results dialog.
     * Deletes the GMM location and updates the row.
     * @param {Element} dialog - The results dialog element.
     * @param {Element} row - The row element containing the Undo button.
     * @param {string} gmmId - The GMM location ID to delete.
     * @param {string} title - The location title for display.
     */
    function handleUndoClick( dialog, row, gmmId, title ) {
        console.log( '[TT Sync Execute] Undo clicked for:', title, 'gmmId:', gmmId );

        // Find the undo button and disable it immediately to prevent double-clicks
        var undoBtn = row.querySelector( '.tt-sync-action-btn' );
        if ( undoBtn ) {
            undoBtn.disabled = true;
        }

        // Dim the row
        row.classList.add( 'tt-sync-row-removing' );

        // Enter SYNC_UNDO mode - shows banner and prevents dialog decoration
        TTOperationMode.enter( TTOperationMode.Mode.GMM_SYNC_UNDO, {
            message: "'" + title + "'..."
        });

        // Delete the GMM location
        deleteGmmLocation( gmmId )
            .then( function() {
                console.log( '[TT Sync Execute] Undo successful for:', title );

                // Update row to show REMOVED status
                row.classList.remove( 'tt-sync-row-removing' );

                // Clear the row and rebuild as a simple "removed" row
                // Find the title element and actions element
                var titleRow = row.querySelector( '.tt-sync-result-row' ) || row;
                var actionsEl = titleRow.querySelector( '.tt-sync-result-actions' );
                if ( actionsEl ) {
                    // Replace actions with REMOVED status only (no undo button)
                    actionsEl.innerHTML = '';
                    var statusEl = TTDom.createElement( 'span', {
                        className: 'tt-sync-status tt-sync-status-removed',
                        text: 'REMOVED'
                    });
                    actionsEl.appendChild( statusEl );
                }

                // Remove any "Matched to" message since item is now removed
                var matchedMsg = row.querySelector( '.tt-sync-item-matched' );
                if ( matchedMsg ) {
                    matchedMsg.remove();
                }

                // Remove any warning messages since item is now removed
                var warningMsgs = row.querySelectorAll( '.tt-sync-item-message-warning' );
                warningMsgs.forEach( function( msg ) {
                    msg.remove();
                });
            })
            .catch( function( error ) {
                console.error( '[TT Sync Execute] Undo failed for:', title, error );

                // Restore row
                row.classList.remove( 'tt-sync-row-removing' );

                // Re-enable undo button
                if ( undoBtn ) {
                    undoBtn.disabled = false;
                }

                // Show error message on the row
                var errorMsg = TTDom.createElement( 'div', {
                    className: 'tt-sync-undo-error',
                    text: '\u26A0 Failed to remove: ' + ( error.message || error )
                });
                row.appendChild( errorMsg );
            })
            .finally( function() {
                // Always exit operation mode
                TTOperationMode.exit();
            });
    }

    // =========================================================================
    // FIX Mode Functions
    // =========================================================================

    /**
     * Enter FIX mode for a failed server location.
     * Pre-fills search box and sets up fix context.
     * @param {Object} serverLocation - The server location to fix.
     * @param {string} failureReason - The error type that caused the failure.
     */
    function enterFixMode( serverLocation, failureReason ) {
        console.log( '[TT Sync Fix] Entering fix mode for:', serverLocation.title );

        // Store context
        _fixContext = {
            serverLocation: serverLocation,
            failureReason: failureReason
        };

        // Close the results dialog
        var resultsDialog = document.querySelector( '.' + TT_SYNC_DIALOG_CLASS );
        if ( resultsDialog ) {
            resultsDialog.remove();
        }

        // Enter FIX mode with banner
        TTOperationMode.enter( TTOperationMode.Mode.GMM_SYNC_FIX, {
            message: "Fixing '" + serverLocation.title + "' \u2014 Find the location, then click Link",
            onStop: exitFixMode
        });

        // Fill search box with server title and submit the search
        var searchField = document.querySelector( TTGmmAdapter.selectors.SEARCH_FIELD );
        if ( searchField ) {
            var searchTitle = serverLocation.title;
            TTDom.setInputValue( searchField, searchTitle );

            // Submit the search so results appear
            TTGmmAdapter.submitSearch()
                .then( function() {
                    // Wait for GMM to clear the field (indicates search is processed)
                    return new Promise( function( resolve ) {
                        var checkInterval = setInterval( function() {
                            if ( searchField.value === '' ) {
                                clearInterval( checkInterval );
                                resolve();
                            }
                        }, 100 );
                        // Timeout after 5 seconds
                        setTimeout( function() {
                            clearInterval( checkInterval );
                            resolve();
                        }, 5000 );
                    });
                })
                .then( function() {
                    // Re-populate the field so user sees what was searched
                    TTDom.setInputValue( searchField, searchTitle );
                    searchField.focus();
                })
                .catch( function( error ) {
                    console.error( '[TT Sync Fix] Error submitting search:', error );
                });
        }
    }

    /**
     * Exit FIX mode and clean up.
     */
    function exitFixMode() {
        console.log( '[TT Sync Fix] Exiting fix mode' );
        _fixContext = null;
        TTOperationMode.exit();
    }

    /**
     * Get current fix context (for gmm.js to access).
     * @returns {Object|null} Fix context or null if not in fix mode.
     */
    function getFixContext() {
        return _fixContext;
    }

    var TT_FIX_DECORATED_ATTR = 'data-tt-fix-decorated';

    /**
     * Decorate add-to-map dialog in FIX mode.
     * Hides native button, shows "Link This Location" button instead.
     * @param {Element} dialogNode - The dialog element.
     */
    function decorateFixModeDialog( dialogNode ) {
        // Guard against multiple decoration
        if ( dialogNode.getAttribute( TT_FIX_DECORATED_ATTR ) ) {
            return;
        }
        dialogNode.setAttribute( TT_FIX_DECORATED_ATTR, 'true' );

        var addButton = dialogNode.querySelector( TTGmmAdapter.selectors.ADD_TO_MAP_BUTTON );
        if ( !addButton ) {
            console.warn( '[TT Sync Fix] Add to map button not found in dialog' );
            return;
        }

        // Hide native button
        addButton.style.display = 'none';

        var container = addButton.parentNode;

        // Create Link button container
        var buttonContainer = TTDom.createElement( 'div', {
            className: 'tt-fix-mode-buttons'
        });

        // Create Link This Location button
        var linkButton = TTDom.createElement( 'button', {
            className: 'tt-gmm-btn tt-category-btn tt-fix-link-btn',
            text: 'Link This Location'
        });

        linkButton.addEventListener( 'click', function( event ) {
            event.stopPropagation();
            handleFixLinkClick( dialogNode, linkButton );
        });

        buttonContainer.appendChild( linkButton );
        container.appendChild( buttonContainer );

        console.log( '[TT Sync Fix] Dialog decorated with Link button' );
    }

    /**
     * Handle "Link This Location" button click in FIX mode.
     * Adds the location with correct styling and updates server.
     * @param {Element} dialogNode - The dialog element.
     * @param {Element} linkButton - The Link button element.
     */
    function handleFixLinkClick( dialogNode, linkButton ) {
        if ( !_fixContext ) {
            console.error( '[TT Sync Fix] No fix context available' );
            return;
        }

        var serverLoc = _fixContext.serverLocation;
        console.log( '[TT Sync Fix] Linking location:', serverLoc.title );

        // Disable button to prevent double-clicks
        linkButton.disabled = true;
        linkButton.textContent = 'Linking...';

        var resultData = null;

        // Get styling options from server location's subcategory
        getStyleOptionsForLocation( serverLoc )
            .then( function( styleOptions ) {
                // Add custom title to rename if needed
                styleOptions.customTitle = serverLoc.title;

                console.log( '[TT Sync Fix] Adding with style options:', styleOptions );

                // Add the location to GMM with proper layer/icon/color
                return TTGmmAdapter.addLocationToLayer( styleOptions );
            })
            .then( function( result ) {
                console.log( '[TT Sync Fix] Location added to GMM:', result );
                resultData = result;

                // Update server location with gmm_id
                return updateServerLocationGmmId( serverLoc.uuid, result.gmmId );
            })
            .then( function() {
                console.log( '[TT Sync Fix] Server updated with gmm_id' );

                // Close info window
                return TTGmmAdapter.closeInfoWindow();
            })
            .then( function() {
                // Clear search results to leave map clean
                return TTGmmAdapter.clearSearchResults();
            })
            .then( function() {
                // Capture fixed location before clearing context
                var fixedLoc = _fixContext.serverLocation;

                // Exit fix mode
                exitFixMode();

                // Show fix complete dialog with fresh sync comparison
                showFixCompleteDialog( fixedLoc, resultData );
            })
            .catch( function( error ) {
                console.error( '[TT Sync Fix] Fix failed:', error );

                // Re-enable button
                linkButton.disabled = false;
                linkButton.textContent = 'Link This Location';

                // Show error (stay in FIX mode so user can try again)
                showErrorNotification( 'Failed to link location: ' + error.message );
            });
    }

    /**
     * Show error notification banner.
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

        // Style inline to ensure it displays correctly
        notification.style.cssText = [
            'position: fixed',
            'top: 60px',
            'left: 50%',
            'transform: translateX(-50%)',
            'background: #d93025',
            'color: white',
            'padding: 12px 24px',
            'border-radius: 8px',
            'font-family: "Google Sans", Roboto, Arial, sans-serif',
            'font-size: 14px',
            'box-shadow: 0 4px 12px rgba(0,0,0,0.3)',
            'z-index: 100000',
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
     * Show fix complete dialog with fresh sync comparison.
     * @param {Object} serverLoc - The server location that was fixed.
     * @param {Object} resultData - The GMM result from addLocationToLayer.
     */
    function showFixCompleteDialog( serverLoc, resultData ) {
        console.log( '[TT Sync Fix] Showing fix complete dialog' );

        // Create dialog
        var dialog = TTDom.createElement( 'div', {
            className: TT_SYNC_DIALOG_CLASS
        });

        // Header
        dialog.appendChild( TTDom.createElement( 'div', {
            className: 'tt-sync-header',
            text: 'Fix Complete'
        }));

        // Success message
        dialog.appendChild( TTDom.createElement( 'div', {
            className: 'tt-sync-in-sync-message',
            text: "Successfully linked '" + serverLoc.title + "'"
        }));

        // Loading indicator for comparison
        var loadingDiv = TTDom.createElement( 'div', {
            className: 'tt-loading',
            text: 'Checking sync status...'
        });
        dialog.appendChild( loadingDiv );

        // Button container
        var buttonContainer = TTDom.createElement( 'div', {
            className: 'tt-sync-buttons'
        });

        var closeBtn = TTDom.createElement( 'button', {
            className: 'tt-gmm-btn tt-cancel-btn',
            text: 'Close'
        });
        closeBtn.addEventListener( 'click', function() {
            dialog.remove();
        });
        buttonContainer.appendChild( closeBtn );

        dialog.appendChild( buttonContainer );
        document.body.appendChild( dialog );

        // Fetch fresh comparison
        fetchFreshComparison()
            .then( function( diff ) {
                loadingDiv.remove();

                var hasRemaining = diff.serverOnly.length > 0 || diff.gmmOnly.length > 0 ||
                                  diff.suggestedMatches.length > 0;

                if ( hasRemaining ) {
                    // Show comparison summary
                    var summaryDiv = renderSyncComparisonSummary( diff );
                    buttonContainer.parentNode.insertBefore( summaryDiv, buttonContainer );

                    // Add "Sync Again" button
                    var syncAgainBtn = TTDom.createElement( 'button', {
                        className: 'tt-gmm-btn tt-category-btn',
                        text: 'Sync Again'
                    });
                    syncAgainBtn.addEventListener( 'click', function() {
                        dialog.remove();
                        performSync( _currentTripData );
                    });
                    buttonContainer.insertBefore( syncAgainBtn, closeBtn );
                } else {
                    // All in sync!
                    buttonContainer.parentNode.insertBefore( TTDom.createElement( 'div', {
                        className: 'tt-sync-in-sync-message',
                        text: 'All locations are now in sync!'
                    }), buttonContainer );
                }
            })
            .catch( function( error ) {
                console.error( '[TT Sync Fix] Failed to get comparison:', error );
                loadingDiv.textContent = 'Could not check sync status';
            });
    }

    /**
     * Fetch fresh sync comparison for current trip.
     * @returns {Promise<Object>} Diff results.
     */
    function fetchFreshComparison() {
        if ( !_currentTripData ) {
            return Promise.reject( new Error( 'No trip data available' ) );
        }

        return Promise.all( [
            fetchServerLocations( _currentTripData.tripUuid ),
            getGmmLocations()
        ])
        .then( function( results ) {
            var serverLocations = results[0];
            var gmmLocations = results[1];
            return compareLocations( serverLocations, gmmLocations );
        });
    }

    /**
     * Render sync comparison summary into a container.
     * @param {Object} diff - Diff results from compareLocations.
     * @returns {Element} The summary container element.
     */
    function renderSyncComparisonSummary( diff ) {
        var container = TTDom.createElement( 'div', {
            className: 'tt-sync-section'
        });

        container.appendChild( TTDom.createElement( 'div', {
            className: 'tt-sync-section-header',
            text: 'Remaining Issues'
        }));

        var parts = [];
        if ( diff.serverOnly.length > 0 ) {
            parts.push( diff.serverOnly.length + ' server-only' );
        }
        if ( diff.gmmOnly.length > 0 ) {
            parts.push( diff.gmmOnly.length + ' GMM-only' );
        }
        if ( diff.suggestedMatches.length > 0 ) {
            parts.push( diff.suggestedMatches.length + ' to link' );
        }

        container.appendChild( TTDom.createElement( 'div', {
            className: 'tt-sync-summary',
            text: parts.join( ', ' )
        }));

        return container;
    }

    /**
     * Sync a server location to GMM.
     * Searches for the location by title and adds it to the map.
     *
     * Three-tier results:
     * - Success: Location added and linked (may have no warnings)
     * - Warning: Location added and linked, but needs user review
     * - Failure: Location could not be added
     *
     * @param {Object} serverLoc - Server location object.
     * @returns {Promise<Object>} Result:
     *   - Success: { success: true, gmm, warnings: [] }
     *   - Failure: { success: false, error: ERROR_TYPE, resultCount? }
     */
    function syncServerLocationToGmm( serverLoc ) {
        console.log( '[TT GMM Sync] Syncing server location to GMM:', serverLoc.title );

        var styleOptions;
        var accumulatedWarnings = [];

        // Get styling info from category (may add warnings for Other layer fallback)
        return getStyleOptionsForLocation( serverLoc )
            .then( function( options ) {
                styleOptions = options;

                // Collect any warnings from style options (no category, unknown category)
                if ( options.warnings && options.warnings.length > 0 ) {
                    accumulatedWarnings = accumulatedWarnings.concat( options.warnings );
                }

                console.log( '[TT GMM Sync] Style options:', styleOptions );

                // Add custom title to rename GMM location to server title
                styleOptions.customTitle = serverLoc.title;

                // Search and add to GMM
                return TTGmmAdapter.searchAndAddLocation( serverLoc.title, styleOptions );
            })
            .then( function( result ) {
                // Clear search results for error cases (success cases clear later)
                if ( result.error ) {
                    return TTGmmAdapter.clearSearchResults()
                        .then( function() {
                            return result;
                        });
                }
                return result;
            })
            .then( function( result ) {
                console.log( '[TT GMM Sync] Search result:', result );

                // Check for error results from searchAndAddLocation
                if ( result.error ) {
                    if ( result.error === 'no_results' ) {
                        console.log( '[TT GMM Sync] No results for:', serverLoc.title );
                        return { success: false, error: ERROR_TYPE.NO_RESULTS };
                    }
                    if ( result.error === 'no_dialog' ) {
                        console.log( '[TT GMM Sync] No dialog opened for:', serverLoc.title,
                            '- result count:', result.resultCount );
                        return {
                            success: false,
                            error: ERROR_TYPE.NO_DIALOG,
                            resultCount: result.resultCount
                        };
                    }
                    // Handle too many results error
                    if ( result.error === ERROR_TYPE.TOO_MANY_RESULTS ) {
                        console.log( '[TT GMM Sync] Too many results for:', serverLoc.title,
                            '- result count:', result.resultCount );
                        return {
                            success: false,
                            error: result.error,
                            resultCount: result.resultCount
                        };
                    }
                }

                // Check if we got a valid GMM result
                if ( !result || !result.gmmId ) {
                    console.log( '[TT GMM Sync] Unexpected: no gmmId for:', serverLoc.title );
                    return { success: false, error: ERROR_TYPE.NO_RESULTS };
                }

                // Check for multiple results warning from adapter
                if ( result.warning === 'multiple_results' ) {
                    var multiMsg = 'Multiple matches found (' + result.resultCount +
                        ' results) - verify location is correct';
                    accumulatedWarnings.push({
                        type: WARNING_TYPE.MULTIPLE_RESULTS,
                        message: multiMsg,
                        resultCount: result.resultCount
                    });
                }

                // Validate coordinates if server location has them
                if ( serverLoc.latitude && serverLoc.longitude && result.coordinates ) {
                    var distance = calculateDistanceMeters(
                        serverLoc.latitude,
                        serverLoc.longitude,
                        result.coordinates.latitude,
                        result.coordinates.longitude
                    );

                    console.log( '[TT GMM Sync] Distance check:', {
                        serverCoords: { lat: serverLoc.latitude, lon: serverLoc.longitude },
                        gmmCoords: result.coordinates,
                        distance: distance,
                        threshold: COORDINATE_DISTANCE_THRESHOLD_M
                    });

                    if ( distance > COORDINATE_DISTANCE_THRESHOLD_M ) {
                        var distanceKm = ( distance / 1000 ).toFixed( 1 );
                        console.log( '[TT GMM Sync] Coordinate mismatch for:', serverLoc.title,
                            '- distance:', distanceKm, 'km' );
                        accumulatedWarnings.push({
                            type: WARNING_TYPE.COORDINATE_MISMATCH,
                            message: 'Location is ' + distanceKm + 'km away - verify location is correct',
                            distance: Math.round( distance )
                        });
                    }
                }

                // Success - update server location with gmm_id
                return updateServerLocationGmmId( serverLoc.uuid, result.gmmId )
                    .then( function() {
                        return TTGmmAdapter.closeInfoWindow();
                    })
                    .then( function() {
                        // Clear search results to leave map clean
                        return TTGmmAdapter.clearSearchResults();
                    })
                    .then( function() {
                        return {
                            success: true,
                            gmm: result,
                            warnings: accumulatedWarnings
                        };
                    });
            });
    }

    /**
     * Get GMM style options for a server location based on its category.
     * Falls back to "Other" layer with warnings for missing/unknown categories.
     * @param {Object} serverLoc - Server location with subcategory_slug.
     * @returns {Promise<Object>} Style options { layerTitle, colorRgb, iconCode, warnings }.
     */
    function getStyleOptionsForLocation( serverLoc ) {
        return getLocationCategories()
            .then( function( categories ) {
                var warnings = [];

                // Check for missing subcategory
                if ( !serverLoc.subcategory_slug ) {
                    warnings.push({
                        type: WARNING_TYPE.NO_CATEGORY,
                        message: WARNING_MESSAGES[WARNING_TYPE.NO_CATEGORY]
                    });
                    return {
                        layerTitle: TT.CONFIG.GMM_OTHER_LAYER_NAME,
                        colorRgb: TT.CONFIG.GMM_OTHER_LAYER_COLOR,
                        iconCode: TT.CONFIG.GMM_OTHER_LAYER_ICON,
                        warnings: warnings
                    };
                }

                // Find the category and subcategory
                for ( var i = 0; i < categories.length; i++ ) {
                    var category = categories[i];
                    var subcategories = category.subcategories || [];
                    var subcategory = subcategories.find( function( s ) {
                        return s.slug === serverLoc.subcategory_slug;
                    });
                    if ( subcategory ) {
                        return {
                            layerTitle: category.name,
                            colorRgb: subcategory.color_code || category.color_code,
                            iconCode: subcategory.icon_code || category.icon_code,
                            warnings: warnings
                        };
                    }
                }

                // Unknown subcategory - use Other layer
                warnings.push({
                    type: WARNING_TYPE.UNKNOWN_CATEGORY,
                    message: "Unknown category '" + serverLoc.subcategory_slug + "' - added to 'Other' layer"
                });
                return {
                    layerTitle: TT.CONFIG.GMM_OTHER_LAYER_NAME,
                    colorRgb: TT.CONFIG.GMM_OTHER_LAYER_COLOR,
                    iconCode: TT.CONFIG.GMM_OTHER_LAYER_ICON,
                    warnings: warnings
                };
            });
    }

    /**
     * Get location categories from client config via background.
     * @returns {Promise<Array>} Array of category objects.
     */
    function getLocationCategories() {
        return new Promise( function( resolve, reject ) {
            chrome.runtime.sendMessage({
                type: TT.MESSAGE.TYPE_GET_LOCATION_CATEGORIES
            }, function( response ) {
                if ( chrome.runtime.lastError ) {
                    reject( new Error( chrome.runtime.lastError.message ) );
                    return;
                }
                if ( response && response.success ) {
                    resolve( response.data.location_categories || [] );
                } else {
                    reject( new Error( response ? response.error : 'No response' ) );
                }
            });
        });
    }

    /**
     * Update a server location's gmm_id.
     * @param {string} locationUuid - Location UUID.
     * @param {string} gmmId - GMM location ID to set.
     * @returns {Promise<void>}
     */
    function updateServerLocationGmmId( locationUuid, gmmId ) {
        return new Promise( function( resolve, reject ) {
            chrome.runtime.sendMessage({
                type: TT.MESSAGE.TYPE_UPDATE_LOCATION,
                data: {
                    uuid: locationUuid,
                    updates: {
                        gmm_id: gmmId
                    }
                }
            }, function( response ) {
                if ( chrome.runtime.lastError ) {
                    reject( new Error( chrome.runtime.lastError.message ) );
                    return;
                }
                if ( response && response.success ) {
                    resolve();
                } else {
                    var errorMsg = ( response && response.data && response.data.error )
                        ? response.data.error
                        : 'Failed to update location';
                    reject( new Error( errorMsg ) );
                }
            });
        });
    }

    /**
     * Sync a GMM location to the server.
     * Opens the location to get full details (coordinates, contact info), then saves to server.
     * @param {string} tripUuid - Trip UUID.
     * @param {Object} gmmLoc - GMM location { fl_id, title, icon_code, layer_title }.
     * @returns {Promise<Object>} Created server location.
     */
    function syncGmmLocationToServer( tripUuid, gmmLoc ) {
        console.log( '[TT GMM Sync] Syncing GMM location to server:', gmmLoc.title );

        // Get categories for subcategory mapping
        return getLocationCategories()
            .then( function( categories ) {
                // Open the location to get coordinates and contact info
                return TTGmmAdapter.openLocationById( gmmLoc.fl_id )
                    .then( function( locationInfo ) {
                        // Build location data for server
                        var locationData = {
                            gmm_id: gmmLoc.fl_id,
                            title: locationInfo.title || gmmLoc.title
                        };

                        // Add coordinates if available
                        if ( locationInfo.coordinates ) {
                            locationData.latitude = locationInfo.coordinates.latitude;
                            locationData.longitude = locationInfo.coordinates.longitude;
                        }

                        // Extract contact info from the open info dialog
                        var contactInfo = TTGmmAdapter.getContactInfo();
                        if ( contactInfo.length > 0 ) {
                            console.log( '[TT GMM Sync] Extracted contact info:', contactInfo );
                            locationData.contact_info = contactInfo;
                        }

                        // Map subcategory from layer name and icon
                        var mapping = mapToSubcategory( gmmLoc.layer_title, gmmLoc.icon_code, categories );
                        if ( mapping ) {
                            locationData.subcategory_slug = mapping.subcategory_slug;
                        }

                        console.log( '[TT GMM Sync] Saving location to server:', locationData );

                        return saveLocationToServer( tripUuid, locationData )
                            .then( function( serverResult ) {
                                return TTGmmAdapter.closeInfoWindow()
                                    .then( function() {
                                        return serverResult;
                                    });
                            });
                    });
            });
    }

    // GMM icon code to subcategory slug mapping
    // Maps Google My Maps icon codes to Trip Tools subcategory slugs
    var GMM_ICON_TO_SUBCATEGORY = {
        // Activities - Hike/Trail
        '1595': 'hike',         // Hiking (Group)
        '1596': 'hike',         // Hiking
        '1597': 'hike',         // Trailhead
        '1837': 'hike',         // Nordic Walking

        // Activities - Museum/Library
        '1636': 'museum',       // Museum
        '1834': 'museum',       // Museum (Japan)
        '1664': 'museum',       // Library
        '1726': 'museum',       // University

        // Activities - Viewpoint/Photo Op
        '1523': 'view_photoop', // Viewpoint
        '1535': 'view_photoop', // Photo
        '1728': 'view_photoop', // Vista (Partial)
        '1729': 'view_photoop', // Vista

        // Activities - Church/Religious
        '1666': 'church_religious', // Bahá'í
        '1668': 'church_religious', // Buddhist (Wheel)
        '1669': 'church_religious', // Buddhist (Zen)
        '1670': 'church_religious', // Christian
        '1671': 'church_religious', // Place of Worship
        '1672': 'church_religious', // Hindu
        '1673': 'church_religious', // Islamic
        '1674': 'church_religious', // Jain
        '1675': 'church_religious', // Jewish
        '1676': 'church_religious', // Prayer
        '1677': 'church_religious', // Shinto
        '1678': 'church_religious', // Sikh
        '1706': 'church_religious', // Temple
        '1830': 'church_religious', // Mormon

        // Activities - Cemetery
        '1542': 'cemetery',     // Cemetery
        '1610': 'cemetery',     // Cemetery (Japan)

        // Activities - Historic/Ruins
        '1598': 'historic_ruins', // Historic Building
        '1600': 'historic_ruins', // Plaque
        '1804': 'historic_ruins', // Historic Building (China)

        // Activities - Park/Garden
        '1582': 'park_garden',  // Garden
        '1720': 'park_garden',  // Park
        '1652': 'park_garden',  // Playground

        // Activities - Waterfall
        '1892': 'waterfall',    // Waterfall

        // Activities - Beach
        '1521': 'beach',        // Beach
        '1882': 'beach',        // Tidepool

        // Activities - Cinema/Play
        '1635': 'cinema_play',  // Movies
        '1637': 'cinema_play',  // Music
        '1649': 'cinema_play',  // Music Hall
        '1698': 'cinema_play',  // Stadium
        '1708': 'cinema_play',  // Amphitheatre
        '1709': 'cinema_play',  // Theater

        // Activities - Theme Park/Zoo
        '1568': 'theme_park_zoo', // Amusement Park

        // Activities - Monument
        '1528': 'monument',     // Bridge
        '1599': 'monument',     // Monument
        '1618': 'monument',     // Lighthouse
        '1715': 'monument',     // Tower

        // Activities - Fountain/Statue
        '1580': 'fountain',     // Fountain

        // Activities - Artwork
        '1509': 'artwork',      // Art

        // Activities - Astronomy
        '1878': 'astronomy',    // Stargazing

        // Activities - Cave
        '1767': 'cave',         // Cave
        '1768': 'cave',         // Caving

        // Activities - Geothermal/Hot Springs
        '1730': 'geothermal',   // Volcano
        '1811': 'geothermal',   // Hot Spring

        // Dining/Shopping - Breakfast/Lunch
        '1534': 'coffee_breakfast', // Cafe
        '1705': 'coffee_breakfast', // Teahouse

        // Dining/Shopping - Dinner/Restaurant
        '1530': 'lunch_dinner', // Burger
        '1545': 'lunch_dinner', // Chicken
        '1567': 'lunch_dinner', // Fast Food
        '1577': 'lunch_dinner', // Restaurant
        '1640': 'lunch_dinner', // Noodles
        '1651': 'lunch_dinner', // Pizza
        '1810': 'lunch_dinner', // Hot Dog
        '1835': 'lunch_dinner', // Sushi

        // Dining/Shopping - Cafe/Bakery
        // Note: 1534 (Cafe) already mapped to coffee_breakfast

        // Dining/Shopping - Desserts/Snacks
        '1607': 'deserts',      // Ice Cream

        // Dining/Shopping - Drinks/Bar
        '1517': 'drinks_bar',   // Cocktails
        '1518': 'drinks_bar',   // Pub
        '1879': 'drinks_bar',   // Beer

        // Dining/Shopping - Food Hall/Market
        '1611': 'food_area',    // Point of Interest (used for food halls)

        // Dining/Shopping - Food Store
        '1578': 'food_store',   // Groceries
        '1587': 'food_store',   // Health Food
        '1631': 'food_store',   // Convenience Store

        // Dining/Shopping - Store/Shop
        '1549': 'store_shop',   // Clothing
        '1584': 'store_shop',   // Gifts
        '1613': 'store_shop',   // Jewelry
        '1683': 'store_shop',   // Shoes
        '1684': 'store_shop',   // Shopping
        '1685': 'store_shop',   // Shopping Cart
        '1686': 'store_shop',   // Shop

        // Places - City
        '1546': 'city',         // City

        // Places - Town
        '1547': 'towns_town',   // Downtown

        // Places - Neighborhood/Area
        '1583': 'neighborhood', // Gated Community
        '1604': 'neighborhood', // Neighborhood

        // Lodging - Hotel
        '1602': 'hotel',        // Hotel

        // Lodging - Hostel/Dormitory
        '1559': 'hostel',       // Dormitory

        // Lodging - Camping/Campground
        '1763': 'camping',      // Camper
        '1764': 'camping',      // Campfire
        '1765': 'camping',      // Camping
        '1859': 'camping',      // RV

        // Transportation - Plane
        '1504': 'plane',        // Airport
        '1750': 'plane',        // Airstrip

        // Transportation - Car/Auto
        '1538': 'car_auto',     // Car
        '1581': 'car_auto',     // Gas Station
        '1704': 'car_auto',     // Taxi
        '1741': 'car_auto',     // Rental Car

        // Transportation - Boat
        '1525': 'boat',         // Boat Launch
        '1622': 'boat',         // Yacht
        '1623': 'boat',         // Marina
        '1681': 'boat',         // Sailing

        // Transportation - Train
        '1662': 'train',        // Railway
        '1716': 'train',        // Train
        '1717': 'train',        // Train (Steam)

        // Transportation - Metro/Tram
        '1626': 'metro_tram',   // Metro
        '1629': 'metro_tram',   // Monorail
        '1718': 'metro_tram',   // Tram
        '1719': 'metro_tram',   // Subway

        // Transportation - Cable Car/Funicular
        '1533': 'cable_car_funicular', // Cable Car
        '1586': 'cable_car_funicular', // Gondola
        '1689': 'cable_car_funicular', // Ski Lift

        // Transportation - Walking Tour
        '1731': 'walking',      // Walking

        // Transportation - Ferry
        '1537': 'ferry',        // Vehicle Ferry
        '1569': 'ferry',        // Ferry

        // Transportation - Bus
        '1532': 'bus',          // Bus

        // Transportation - Bicycle
        '1522': 'bicycle',      // Cycling

        // Transportation - Helicopter
        '1593': 'helicopter',   // Helicopter

        // Transportation - Parking
        '1562': 'parking',      // Parking Space
        '1644': 'parking'       // Parking
    };

    /**
     * Map GMM layer name and icon code to subcategory slug.
     * Uses GMM icon mapping as primary lookup, falls back to layer name.
     * @param {string} layerTitle - GMM layer title.
     * @param {string} iconCode - GMM icon code.
     * @param {Array} categories - Categories from client config.
     * @returns {Object|null} { subcategory_slug } or null.
     */
    function mapToSubcategory( layerTitle, iconCode, categories ) {
        // Priority 1: Look up icon code in GMM mapping
        if ( iconCode && GMM_ICON_TO_SUBCATEGORY[iconCode] ) {
            var slug = GMM_ICON_TO_SUBCATEGORY[iconCode];
            console.log( '[TT GMM Sync] Matched icon code', iconCode, 'to subcategory:', slug );
            return { subcategory_slug: slug };
        }

        // Priority 2: Match layer name to category, use first subcategory
        if ( layerTitle && categories && categories.length > 0 ) {
            var normalizedLayer = layerTitle.toLowerCase().trim();
            for ( var i = 0; i < categories.length; i++ ) {
                var cat = categories[i];
                if ( cat.name.toLowerCase().trim() === normalizedLayer ) {
                    var subs = cat.subcategories || [];
                    if ( subs.length > 0 ) {
                        console.log( '[TT GMM Sync] Matched layer name', layerTitle,
                                     'to category, using first subcategory:', subs[0].slug );
                        return { subcategory_slug: subs[0].slug };
                    }
                }
            }
        }

        console.log( '[TT GMM Sync] No subcategory match for layer:', layerTitle, 'icon:', iconCode );
        return null;
    }

    /**
     * Save location to server via background script.
     * @param {string} tripUuid - Trip UUID.
     * @param {Object} locationData - Location data.
     * @returns {Promise<Object>} Server response.
     */
    function saveLocationToServer( tripUuid, locationData ) {
        return new Promise( function( resolve, reject ) {
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
                        : 'Failed to save location';
                    reject( new Error( errorMsg ) );
                }
            });
        });
    }

    /**
     * Delete location from server via background script.
     * @param {string} locationUuid - Location UUID.
     * @returns {Promise<void>}
     */
    function deleteServerLocation( locationUuid ) {
        return new Promise( function( resolve, reject ) {
            chrome.runtime.sendMessage({
                type: TT.MESSAGE.TYPE_DELETE_LOCATION,
                data: { uuid: locationUuid }
            }, function( response ) {
                if ( chrome.runtime.lastError ) {
                    reject( new Error( chrome.runtime.lastError.message ) );
                    return;
                }
                if ( response && response.success ) {
                    resolve();
                } else {
                    var errorMsg = ( response && response.data && response.data.error )
                        ? response.data.error
                        : 'Failed to delete location';
                    reject( new Error( errorMsg ) );
                }
            });
        });
    }

    /**
     * Fetch all locations for a trip from the server.
     * @param {string} tripUuid - The trip UUID.
     * @returns {Promise<Array>} Array of location objects.
     */
    function fetchServerLocations( tripUuid ) {
        return new Promise( function( resolve, reject ) {
            chrome.runtime.sendMessage(
                {
                    type: TT.MESSAGE.TYPE_GET_TRIP_LOCATIONS,
                    data: { tripUuid: tripUuid }
                },
                function( response ) {
                    if ( chrome.runtime.lastError ) {
                        reject( new Error( chrome.runtime.lastError.message ) );
                        return;
                    }
                    if ( response && response.success ) {
                        resolve( response.data.locations || [] );
                    } else {
                        reject( new Error( response && response.data && response.data.error
                            ? response.data.error : 'Failed to fetch locations' ) );
                    }
                }
            );
        });
    }

    /**
     * Get locations from GMM DOM.
     * Reads all locations from all layers using TTGmmAdapter.
     * @returns {Promise<Array>} Array of GMM location objects with fl_id.
     */
    function getGmmLocations() {
        var locations = [];

        try {
            var layers = TTGmmAdapter.getLayers();
            console.log( '[TT GMM Sync] Found ' + layers.length + ' layers' );

            layers.forEach( function( layer ) {
                var layerLocations = TTGmmAdapter.getLocationsInLayer( layer );
                console.log( '[TT GMM Sync] Layer "' + layer.title + '": ' +
                    layerLocations.length + ' locations' );

                layerLocations.forEach( function( loc ) {
                    locations.push({
                        fl_id: loc.id,
                        title: loc.title,
                        icon_code: loc.iconCode,
                        layer_id: layer.id,
                        layer_title: layer.title
                    });
                });
            });

            console.log( '[TT GMM Sync] Total GMM locations: ' + locations.length );
        } catch ( error ) {
            console.error( '[TT GMM Sync] Error reading GMM locations:', error );
        }

        return Promise.resolve( locations );
    }

    /**
     * Normalize a title for comparison (trim whitespace, lowercase).
     * @param {string} title - The title to normalize.
     * @returns {string} Normalized title.
     */
    function normalizeTitle( title ) {
        return ( title || '' ).trim().toLowerCase();
    }

    /**
     * Compare server and GMM locations to find differences.
     * Uses gmm_id (server) and fl_id (GMM) for matching.
     * Also detects title matches among unlinked locations.
     * @param {Array} serverLocations - Locations from server.
     * @param {Array} gmmLocations - Locations from GMM DOM.
     * @returns {Object} Diff result with serverOnly, gmmOnly, inBoth, suggestedMatches arrays.
     */
    function compareLocations( serverLocations, gmmLocations ) {
        // Build lookup of GMM fl_ids
        var gmmIdSet = {};
        gmmLocations.forEach( function( loc ) {
            if ( loc.fl_id ) {
                gmmIdSet[loc.fl_id] = loc;
            }
        });

        // Build lookup of server gmm_ids
        var serverGmmIdSet = {};
        serverLocations.forEach( function( loc ) {
            if ( loc.gmm_id ) {
                serverGmmIdSet[loc.gmm_id] = loc;
            }
        });

        var serverOnlyInitial = [];
        var inBoth = [];

        // Check each server location
        serverLocations.forEach( function( serverLoc ) {
            if ( serverLoc.gmm_id && gmmIdSet[serverLoc.gmm_id] ) {
                // Found in both
                inBoth.push( {
                    server: serverLoc,
                    gmm: gmmIdSet[serverLoc.gmm_id]
                });
            } else {
                // Server only (no gmm_id or not found in GMM)
                serverOnlyInitial.push( serverLoc );
            }
        });

        // Check for GMM-only locations
        var gmmOnlyInitial = [];
        gmmLocations.forEach( function( gmmLoc ) {
            if ( gmmLoc.fl_id && !serverGmmIdSet[gmmLoc.fl_id] ) {
                gmmOnlyInitial.push( gmmLoc );
            }
        });

        // Find title matches among unlinked locations
        var suggestedMatches = [];
        var serverOnly = [];
        var gmmOnly = [];

        // Build normalized title lookup for GMM-only locations
        var gmmByNormalizedTitle = {};
        gmmOnlyInitial.forEach( function( gmmLoc ) {
            var normalized = normalizeTitle( gmmLoc.title );
            if ( !gmmByNormalizedTitle[normalized] ) {
                gmmByNormalizedTitle[normalized] = [];
            }
            gmmByNormalizedTitle[normalized].push( gmmLoc );
        });

        // Check each server-only location for title match
        serverOnlyInitial.forEach( function( serverLoc ) {
            var normalized = normalizeTitle( serverLoc.title );
            var gmmMatches = gmmByNormalizedTitle[normalized];

            if ( gmmMatches && gmmMatches.length > 0 ) {
                // Take first match, remove from available pool
                var gmmMatch = gmmMatches.shift();
                suggestedMatches.push( {
                    server: serverLoc,
                    gmm: gmmMatch
                });
            } else {
                serverOnly.push( serverLoc );
            }
        });

        // Remaining GMM locations (not matched by title)
        Object.keys( gmmByNormalizedTitle ).forEach( function( key ) {
            gmmByNormalizedTitle[key].forEach( function( gmmLoc ) {
                gmmOnly.push( gmmLoc );
            });
        });

        return {
            serverOnly: serverOnly,
            gmmOnly: gmmOnly,
            inBoth: inBoth,
            suggestedMatches: suggestedMatches
        };
    }

    /**
     * Show the sync compare dialog with diff results.
     * Shows per-location KEEP/DISCARD toggles for differences.
     * Shows Link/Don't Link toggles for suggested title matches.
     * @param {Object} data - Sync request data (tripUuid, tripTitle, etc.).
     * @param {Object} diff - Diff results from compareLocations.
     * @returns {Promise<Object>} Result of sync operation.
     */
    function showSyncCompareDialog( data, diff ) {
        return new Promise( function( resolve ) {
            // Remove any existing dialog
            var existingDialog = document.querySelector( '.' + TT_SYNC_DIALOG_CLASS );
            if ( existingDialog ) {
                existingDialog.remove();
            }

            // Track sync decisions - all default to KEEP/LINK
            var syncDecisions = {};

            // Create dialog container
            var dialog = TTDom.createElement( 'div', {
                className: TT_SYNC_DIALOG_CLASS
            });

            // Header
            var header = TTDom.createElement( 'div', {
                className: 'tt-sync-header',
                text: 'Sync Map'
            });
            dialog.appendChild( header );

            // Trip info
            var tripInfo = TTDom.createElement( 'div', {
                className: 'tt-sync-trip-info',
                text: 'Trip: ' + ( data.tripTitle || 'Unknown' )
            });
            dialog.appendChild( tripInfo );

            var hasSuggestedMatches = diff.suggestedMatches && diff.suggestedMatches.length > 0;
            var hasDifferences = diff.serverOnly.length > 0 || diff.gmmOnly.length > 0;
            var hasAnyAction = hasSuggestedMatches || hasDifferences;

            // Suggested Matches section (shown first if present)
            if ( hasSuggestedMatches ) {
                var matchSection = TTDom.createElement( 'div', {
                    className: 'tt-sync-section tt-sync-section-suggested'
                });

                var matchHeader = TTDom.createElement( 'div', {
                    className: 'tt-sync-section-header',
                    text: 'Suggested Matches (' + diff.suggestedMatches.length + ')'
                });
                matchSection.appendChild( matchHeader );

                var matchList = TTDom.createElement( 'div', {
                    className: 'tt-sync-location-list'
                });

                diff.suggestedMatches.forEach( function( match ) {
                    var itemId = 'match_' + match.server.uuid;
                    syncDecisions[itemId] = {
                        action: 'link',
                        source: 'match',
                        server: match.server,
                        gmm: match.gmm
                    };
                    var item = createSuggestedMatchItem(
                        match.server.title,
                        itemId,
                        syncDecisions
                    );
                    matchList.appendChild( item );
                });

                matchSection.appendChild( matchList );
                dialog.appendChild( matchSection );
            }

            // Differences section
            if ( hasDifferences ) {
                var diffSection = TTDom.createElement( 'div', {
                    className: 'tt-sync-section'
                });

                var diffHeader = TTDom.createElement( 'div', {
                    className: 'tt-sync-section-header',
                    text: 'Differences'
                });
                diffSection.appendChild( diffHeader );

                // Location list
                var locationList = TTDom.createElement( 'div', {
                    className: 'tt-sync-location-list'
                });

                // Add server-only locations
                diff.serverOnly.forEach( function( loc ) {
                    var itemId = 'server_' + loc.uuid;
                    syncDecisions[itemId] = { action: 'keep', source: 'server', location: loc };
                    var item = createLocationItem( loc.title, 'Server only', 'server', itemId, syncDecisions );
                    locationList.appendChild( item );
                });

                // Add GMM-only locations
                diff.gmmOnly.forEach( function( loc ) {
                    var itemId = 'gmm_' + loc.fl_id;
                    syncDecisions[itemId] = { action: 'keep', source: 'gmm', location: loc };
                    var item = createLocationItem( loc.title, 'GMM only', 'gmm', itemId, syncDecisions );
                    locationList.appendChild( item );
                });

                diffSection.appendChild( locationList );
                dialog.appendChild( diffSection );
            }

            // Summary section (always shown)
            var summarySection = TTDom.createElement( 'div', {
                className: 'tt-sync-section'
            });

            if ( hasAnyAction ) {
                var summaryText = TTDom.createElement( 'div', {
                    className: 'tt-sync-summary'
                });
                var inSyncSpan = TTDom.createElement( 'span', {
                    className: 'tt-sync-summary-count',
                    text: diff.inBoth.length
                });
                summaryText.appendChild( inSyncSpan );
                summaryText.appendChild( document.createTextNode(
                    ' location' + ( diff.inBoth.length !== 1 ? 's' : '' ) + ' already in sync'
                ));
                summarySection.appendChild( summaryText );
            } else {
                var inSyncMessage = TTDom.createElement( 'div', {
                    className: 'tt-sync-in-sync-message',
                    text: 'All ' + diff.inBoth.length + ' locations are in sync!'
                });
                summarySection.appendChild( inSyncMessage );
            }

            dialog.appendChild( summarySection );

            // Button container
            var buttonContainer = TTDom.createElement( 'div', {
                className: 'tt-sync-buttons'
            });

            var closeBtn = TTDom.createElement( 'button', {
                className: 'tt-gmm-btn tt-cancel-btn',
                text: hasAnyAction ? 'Cancel' : 'Close'
            });
            closeBtn.addEventListener( 'click', function() {
                dialog.remove();
                resolve( { cancelled: true } );
            });
            buttonContainer.appendChild( closeBtn );

            if ( hasAnyAction ) {
                var syncBtn = TTDom.createElement( 'button', {
                    className: 'tt-gmm-btn tt-category-btn',
                    text: 'Apply Sync'
                });
                syncBtn.addEventListener( 'click', function() {
                    dialog.remove();
                    resolve( { cancelled: false, decisions: syncDecisions } );
                });
                buttonContainer.appendChild( syncBtn );
            }

            dialog.appendChild( buttonContainer );

            document.body.appendChild( dialog );
            console.log( '[TT Sync Compare] Dialog displayed' );
        });
    }

    /**
     * Create a suggested match item row with Link/Don't Link toggle.
     * @param {string} title - Location title (same in both places).
     * @param {string} itemId - Unique identifier for this item.
     * @param {Object} syncDecisions - Reference to decisions object.
     * @returns {Element} The location item element.
     */
    function createSuggestedMatchItem( title, itemId, syncDecisions ) {
        var item = TTDom.createElement( 'div', {
            className: 'tt-sync-location-item tt-sync-suggested-match'
        });

        // Location info
        var info = TTDom.createElement( 'div', {
            className: 'tt-sync-location-info'
        });

        var titleEl = TTDom.createElement( 'div', {
            className: 'tt-sync-location-title',
            text: title
        });
        info.appendChild( titleEl );

        var sourceEl = TTDom.createElement( 'div', {
            className: 'tt-sync-location-source tt-sync-location-source-match',
            text: 'Same name found in both places'
        });
        info.appendChild( sourceEl );

        item.appendChild( info );

        // Toggle buttons
        var toggle = TTDom.createElement( 'div', {
            className: 'tt-sync-toggle'
        });

        var linkBtn = TTDom.createElement( 'button', {
            className: 'tt-sync-toggle-btn tt-toggle-link',
            text: 'Link'
        });

        var dontLinkBtn = TTDom.createElement( 'button', {
            className: 'tt-sync-toggle-btn',
            text: "Don't Link"
        });

        linkBtn.addEventListener( 'click', function() {
            syncDecisions[itemId].action = 'link';
            linkBtn.classList.add( 'tt-toggle-link' );
            dontLinkBtn.classList.remove( 'tt-toggle-dont-link' );
        });

        dontLinkBtn.addEventListener( 'click', function() {
            syncDecisions[itemId].action = 'dont_link';
            dontLinkBtn.classList.add( 'tt-toggle-dont-link' );
            linkBtn.classList.remove( 'tt-toggle-link' );
        });

        toggle.appendChild( linkBtn );
        toggle.appendChild( dontLinkBtn );
        item.appendChild( toggle );

        return item;
    }

    /**
     * Show sync execute results dialog after sync completes.
     * Three-tier display: Synced (green), Needs Review (yellow), Failed (red).
     * @param {Object} results - Sync results object.
     * @returns {Promise<Object>} The results (passed through).
     */
    function showSyncExecuteResultsDialog( results ) {
        return new Promise( function( resolve ) {
            // Remove any existing dialog
            var existingDialog = document.querySelector( '.' + TT_SYNC_DIALOG_CLASS );
            if ( existingDialog ) {
                existingDialog.remove();
            }

            // Create dialog container
            var dialog = TTDom.createElement( 'div', {
                className: TT_SYNC_DIALOG_CLASS
            });

            // Header
            var headerText = results.stopped ? 'Sync Stopped' : 'Sync Complete';
            var header = TTDom.createElement( 'div', {
                className: 'tt-sync-header',
                text: headerText
            });
            dialog.appendChild( header );

            // If stopped, show a notice
            if ( results.stopped ) {
                var stoppedNotice = TTDom.createElement( 'div', {
                    className: 'tt-sync-stopped-notice',
                    text: 'Sync was stopped before completion. Partial results shown below.'
                });
                dialog.appendChild( stoppedNotice );
            }

            // Count clean successes (warnings shown separately)
            var linkedByTitleCount = results.linkedByTitle ? results.linkedByTitle.length : 0;
            var cleanSuccessCount = results.addedToServer.length + results.addedToGmm.length +
                              linkedByTitleCount +
                              results.deletedFromServer.length + results.deletedFromGmm.length;
            var hasCleanSuccesses = cleanSuccessCount > 0;
            var hasWarnings = results.warnings && results.warnings.length > 0;
            var hasFailures = results.failures && results.failures.length > 0;
            var hasErrors = results.errors && results.errors.length > 0;

            // ========== SYNCED SECTION (green) ==========
            if ( hasCleanSuccesses ) {
                var syncedSection = TTDom.createElement( 'div', {
                    className: 'tt-sync-section tt-sync-section-success'
                });

                var syncedHeader = TTDom.createElement( 'div', {
                    className: 'tt-sync-section-header tt-sync-header-success',
                    text: '\u2713 SYNCED (' + cleanSuccessCount + ')'
                });
                syncedSection.appendChild( syncedHeader );

                var syncedList = TTDom.createElement( 'div', {
                    className: 'tt-sync-location-list'
                });

                // GMM -> Server (ADDED)
                results.addedToServer.forEach( function( item ) {
                    var row = createSyncedRow( item.gmm.title, 'ADDED', null );
                    syncedList.appendChild( row );
                });

                // Server -> GMM without warnings (MATCHED)
                results.addedToGmm.forEach( function( item ) {
                    var googleTitle = item.gmm ? item.gmm.googleTitle : null;
                    var gmmId = item.gmm ? item.gmm.gmmId : null;
                    var onUndo = gmmId ? function( row ) {
                        handleUndoClick( dialog, row, gmmId, item.server.title );
                    } : null;
                    var row = createSyncedRow( item.server.title, 'MATCHED', onUndo, googleTitle );
                    syncedList.appendChild( row );
                });

                // Linked by title (LINKED)
                if ( results.linkedByTitle ) {
                    results.linkedByTitle.forEach( function( item ) {
                        var row = createSyncedRow( item.server.title, 'LINKED', null );
                        syncedList.appendChild( row );
                    });
                }

                // Deletions
                results.deletedFromServer.forEach( function( loc ) {
                    var row = createSyncedRow( loc.title, 'REMOVED', null );
                    syncedList.appendChild( row );
                });
                results.deletedFromGmm.forEach( function( loc ) {
                    var row = createSyncedRow( loc.title, 'REMOVED', null );
                    syncedList.appendChild( row );
                });

                syncedSection.appendChild( syncedList );
                dialog.appendChild( syncedSection );
            }

            // ========== WARNINGS SECTION (yellow) ==========
            if ( hasWarnings ) {
                var warningsSection = TTDom.createElement( 'div', {
                    className: 'tt-sync-section tt-sync-section-warning'
                });

                var warningsHeader = TTDom.createElement( 'div', {
                    className: 'tt-sync-section-header tt-sync-header-warning',
                    text: '\u26A0 NEEDS REVIEW (' + results.warnings.length + ')'
                });
                warningsSection.appendChild( warningsHeader );

                var warningsList = TTDom.createElement( 'div', {
                    className: 'tt-sync-location-list'
                });

                results.warnings.forEach( function( item ) {
                    var gmmId = item.gmm ? item.gmm.gmmId : null;
                    var onUndo = gmmId ? function( row ) {
                        handleUndoClick( dialog, row, gmmId, item.server.title );
                    } : null;
                    var row = createWarningRow( item.server.title, item.warnings, item.gmm, onUndo );
                    warningsList.appendChild( row );
                });

                warningsSection.appendChild( warningsList );
                dialog.appendChild( warningsSection );
            }

            // ========== FAILURES SECTION (red) ==========
            if ( hasFailures ) {
                var failuresSection = TTDom.createElement( 'div', {
                    className: 'tt-sync-section tt-sync-section-error'
                });

                var failuresHeader = TTDom.createElement( 'div', {
                    className: 'tt-sync-section-header tt-sync-header-error',
                    text: '\u2717 FAILED (' + results.failures.length + ')'
                });
                failuresSection.appendChild( failuresHeader );

                var failuresList = TTDom.createElement( 'div', {
                    className: 'tt-sync-location-list'
                });

                results.failures.forEach( function( item ) {
                    var row = createFailureRow( item );
                    failuresList.appendChild( row );
                });

                failuresSection.appendChild( failuresList );
                dialog.appendChild( failuresSection );
            }

            // ========== ERRORS SECTION (unexpected errors) ==========
            if ( hasErrors ) {
                var errorsSection = TTDom.createElement( 'div', {
                    className: 'tt-sync-section tt-sync-section-error'
                });

                var errorsHeader = TTDom.createElement( 'div', {
                    className: 'tt-sync-section-header tt-sync-header-error',
                    text: '\u2717 ERRORS (' + results.errors.length + ')'
                });
                errorsSection.appendChild( errorsHeader );

                results.errors.forEach( function( err ) {
                    var errorRow = TTDom.createElement( 'div', {
                        className: 'tt-sync-result-row'
                    });
                    var label = TTDom.createElement( 'span', {
                        className: 'tt-sync-result-title',
                        text: err.location ? err.location.title : 'Unknown'
                    });
                    var value = TTDom.createElement( 'span', {
                        className: 'tt-sync-result-error-text',
                        text: err.error
                    });
                    errorRow.appendChild( label );
                    errorRow.appendChild( value );
                    errorsSection.appendChild( errorRow );
                });

                dialog.appendChild( errorsSection );
            }

            // No activity message
            if ( !hasCleanSuccesses && !hasWarnings && !hasFailures && !hasErrors ) {
                var noActivityMsg = TTDom.createElement( 'div', {
                    className: 'tt-sync-in-sync-message',
                    text: 'No changes were made.'
                });
                dialog.appendChild( noActivityMsg );
            }

            // Button container
            var buttonContainer = TTDom.createElement( 'div', {
                className: 'tt-sync-buttons'
            });

            var closeBtn = TTDom.createElement( 'button', {
                className: 'tt-gmm-btn tt-cancel-btn',
                text: 'Close'
            });
            closeBtn.addEventListener( 'click', function() {
                dialog.remove();
                resolve( results );
            });
            buttonContainer.appendChild( closeBtn );

            dialog.appendChild( buttonContainer );

            document.body.appendChild( dialog );
            console.log( '[TT Sync Execute] Results dialog displayed' );
        });
    }

    /**
     * Create a synced row for the results dialog (success tier).
     * @param {string} title - Location title (server title).
     * @param {string} status - Status label (ADDED, MATCHED, REMOVED).
     * @param {Function} [onUndo] - Callback when Undo is clicked (receives row element).
     * @param {string} [googleTitle] - The Google title that was matched to.
     * @returns {Element} The row element.
     */
    function createSyncedRow( title, status, onUndo, googleTitle ) {
        // If we have a googleTitle, use result-item container for multi-line display
        if ( googleTitle ) {
            var item = TTDom.createElement( 'div', {
                className: 'tt-sync-result-item'
            });

            var titleRow = TTDom.createElement( 'div', {
                className: 'tt-sync-result-row'
            });

            var titleEl = TTDom.createElement( 'span', {
                className: 'tt-sync-result-title',
                text: title
            });
            titleRow.appendChild( titleEl );

            var actionsEl = TTDom.createElement( 'div', {
                className: 'tt-sync-result-actions'
            });

            var statusEl = TTDom.createElement( 'span', {
                className: 'tt-sync-status tt-sync-status-' + status.toLowerCase(),
                text: status
            });
            actionsEl.appendChild( statusEl );

            if ( onUndo ) {
                var undoBtn = TTDom.createElement( 'button', {
                    className: 'tt-sync-action-btn',
                    text: 'Undo'
                });
                undoBtn.addEventListener( 'click', function() {
                    onUndo( item );
                });
                actionsEl.appendChild( undoBtn );
            }

            titleRow.appendChild( actionsEl );
            item.appendChild( titleRow );

            // Add "Matched to" line
            var matchedEl = TTDom.createElement( 'div', {
                className: 'tt-sync-item-message tt-sync-item-matched',
                text: "Matched to '" + googleTitle + "'"
            });
            item.appendChild( matchedEl );

            return item;
        }

        // Simple single-line row for non-matched items
        var row = TTDom.createElement( 'div', {
            className: 'tt-sync-result-row'
        });

        var titleEl = TTDom.createElement( 'span', {
            className: 'tt-sync-result-title',
            text: title
        });
        row.appendChild( titleEl );

        var actionsEl = TTDom.createElement( 'div', {
            className: 'tt-sync-result-actions'
        });

        var statusEl = TTDom.createElement( 'span', {
            className: 'tt-sync-status tt-sync-status-' + status.toLowerCase(),
            text: status
        });
        actionsEl.appendChild( statusEl );

        if ( onUndo ) {
            var undoBtn = TTDom.createElement( 'button', {
                className: 'tt-sync-action-btn',
                text: 'Undo'
            });
            undoBtn.addEventListener( 'click', function() {
                onUndo( row );
            });
            actionsEl.appendChild( undoBtn );
        }

        row.appendChild( actionsEl );
        return row;
    }

    /**
     * Create a warning row for the results dialog (warning tier).
     * @param {string} title - Location title (server title).
     * @param {Array} warnings - Array of warning objects.
     * @param {Object} gmm - GMM location info (for potential undo and googleTitle).
     * @param {Function} [onUndo] - Callback when Undo is clicked (receives row element).
     * @returns {Element} The row element.
     */
    function createWarningRow( title, warnings, gmm, onUndo ) {
        var item = TTDom.createElement( 'div', {
            className: 'tt-sync-result-item'
        });

        // Title row with Undo button
        var titleRow = TTDom.createElement( 'div', {
            className: 'tt-sync-result-row'
        });

        var titleEl = TTDom.createElement( 'span', {
            className: 'tt-sync-result-title',
            text: title
        });
        titleRow.appendChild( titleEl );

        var actionsEl = TTDom.createElement( 'div', {
            className: 'tt-sync-result-actions'
        });

        if ( onUndo ) {
            var undoBtn = TTDom.createElement( 'button', {
                className: 'tt-sync-action-btn',
                text: 'Undo'
            });
            undoBtn.addEventListener( 'click', function() {
                onUndo( item );
            });
            actionsEl.appendChild( undoBtn );
        }

        titleRow.appendChild( actionsEl );
        item.appendChild( titleRow );

        // "Matched to" line (always show for warnings since they are matched)
        if ( gmm && gmm.googleTitle ) {
            var matchedEl = TTDom.createElement( 'div', {
                className: 'tt-sync-item-message tt-sync-item-matched',
                text: "Matched to '" + gmm.googleTitle + "'"
            });
            item.appendChild( matchedEl );
        }

        // Warning messages
        warnings.forEach( function( warning ) {
            var msgEl = TTDom.createElement( 'div', {
                className: 'tt-sync-item-message tt-sync-item-message-warning',
                text: warning.message
            });
            item.appendChild( msgEl );
        });

        return item;
    }

    /**
     * Create a failure row for the results dialog (failure tier).
     * @param {string} title - Location title.
     * @param {Object} item - The failure item containing server location, error, and resultCount.
     * @returns {Element} The row element.
     */
    function createFailureRow( item ) {
        var title = item.server.title;
        var error = item.error;
        var resultCount = item.resultCount;

        var rowEl = TTDom.createElement( 'div', {
            className: 'tt-sync-result-item'
        });

        // Title row with Fix button
        var titleRow = TTDom.createElement( 'div', {
            className: 'tt-sync-result-row'
        });

        var titleEl = TTDom.createElement( 'span', {
            className: 'tt-sync-result-title',
            text: title
        });
        titleRow.appendChild( titleEl );

        var actionsEl = TTDom.createElement( 'div', {
            className: 'tt-sync-result-actions'
        });

        var fixBtn = TTDom.createElement( 'button', {
            className: 'tt-sync-action-btn',
            text: 'Fix'
        });
        // Enable Fix button with click handler
        fixBtn.addEventListener( 'click', function() {
            enterFixMode( item.server, item.error );
        });
        actionsEl.appendChild( fixBtn );

        titleRow.appendChild( actionsEl );
        rowEl.appendChild( titleRow );

        // Error message
        var errorMsg = ERROR_MESSAGES[error] || error;
        if ( resultCount && resultCount > 1 ) {
            if ( error === ERROR_TYPE.NO_DIALOG ) {
                errorMsg = 'Multiple matches found (' + resultCount + ' results)';
            } else if ( error === ERROR_TYPE.TOO_MANY_RESULTS ) {
                errorMsg = 'Too many matches (' + resultCount + ' results) - search manually';
            }
        } else if ( resultCount === 1 && error === ERROR_TYPE.NO_DIALOG ) {
            errorMsg = 'Result found but could not add - try manually';
        }

        var msgEl = TTDom.createElement( 'div', {
            className: 'tt-sync-item-message tt-sync-item-message-error',
            text: errorMsg
        });
        rowEl.appendChild( msgEl );

        return rowEl;
    }

    /**
     * Create a location item row with KEEP/DISCARD toggle.
     * @param {string} title - Location title.
     * @param {string} sourceText - Source description (e.g., "Server only").
     * @param {string} sourceType - Source type ('server' or 'gmm').
     * @param {string} itemId - Unique identifier for this item.
     * @param {Object} syncDecisions - Reference to decisions object.
     * @returns {Element} The location item element.
     */
    function createLocationItem( title, sourceText, sourceType, itemId, syncDecisions ) {
        var item = TTDom.createElement( 'div', {
            className: 'tt-sync-location-item'
        });

        // Location info
        var info = TTDom.createElement( 'div', {
            className: 'tt-sync-location-info'
        });

        var titleEl = TTDom.createElement( 'div', {
            className: 'tt-sync-location-title',
            text: title
        });
        info.appendChild( titleEl );

        var sourceEl = TTDom.createElement( 'div', {
            className: 'tt-sync-location-source tt-sync-location-source-' + sourceType,
            text: sourceText
        });
        info.appendChild( sourceEl );

        item.appendChild( info );

        // Toggle buttons
        var toggle = TTDom.createElement( 'div', {
            className: 'tt-sync-toggle'
        });

        var keepBtn = TTDom.createElement( 'button', {
            className: 'tt-sync-toggle-btn tt-toggle-keep',
            text: 'Keep'
        });

        var discardBtn = TTDom.createElement( 'button', {
            className: 'tt-sync-toggle-btn',
            text: 'Discard'
        });

        keepBtn.addEventListener( 'click', function() {
            syncDecisions[itemId].action = 'keep';
            keepBtn.classList.add( 'tt-toggle-keep' );
            discardBtn.classList.remove( 'tt-toggle-discard' );
        });

        discardBtn.addEventListener( 'click', function() {
            syncDecisions[itemId].action = 'discard';
            discardBtn.classList.add( 'tt-toggle-discard' );
            keepBtn.classList.remove( 'tt-toggle-keep' );
        });

        toggle.appendChild( keepBtn );
        toggle.appendChild( discardBtn );
        item.appendChild( toggle );

        return item;
    }

    // Initialize on load
    initSync();

    // Expose public API for FIX mode (used by gmm.js)
    window.TTGmmSync = {
        decorateFixModeDialog: decorateFixModeDialog,
        getFixContext: getFixContext
    };

})();
