/*
 * Trip Tools Chrome Extension - API Module
 * Provides fetch wrapper with auth headers and 401 handling.
 * Depends on: constants.js, storage.js, auth.js, sync.js
 */

var TTApi = TTApi || {};

/**
 * Callback for auth failure events.
 * Set this to handle 401 responses at the UI level.
 * @type {Function|null}
 */
TTApi.onAuthFailure = null;

/**
 * Get the configured server URL.
 * @returns {Promise<string>} The server URL.
 */
TTApi.getServerUrl = function() {
    var defaultUrl = TT.CONFIG.IS_DEVELOPMENT
        ? TT.CONFIG.DEFAULT_SERVER_URL_DEV
        : TT.CONFIG.DEFAULT_SERVER_URL_PROD;

    return TTStorage.get( TT.STORAGE.KEY_SERVER_URL, defaultUrl );
};

/**
 * Get sync headers from storage.
 * @private
 * @returns {Promise<Object>} Object with X-Sync-Since and X-Sync-Trip headers.
 */
TTApi._getSyncHeaders = function() {
    var headers = {};
    return TTStorage.get( TT.STORAGE.KEY_SYNC_AS_OF, null )
        .then( function( syncAsOf ) {
            if ( syncAsOf ) {
                headers[TT.HEADERS.SYNC_SINCE] = syncAsOf;
            }
            return TTStorage.get( TT.STORAGE.KEY_CURRENT_TRIP_UUID, null );
        })
        .then( function( tripUuid ) {
            if ( tripUuid ) {
                headers[TT.HEADERS.SYNC_TRIP] = tripUuid;
            }
            return headers;
        });
};

/**
 * Make an authenticated API request.
 * Automatically handles 401 responses by clearing auth state.
 * Includes sync headers (X-Sync-Since, X-Sync-Trip) when available.
 * @param {string} endpoint - The API endpoint (e.g., '/api/v1/me/').
 * @param {Object} options - Fetch options (method, headers, body, etc.).
 * @returns {Promise<Response>} The fetch response.
 */
TTApi.fetch = function( endpoint, options ) {
    options = options || {};

    var serverUrl;
    var token;
    var syncHeaders;

    return TTApi.getServerUrl()
        .then( function( url ) {
            serverUrl = url;
            return TTAuth.getApiToken();
        })
        .then( function( storedToken ) {
            token = storedToken;
            return TTApi._getSyncHeaders();
        })
        .then( function( headers ) {
            syncHeaders = headers;

            var url = serverUrl + endpoint;
            var allHeaders = Object.assign( {}, options.headers || {}, syncHeaders );

            // Add authorization header if we have a token
            if ( token ) {
                allHeaders['Authorization'] = 'Bearer ' + token;
            }

            // Add content type for JSON if body is present
            if ( options.body && !allHeaders['Content-Type'] ) {
                allHeaders['Content-Type'] = 'application/json';
            }

            var fetchOptions = Object.assign( {}, options, { headers: allHeaders } );

            return fetch( url, fetchOptions );
        })
        .then( function( response ) {
            // Handle 401 Unauthorized - token is invalid or expired
            if ( response.status === 401 ) {
                return TTApi._handleAuthFailure()
                    .then( function() {
                        var error = new Error( TT.STRINGS.AUTH_ERROR_INVALID_TOKEN );
                        error.status = 401;
                        throw error;
                    });
            }

            return response;
        })
        .catch( function( error ) {
            // Network errors (server unreachable, CORS, etc.)
            if ( !error.status ) {
                var networkError = new Error( TT.STRINGS.AUTH_ERROR_NETWORK );
                networkError.originalError = error;
                throw networkError;
            }
            throw error;
        });
};

/**
 * Handle authentication failure (401 response).
 * Clears token and auth state, notifies listeners.
 * @private
 * @returns {Promise<void>}
 */
TTApi._handleAuthFailure = function() {
    return TTAuth.disconnect()
        .then( function() {
            if ( TTApi.onAuthFailure ) {
                TTApi.onAuthFailure();
            }
        });
};

/**
 * Make a GET request.
 * @param {string} endpoint - The API endpoint.
 * @returns {Promise<Response>} The fetch response.
 */
TTApi.get = function( endpoint ) {
    return TTApi.fetch( endpoint, { method: 'GET' } );
};

/**
 * Make a POST request with JSON body.
 * @param {string} endpoint - The API endpoint.
 * @param {Object} data - The data to send.
 * @returns {Promise<Response>} The fetch response.
 */
TTApi.post = function( endpoint, data ) {
    return TTApi.fetch( endpoint, {
        method: 'POST',
        body: JSON.stringify( data )
    });
};

/**
 * Get current user info from /api/v1/me/.
 * @returns {Promise<Object>} User info with uuid and email.
 */
TTApi.getMe = function() {
    return TTApi.get( TT.CONFIG.API_ME_ENDPOINT )
        .then( function( response ) {
            if ( !response.ok ) {
                throw new Error( 'Failed to get user info: ' + response.status );
            }
            return response.json();
        });
};

