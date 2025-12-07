"""
Tests for rate limiting decorator.

Tests the rate_limit decorator used to protect Django views from abuse.
"""

import logging
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.test import TestCase, RequestFactory
from django.views import View

from tt.apps.common.rate_limit import rate_limit

logging.disable( logging.CRITICAL )

User = get_user_model()


class RateLimitDecoratorTestCase( TestCase ):
    """Test rate_limit decorator behavior."""

    def setUp(self):
        """Create test user and request factory."""
        self.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpass123',
        )
        self.factory = RequestFactory()

    def _make_view_class(self, limit, period_secs):
        """Create a test view class with rate limiting."""
        class TestView( View ):
            @rate_limit( 'test_ops', limit=limit, period_secs=period_secs )
            def post(self, request, *args, **kwargs):
                return HttpResponse( 'OK', status=200 )

        return TestView

    def test_first_request_succeeds(self):
        """Test first request within rate limit succeeds."""
        with patch( 'tt.apps.common.rate_limit.cache' ) as mock_cache:
            mock_cache.add.return_value = True  # Key didn't exist, was created

            ViewClass = self._make_view_class( limit=10, period_secs=3600 )
            view = ViewClass.as_view()

            request = self.factory.post( '/test/' )
            request.user = self.user

            response = view( request )

            self.assertEqual( response.status_code, 200 )
            mock_cache.add.assert_called_once()

    def test_requests_under_limit_succeed(self):
        """Test requests under rate limit all succeed."""
        with patch( 'tt.apps.common.rate_limit.cache' ) as mock_cache:
            # Simulate incrementing counter (key exists)
            mock_cache.add.return_value = False
            mock_cache.incr.side_effect = [2, 3, 4, 5]  # Return incrementing counts

            ViewClass = self._make_view_class( limit=10, period_secs=3600 )
            view = ViewClass.as_view()

            request = self.factory.post( '/test/' )
            request.user = self.user

            # Make 4 requests, all should succeed
            for i in range( 4 ):
                response = view( request )
                self.assertEqual( response.status_code, 200, f'Request {i+1} should succeed' )

    def test_requests_over_limit_return_429(self):
        """Test requests over rate limit return 429."""
        with patch( 'tt.apps.common.rate_limit.cache' ) as mock_cache:
            mock_cache.add.return_value = False  # Key exists
            mock_cache.incr.return_value = 11  # Over limit of 10

            ViewClass = self._make_view_class( limit=10, period_secs=3600 )
            view = ViewClass.as_view()

            request = self.factory.post( '/test/' )
            request.user = self.user

            response = view( request )

            self.assertEqual( response.status_code, 429 )
            self.assertIn( 'Rate limit', response.content.decode() )

    def test_cache_key_includes_user_id(self):
        """Test cache key includes user ID for per-user limiting."""
        with patch( 'tt.apps.common.rate_limit.cache' ) as mock_cache:
            mock_cache.add.return_value = True

            ViewClass = self._make_view_class( limit=10, period_secs=3600 )
            view = ViewClass.as_view()

            request = self.factory.post( '/test/' )
            request.user = self.user

            view( request )

            # Check that cache.add was called with a key containing the user ID
            call_args = mock_cache.add.call_args
            cache_key = call_args[0][0]
            self.assertIn( str( self.user.id ), cache_key )
            self.assertIn( 'test_ops', cache_key )

    def test_handles_cache_race_condition(self):
        """Test decorator handles race condition when key expires between add and incr."""
        with patch( 'tt.apps.common.rate_limit.cache' ) as mock_cache:
            # Simulate: add returns False (key exists), but incr raises ValueError (key expired)
            mock_cache.add.return_value = False
            mock_cache.incr.side_effect = ValueError( 'Key not found' )

            ViewClass = self._make_view_class( limit=10, period_secs=3600 )
            view = ViewClass.as_view()

            request = self.factory.post( '/test/' )
            request.user = self.user

            response = view( request )

            # Should succeed and set a new key
            self.assertEqual( response.status_code, 200 )
            mock_cache.set.assert_called_once()

    def test_different_key_prefixes_are_independent(self):
        """Test different key prefixes create independent rate limits."""
        with patch( 'tt.apps.common.rate_limit.cache' ) as mock_cache:
            mock_cache.add.return_value = True

            # Two views with different prefixes
            class View1( View ):
                @rate_limit( 'prefix_a', limit=10, period_secs=3600 )
                def post(self, request):
                    return HttpResponse( 'View1' )

            class View2( View ):
                @rate_limit( 'prefix_b', limit=10, period_secs=3600 )
                def post(self, request):
                    return HttpResponse( 'View2' )

            request = self.factory.post( '/test/' )
            request.user = self.user

            View1.as_view()( request )
            View2.as_view()( request )

            # Both should use different cache keys
            calls = mock_cache.add.call_args_list
            self.assertEqual( len( calls ), 2 )
            key1 = calls[0][0][0]
            key2 = calls[1][0][0]
            self.assertIn( 'prefix_a', key1 )
            self.assertIn( 'prefix_b', key2 )
            self.assertNotEqual( key1, key2 )
