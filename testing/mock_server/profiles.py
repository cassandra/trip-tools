"""
Profile definitions for the mock server.

Each profile defines response configurations for different API endpoints.
Profiles simulate various server states: success, auth failure, errors, timeouts.

Naming convention:
- `ext_` prefix for extension-specific profiles
- Generic names for reusable profiles (server_error, timeout, etc.)
"""

import threading

# Thread-safe profile storage for runtime switching
_profile_lock = threading.Lock()
_current_profile_name = 'ext_auth_success'


PROFILES = {
    # Extension authorization - successful
    'ext_auth_success': {
        'api_me': {
            'status': 200,
            'body': {
                'uuid': '12345678-1234-1234-1234-123456789abc',
                'email': 'test@example.com',
            },
            'delay_ms': 0,
        },
        'api_extension_status': {
            'status': 200,
            'body': {
                'email': 'test@example.com',
                'config_version': 1,
            },
            'delay_ms': 0,
        },
        'api_tokens_delete': {
            'status': 204,
        },
    },

    # Extension authorization - 401 unauthorized
    'ext_auth_401': {
        'api_me': {
            'status': 401,
            'body': {
                'detail': 'Authentication credentials were not provided.',
            },
            'delay_ms': 0,
        },
        'api_extension_status': {
            'status': 401,
            'body': {
                'detail': 'Authentication credentials were not provided.',
            },
            'delay_ms': 0,
        },
    },

    # Extension authorization - different user (for identity change tests)
    'ext_different_user': {
        'api_me': {
            'status': 200,
            'body': {
                'uuid': '87654321-4321-4321-4321-876543210fed',
                'email': 'different@example.com',
            },
            'delay_ms': 0,
        },
        'api_extension_status': {
            'status': 200,
            'body': {
                'email': 'different@example.com',
                'config_version': 1,
            },
            'delay_ms': 0,
        },
    },

    # Generic - server error (500)
    'server_error': {
        'api_me': {
            'status': 500,
            'body': {
                'detail': 'Internal server error',
            },
            'delay_ms': 0,
        },
        'api_extension_status': {
            'status': 500,
            'body': {
                'detail': 'Internal server error',
            },
            'delay_ms': 0,
        },
        'api_tokens_delete': {
            'status': 500,
            'body': {
                'detail': 'Internal server error',
            },
        },
    },

    # Generic - service unavailable (503)
    'service_unavailable': {
        'api_me': {
            'status': 503,
            'body': {
                'detail': 'Service temporarily unavailable',
            },
            'delay_ms': 0,
        },
        'api_extension_status': {
            'status': 503,
            'body': {
                'detail': 'Service temporarily unavailable',
            },
            'delay_ms': 0,
        },
    },

    # Generic - timeout (10s delay exceeds extension's 5s timeout)
    'timeout': {
        'api_me': {
            'status': 200,
            'body': {},
            'delay_ms': 10000,
        },
        'api_extension_status': {
            'status': 200,
            'body': {},
            'delay_ms': 10000,
        },
    },

    # Generic - slow but successful (2s delay)
    'slow_success': {
        'api_me': {
            'status': 200,
            'body': {
                'uuid': '12345678-1234-1234-1234-123456789abc',
                'email': 'slow@example.com',
            },
            'delay_ms': 2000,
        },
        'api_extension_status': {
            'status': 200,
            'body': {
                'email': 'slow@example.com',
                'config_version': 1,
            },
            'delay_ms': 2000,
        },
    },

    # Generic - rate limit (429)
    'rate_limit': {
        'api_me': {
            'status': 429,
            'body': {
                'detail': 'Too many requests',
            },
            'delay_ms': 0,
        },
        'api_extension_status': {
            'status': 429,
            'body': {
                'detail': 'Too many requests',
            },
            'delay_ms': 0,
        },
    },

    # Generic - bad gateway (502)
    'bad_gateway': {
        'api_me': {
            'status': 502,
            'body': {
                'detail': 'Bad Gateway',
            },
            'delay_ms': 0,
        },
        'api_extension_status': {
            'status': 502,
            'body': {
                'detail': 'Bad Gateway',
            },
            'delay_ms': 0,
        },
    },
}


def get_current_profile():
    """Get the current profile configuration dict."""
    with _profile_lock:
        return PROFILES.get(_current_profile_name, PROFILES['ext_auth_success'])


def get_current_profile_name():
    """Get the current profile name."""
    with _profile_lock:
        return _current_profile_name


def set_current_profile(name):
    """Set the current profile by name."""
    global _current_profile_name
    if name not in PROFILES:
        raise ValueError(f'Unknown profile: {name}. Available: {list(PROFILES.keys())}')
    with _profile_lock:
        _current_profile_name = name


def get_endpoint_config(endpoint_key):
    """
    Get the configuration for a specific endpoint from the current profile.

    Args:
        endpoint_key: The endpoint key (e.g., 'api_me', 'api_tokens_delete')

    Returns:
        dict with 'status', 'body', 'delay_ms' keys, or defaults if not configured.
    """
    profile = get_current_profile()
    return profile.get(endpoint_key, {
        'status': 200,
        'body': {},
        'delay_ms': 0,
    })