/**
 * Validate a token by calling /api/v1/me/.
 * Temporarily sets the token for the request.
 * @param {string} token - The token to validate.
 * @returns {Promise<Object>} User info if valid.
 */
TTApi.validateToken = function( token ) {
    return TTApi.validateTokenWithSignal( token, null );
};

/**
 * Validate a token with optional AbortSignal for timeout support.
 * @param {string} token - The token to validate.
 * @param {AbortSignal|null} signal - Optional abort signal for timeout.
 * @returns {Promise<Object>} User info if valid.
 */
TTApi.validateTokenWithSignal = function( token, signal ) {
    var serverUrl;

    return TTApi.getServerUrl()
        .then( function( url ) {
            serverUrl = url;

            var headers = {
                'Authorization': 'Bearer ' + token
            };

            var options = {
                method: 'GET',
                headers: headers
            };

            if ( signal ) {
                options.signal = signal;
            }

            return fetch( serverUrl + TT.CONFIG.API_ME_ENDPOINT, options );
        })
        .then( function( response ) {
            if ( response.status === 401 ) {
                var error = new Error( TT.STRINGS.AUTH_ERROR_INVALID_TOKEN );
                error.status = 401;
                throw error;
            }
            if ( response.status >= 500 ) {
                var error = new Error( 'Server error' );
                error.status = response.status;
                throw error;
            }
            if ( !response.ok ) {
                throw new Error( 'Validation failed: ' + response.status );
            }
            return response.json();
        });
};

/**
 * Get extension status from /api/v1/extension/status/.
 * Validates auth and processes sync envelope for trips.
 * Also syncs client config version.
 * @param {string} token - The API token to use.
 * @param {AbortSignal|null} signal - Optional abort signal for timeout.
 * @returns {Promise<Object>} Status data with email and config_version.
 */
TTApi.getExtensionStatus = function( token, signal ) {
    var serverUrl;

    return TTApi.getServerUrl()
        .then( function( url ) {
            serverUrl = url;

            var headers = {
                'Authorization': 'Bearer ' + token
            };

            var options = {
                method: 'GET',
                headers: headers
            };

            if ( signal ) {
                options.signal = signal;
            }

            return fetch( serverUrl + TT.CONFIG.API_EXTENSION_STATUS_ENDPOINT, options );
        })
        .then( function( response ) {
            if ( response.status === 401 ) {
                var error = new Error( TT.STRINGS.AUTH_ERROR_INVALID_TOKEN );
                error.status = 401;
                throw error;
            }
            if ( response.status >= 500 ) {
                var error = new Error( 'Server error' );
                error.status = response.status;
                throw error;
            }
            if ( !response.ok ) {
                throw new Error( 'Status check failed: ' + response.status );
            }
            // Process sync envelope and return data
            return TTApi.processResponse( response );
        })
        .then( function( data ) {
            // Sync client config version (marks stale if version changed)
            if ( data && data.config_version && typeof TTClientConfig !== 'undefined' ) {
                return TTClientConfig.handleVersionSync( data.config_version )
                    .then( function() {
                        return data;
                    });
            }
            return data;
        });
};

/**
 * Make a PATCH request with JSON body.
 * @param {string} endpoint - The API endpoint.
 * @param {Object} data - The data to send.
 * @returns {Promise<Response>} The fetch response.
 */
TTApi.patch = function( endpoint, data ) {
    return TTApi.fetch( endpoint, {
        method: 'PATCH',
        body: JSON.stringify( data )
    });
};

/**
 * Make a DELETE request.
 * @param {string} endpoint - The API endpoint.
 * @returns {Promise<Response>} The fetch response.
 */
TTApi.delete = function( endpoint ) {
    return TTApi.fetch( endpoint, { method: 'DELETE' } );
};

/**
 * Delete a token on the server.
 * @param {string} lookupKey - The token's lookup key.
 * @returns {Promise<void>} Resolves on success, rejects on error.
 */
TTApi.deleteToken = function( lookupKey ) {
    var endpoint = TT.CONFIG.API_TOKENS_ENDPOINT + lookupKey + '/';
    return TTApi.delete( endpoint )
        .then( function( response ) {
            if ( response.status === 404 ) {
                // Token already deleted or doesn't exist - that's fine
                return;
            }
            if ( !response.ok ) {
                throw new Error( 'Failed to delete token: ' + response.status );
            }
        });
};

/**
 * Update a trip with partial data.
 * @param {string} tripUuid - The trip UUID.
 * @param {Object} data - The data to update (e.g., { gmm_map_id: '...' }).
 * @returns {Promise<Object>} Updated trip data.
 */
TTApi.updateTrip = function( tripUuid, data ) {
    var endpoint = TT.CONFIG.API_TRIPS_ENDPOINT + tripUuid + '/';
    return TTApi.patch( endpoint, data )
        .then( function( response ) {
            if ( !response.ok ) {
                throw new Error( 'Failed to update trip: ' + response.status );
            }
            return TTApi.processResponse( response );
        });
};

/**
 * Create a new trip.
 * @param {string} title - The trip title (required).
 * @param {string} description - The trip description (optional).
 * @param {string} gmmMapId - GMM map ID to link (optional).
 * @returns {Promise<Object>} Created trip data.
 */
