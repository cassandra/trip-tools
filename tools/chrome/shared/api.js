/*
 * Trip Tools Chrome Extension - API Module
 * Provides fetch wrapper with auth headers and 401 handling.
 * Depends on: constants.js, storage.js, auth.js
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
 * Make an authenticated API request.
 * Automatically handles 401 responses by clearing auth state.
 * @param {string} endpoint - The API endpoint (e.g., '/api/v1/me/').
 * @param {Object} options - Fetch options (method, headers, body, etc.).
 * @returns {Promise<Response>} The fetch response.
 */
TTApi.fetch = function( endpoint, options ) {
    options = options || {};

    var serverUrl;
    var token;

    return TTApi.getServerUrl()
        .then( function( url ) {
            serverUrl = url;
            return TTAuth.getApiToken();
        })
        .then( function( storedToken ) {
            token = storedToken;

            var url = serverUrl + endpoint;
            var headers = Object.assign( {}, options.headers || {} );

            // Add authorization header if we have a token
            if ( token ) {
                headers['Authorization'] = 'Bearer ' + token;
            }

            // Add content type for JSON if body is present
            if ( options.body && !headers['Content-Type'] ) {
                headers['Content-Type'] = 'application/json';
            }

            var fetchOptions = Object.assign( {}, options, { headers: headers } );

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
