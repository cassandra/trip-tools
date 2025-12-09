"""
Tests for API views.

Focuses on high-value testing of:
- SyncableAPIView response wrapping behavior
- Header parsing (X-Sync-Since, X-Sync-Trip)
- Sync envelope inclusion for authenticated requests
- ExtensionStatusView response format
"""
import logging
from datetime import datetime
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.test import APIClient, APIRequestFactory

from tt.apps.api.services import APITokenService
from tt.apps.api.views import SyncableAPIView
from tt.apps.trips.tests.synthetic_data import TripSyntheticData

logging.disable(logging.CRITICAL)

User = get_user_model()


# =============================================================================
# Test View for SyncableAPIView Tests
# =============================================================================

class TestSyncableView(SyncableAPIView):
    """Test view that inherits from SyncableAPIView."""
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({'message': 'test data'})


class AuthenticatedTestSyncableView(SyncableAPIView):
    """Test view requiring authentication."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({'items': [1, 2, 3]})


# =============================================================================
# SyncableAPIView Response Wrapping Tests
# =============================================================================

class SyncableAPIViewResponseWrappingTestCase(TestCase):
    """Test SyncableAPIView response wrapping behavior."""

    @classmethod
    def setUpTestData(cls):
        """Create test user once for all tests."""
        cls.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpass123'
        )
        cls.factory = APIRequestFactory()

    def test_authenticated_request_wraps_response(self):
        """Test authenticated request wraps response with sync envelope."""
        request = self.factory.get('/test/')
        request.user = self.user

        view = TestSyncableView.as_view()
        response = view(request)

        # Response should be wrapped
        self.assertIn('data', response.data)
        self.assertIn('sync', response.data)
        self.assertEqual(response.data['data'], {'message': 'test data'})

    def test_anonymous_request_wraps_without_trip_sync(self):
        """Test anonymous request wraps response without trip sync."""
        from django.contrib.auth.models import AnonymousUser

        request = self.factory.get('/test/')
        request.user = AnonymousUser()

        view = TestSyncableView.as_view()
        response = view(request)

        # Response should be wrapped with sync envelope
        self.assertIn('data', response.data)
        self.assertIn('sync', response.data)
        self.assertEqual(response.data['data'], {'message': 'test data'})
        # Trip sync should be absent (not applicable for anonymous)
        self.assertNotIn('trip', response.data['sync'])

    def test_sync_envelope_includes_as_of(self):
        """Test sync envelope includes as_of timestamp."""
        request = self.factory.get('/test/')
        request.user = self.user

        view = TestSyncableView.as_view()
        response = view(request)

        sync = response.data['sync']
        self.assertIn('as_of', sync)
        # Should be valid ISO format
        datetime.fromisoformat(sync['as_of'].replace('Z', '+00:00'))

    def test_sync_envelope_includes_trip_versions(self):
        """Test sync envelope includes trip versions."""
        trip = TripSyntheticData.create_test_trip(
            user=self.user,
            title='Test Trip'
        )

        request = self.factory.get('/test/')
        request.user = self.user

        view = TestSyncableView.as_view()
        response = view(request)

        sync = response.data['sync']
        self.assertIn('trip', sync)
        self.assertIn('versions', sync['trip'])
        self.assertIn(str(trip.uuid), sync['trip']['versions'])

    def test_sync_envelope_excludes_past_trips(self):
        """Test sync envelope excludes trips with PAST status."""
        from tt.apps.trips.enums import TripStatus

        upcoming_trip = TripSyntheticData.create_test_trip(
            user=self.user,
            title='Upcoming Trip',
            trip_status=TripStatus.UPCOMING
        )
        past_trip = TripSyntheticData.create_test_trip(
            user=self.user,
            title='Past Trip',
            trip_status=TripStatus.PAST
        )

        request = self.factory.get('/test/')
        request.user = self.user

        view = TestSyncableView.as_view()
        response = view(request)

        sync = response.data['sync']
        versions = sync['trip']['versions']
        self.assertIn(str(upcoming_trip.uuid), versions)
        self.assertNotIn(str(past_trip.uuid), versions)


# =============================================================================
# SyncableAPIView Header Parsing Tests
# =============================================================================

class SyncableAPIViewHeaderParsingTestCase(TestCase):
    """Test SyncableAPIView header parsing."""

    @classmethod
    def setUpTestData(cls):
        """Create test user once for all tests."""
        cls.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpass123'
        )
        cls.factory = APIRequestFactory()

    def test_parse_sync_since_valid_iso8601(self):
        """Test X-Sync-Since header is parsed correctly."""
        view = TestSyncableView()

        request = self.factory.get('/test/')
        request.user = self.user

        # Set header
        request.META['HTTP_X_SYNC_SINCE'] = '2025-01-15T10:30:00Z'

        result = view._parse_sync_since(request)
        self.assertIsNotNone(result)
        self.assertEqual(result.year, 2025)
        self.assertEqual(result.month, 1)
        self.assertEqual(result.day, 15)

    def test_parse_sync_since_with_offset(self):
        """Test X-Sync-Since with timezone offset."""
        view = TestSyncableView()

        request = self.factory.get('/test/')
        request.META['HTTP_X_SYNC_SINCE'] = '2025-01-15T10:30:00+05:30'

        result = view._parse_sync_since(request)
        self.assertIsNotNone(result)

    def test_parse_sync_since_missing_returns_none(self):
        """Test missing X-Sync-Since returns None."""
        view = TestSyncableView()

        request = self.factory.get('/test/')

        result = view._parse_sync_since(request)
        self.assertIsNone(result)

    def test_parse_sync_since_invalid_returns_none(self):
        """Test invalid X-Sync-Since returns None (graceful handling)."""
        view = TestSyncableView()

        request = self.factory.get('/test/')
        request.META['HTTP_X_SYNC_SINCE'] = 'not-a-valid-timestamp'

        result = view._parse_sync_since(request)
        self.assertIsNone(result)

    def test_parse_sync_trip_valid_uuid(self):
        """Test X-Sync-Trip header is parsed correctly."""
        view = TestSyncableView()

        request = self.factory.get('/test/')
        trip_uuid = uuid4()
        request.META['HTTP_X_SYNC_TRIP'] = str(trip_uuid)

        result = view._parse_sync_trip(request)
        self.assertEqual(result, trip_uuid)

    def test_parse_sync_trip_missing_returns_none(self):
        """Test missing X-Sync-Trip returns None."""
        view = TestSyncableView()

        request = self.factory.get('/test/')

        result = view._parse_sync_trip(request)
        self.assertIsNone(result)

    def test_parse_sync_trip_invalid_returns_none(self):
        """Test invalid X-Sync-Trip returns None (graceful handling)."""
        view = TestSyncableView()

        request = self.factory.get('/test/')
        request.META['HTTP_X_SYNC_TRIP'] = 'not-a-uuid'

        result = view._parse_sync_trip(request)
        self.assertIsNone(result)


# =============================================================================
# SyncableAPIView Location Sync Tests
# =============================================================================

class SyncableAPIViewLocationSyncTestCase(TestCase):
    """Test SyncableAPIView location sync inclusion."""

    @classmethod
    def setUpTestData(cls):
        """Create test user and trip once for all tests."""
        cls.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpass123'
        )
        cls.factory = APIRequestFactory()

    def test_location_sync_included_with_trip_header(self):
        """Test location sync included when X-Sync-Trip header present."""
        trip = TripSyntheticData.create_test_trip(
            user=self.user,
            title='Test Trip'
        )

        request = self.factory.get('/test/')
        request.user = self.user
        request.META['HTTP_X_SYNC_TRIP'] = str(trip.uuid)

        view = TestSyncableView.as_view()
        response = view(request)

        sync = response.data['sync']
        self.assertIn('location', sync)
        self.assertIn('versions', sync['location'])
        self.assertIn('deleted', sync['location'])

    def test_location_sync_excluded_without_trip_header(self):
        """Test location sync excluded when X-Sync-Trip header absent."""
        TripSyntheticData.create_test_trip(
            user=self.user,
            title='Test Trip'
        )

        request = self.factory.get('/test/')
        request.user = self.user

        view = TestSyncableView.as_view()
        response = view(request)

        sync = response.data['sync']
        self.assertNotIn('location', sync)


# =============================================================================
# ExtensionStatusView Tests
# =============================================================================

class ExtensionStatusViewTestCase( TestCase ):
    """Test GET /api/v1/extension/status/ endpoint."""

    @classmethod
    def setUpTestData( cls ):
        cls.user = User.objects.create_user(
            email = 'testuser@example.com',
            password = 'testpass123'
        )
        cls.token_data = APITokenService.create_token(
            cls.user,
            'Test Token'
        )

    def setUp( self ):
        self.client = APIClient()

    def test_requires_authentication( self ):
        """Test endpoint requires authentication."""
        response = self.client.get( '/api/v1/extension/status/' )
        self.assertEqual( response.status_code, 401 )

    def test_returns_user_email( self ):
        """Test returns user email."""
        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + self.token_data.api_token_str
        )
        response = self.client.get( '/api/v1/extension/status/' )

        self.assertEqual( response.status_code, 200 )
        self.assertIn( 'data', response.json() )
        data = response.json()['data']
        self.assertEqual( data['email'], 'testuser@example.com' )

    def test_returns_config_version( self ):
        """Test returns config_version field as MD5 hash."""
        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + self.token_data.api_token_str
        )
        response = self.client.get( '/api/v1/extension/status/' )

        self.assertEqual( response.status_code, 200 )
        data = response.json()['data']
        self.assertIn( 'config_version', data )
        # config_version is an MD5 hash (32 hex characters)
        version = data['config_version']
        self.assertEqual( len( version ), 32 )
        self.assertTrue( all( c in '0123456789abcdef' for c in version ) )

    def test_response_includes_sync_envelope( self ):
        """Test response includes sync envelope."""
        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + self.token_data.api_token_str
        )
        response = self.client.get( '/api/v1/extension/status/' )

        self.assertEqual( response.status_code, 200 )
        json_data = response.json()
        self.assertIn( 'sync', json_data )
        self.assertIn( 'as_of', json_data['sync'] )
        self.assertIn( 'trip', json_data['sync'] )

    def test_sync_includes_user_trips( self ):
        """Test sync envelope includes user's accessible trips."""
        trip = TripSyntheticData.create_test_trip(
            user = self.user,
            title = 'Test Trip'
        )

        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + self.token_data.api_token_str
        )
        response = self.client.get( '/api/v1/extension/status/' )

        self.assertEqual( response.status_code, 200 )
        sync = response.json()['sync']
        self.assertIn( str( trip.uuid ), sync['trip']['versions'] )