TTApi.createTrip = function( title, description, gmmMapId ) {
    var data = { title: title };
    if ( description ) {
        data.description = description;
    }
    if ( gmmMapId ) {
        data.gmm_map_id = gmmMapId;
    }
    return TTApi.post( TT.CONFIG.API_TRIPS_ENDPOINT, data )
        .then( function( response ) {
            if ( response.status === 409 ) {
                var error = new Error( 'A trip with this map ID already exists' );
                error.status = 409;
                throw error;
            }
            if ( !response.ok ) {
                throw new Error( 'Failed to create trip: ' + response.status );
            }
            return TTApi.processResponse( response );
        });
};

/**
 * Process API response from TtApiView or SyncableAPIView endpoints.
 *
 * Both view types wrap responses in {data: ...} envelope.
 * SyncableAPIView additionally includes {sync: {...}} which is processed here.
 *
 * @param {Response} response - Fetch Response object.
 * @returns {Promise<Object>} Resolves with the data portion of response.
 */
TTApi.processResponse = function( response ) {
    if ( !response.ok ) {
        return Promise.reject( new Error( 'Request failed: ' + response.status ) );
    }

    return response.json()
        .then( function( json ) {
            var data = json[TT.SYNC.FIELD_DATA];
            // Process sync envelope if present (SyncableAPIView)
            if ( json[TT.SYNC.FIELD_SYNC] ) {
                return TTSync.processEnvelope( json[TT.SYNC.FIELD_SYNC] )
                    .then( function() {
                        return data;
                    });
            }
            return data;
        });
};

// =============================================================================
// Location API Methods
// =============================================================================

/**
 * Get locations for a trip.
 * @param {string} tripUuid - The trip UUID.
 * @returns {Promise<Array>} Array of location objects.
 */
TTApi.getLocations = function( tripUuid ) {
    var endpoint = TT.CONFIG.API_LOCATIONS_ENDPOINT + '?trip=' + tripUuid;
    return TTApi.get( endpoint )
        .then( function( response ) {
            if ( !response.ok ) {
                throw new Error( 'Failed to get locations: ' + response.status );
            }
            return TTApi.processResponse( response );
        });
};

/**
 * Get a single location by UUID.
 * @param {string} locationUuid - The location UUID.
 * @returns {Promise<Object>} Location data.
 */
TTApi.getLocation = function( locationUuid ) {
    var endpoint = TT.CONFIG.API_LOCATIONS_ENDPOINT + locationUuid + '/';
    return TTApi.get( endpoint )
        .then( function( response ) {
            if ( !response.ok ) {
                throw new Error( 'Failed to get location: ' + response.status );
            }
            return TTApi.processResponse( response );
        });
};

/**
 * Get a location by GMM ID within a trip.
 * @param {string} tripUuid - The trip UUID.
 * @param {string} gmmId - The GMM feature ID.
 * @returns {Promise<Object|null>} Location data or null if not found.
 */
TTApi.getLocationByGmmId = function( tripUuid, gmmId ) {
    var endpoint = TT.CONFIG.API_LOCATIONS_ENDPOINT + 'by-gmm-id/' + tripUuid + '/' + gmmId + '/';
    return TTApi.get( endpoint )
        .then( function( response ) {
            if ( response.status === 404 ) {
                return null;
            }
            if ( !response.ok ) {
                throw new Error( 'Failed to get location: ' + response.status );
            }
            return TTApi.processResponse( response );
        });
};

/**
 * Create a new location.
 * @param {Object} locationData - Location data including trip_uuid, title, etc.
 * @returns {Promise<Object>} Created location data.
 */
TTApi.createLocation = function( locationData ) {
    return TTApi.post( TT.CONFIG.API_LOCATIONS_ENDPOINT, locationData )
        .then( function( response ) {
            if ( !response.ok ) {
                throw new Error( 'Failed to create location: ' + response.status );
            }
            return TTApi.processResponse( response );
        });
};

/**
 * Update a location with partial data.
 * @param {string} locationUuid - The location UUID.
 * @param {Object} data - The data to update.
 * @returns {Promise<Object>} Updated location data.
 */
TTApi.updateLocation = function( locationUuid, data ) {
    var endpoint = TT.CONFIG.API_LOCATIONS_ENDPOINT + locationUuid + '/';
    return TTApi.patch( endpoint, data )
        .then( function( response ) {
            if ( !response.ok ) {
                throw new Error( 'Failed to update location: ' + response.status );
            }
            return TTApi.processResponse( response );
        });
};

/**
 * Delete a location.
 * @param {string} locationUuid - The location UUID.
 * @returns {Promise<void>} Resolves on success.
 */
TTApi.deleteLocation = function( locationUuid ) {
    var endpoint = TT.CONFIG.API_LOCATIONS_ENDPOINT + locationUuid + '/';
    return TTApi.delete( endpoint )
        .then( function( response ) {
            if ( !response.ok ) {
                throw new Error( 'Failed to delete location: ' + response.status );
            }
        });
};
