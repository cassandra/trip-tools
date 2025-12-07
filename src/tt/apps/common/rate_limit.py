"""
Rate limiting utilities for Django views.

Provides decorators for rate limiting view methods using Django's cache framework.
"""

from functools import wraps

from django.core.cache import cache
from django.http import HttpResponse


def rate_limit( key_prefix: str, limit: int, period_secs: int ):
    """
    Rate limiting decorator for Django class-based view methods.

    Uses Django's cache framework with proper TTL handling:
    - cache.add() sets TTL only on first request (when key doesn't exist)
    - cache.incr() atomically increments without resetting TTL

    Args:
        key_prefix: Prefix for cache key (e.g., 'api_token_ops')
        limit: Maximum requests allowed in the period_secs
        period_secs: Time period_secs in seconds

    Returns:
        429 response if rate limit exceeded, otherwise proceeds to view

    Usage:
        class MyView(View):
            @rate_limit('my_operation', limit=100, period_secs=3600)
            def post(self, request, *args, **kwargs):
                ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(self, request, *args, **kwargs):
            user_id = request.user.id
            cache_key = f'rate_limit:{key_prefix}:{user_id}'

            # Try to add key with initial value 1 (only succeeds if key doesn't exist)
            # This sets the TTL only once when the window starts
            if cache.add( cache_key, 1, period_secs ):
                # Key was created, this is first request in window
                return view_func( self, request, *args, **kwargs )

            # Key exists, increment and check limit
            try:
                count = cache.incr( cache_key )
            except ValueError:
                # Key expired between add() and incr(), treat as first request
                cache.set( cache_key, 1, period_secs )
                return view_func( self, request, *args, **kwargs )

            if count > limit:
                return HttpResponse(
                    'Rate limit exceeded. Please try again later.',
                    status = 429,
                    content_type = 'text/plain',
                )

            return view_func( self, request, *args, **kwargs )
        return wrapped
    return decorator
