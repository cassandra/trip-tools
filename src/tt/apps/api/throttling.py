"""
DRF throttling classes for API rate limiting.

Provides rate limiting for both authenticated and unauthenticated API requests.
"""

from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class APIUserRateThrottle( UserRateThrottle ):
    """Rate limit for authenticated API users."""
    scope = 'api_user'


class APIAnonRateThrottle( AnonRateThrottle ):
    """Rate limit for unauthenticated API requests (auth attempts)."""
    scope = 'api_anon'
