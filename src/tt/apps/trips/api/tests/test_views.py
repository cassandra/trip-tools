"""
Tests for Trip API views.

Tests the TripCollectionView and TripItemView endpoints.
"""
import logging

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from tt.apps.api.services import APITokenService
from tt.apps.trips.enums import TripPermissionLevel, TripStatus
from tt.apps.trips.tests.synthetic_data import TripSyntheticData

logging.disable( logging.CRITICAL )

User = get_user_model()


# =============================================================================
# TripCollectionView Tests
# =============================================================================

class TripCollectionViewTestCase( TestCase ):
    """Test GET /api/v1/trips/ endpoint."""

    @classmethod
    def setUpTestData( cls ):
        cls.user = User.objects.create_user(
            email = 'testuser@example.com',
            password = 'testpass123'
        )
        cls.other_user = User.objects.create_user(
            email = 'otheruser@example.com',
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
        response = self.client.get( '/api/v1/trips/' )
        self.assertEqual( response.status_code, 401 )

    def test_returns_user_trips( self ):
        """Test returns trips where user is a member."""
        trip = TripSyntheticData.create_test_trip(
            user = self.user,
            title = 'My Trip',
            trip_status = TripStatus.UPCOMING
        )

        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + self.token_data.api_token_str
        )
        response = self.client.get( '/api/v1/trips/' )

        self.assertEqual( response.status_code, 200 )
        self.assertIn( 'data', response.json() )
        data = response.json()['data']
        self.assertEqual( len( data ), 1 )
        self.assertEqual( data[0]['uuid'], str( trip.uuid ) )
        self.assertEqual( data[0]['title'], 'My Trip' )

    def test_excludes_other_user_trips( self ):
        """Test does not return trips user is not a member of."""
        TripSyntheticData.create_test_trip(
            user = self.other_user,
            title = 'Other Trip',
            trip_status = TripStatus.UPCOMING
        )

        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + self.token_data.api_token_str
        )
        response = self.client.get( '/api/v1/trips/' )

        self.assertEqual( response.status_code, 200 )
        data = response.json()['data']
        self.assertEqual( len( data ), 0 )

    def test_includes_shared_trips( self ):
        """Test includes trips where user is a non-owner member."""
        shared_trip = TripSyntheticData.create_test_trip(
            user = self.other_user,
            title = 'Shared Trip',
            trip_status = TripStatus.UPCOMING
        )
        TripSyntheticData.add_trip_member(
            trip = shared_trip,
            user = self.user,
            permission_level = TripPermissionLevel.VIEWER,
            added_by = self.other_user
        )

        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + self.token_data.api_token_str
        )
        response = self.client.get( '/api/v1/trips/' )

        self.assertEqual( response.status_code, 200 )
        data = response.json()['data']
        self.assertEqual( len( data ), 1 )
        self.assertEqual( data[0]['title'], 'Shared Trip' )

    def test_response_includes_sync_envelope( self ):
        """Test response includes sync envelope."""
        TripSyntheticData.create_test_trip(
            user = self.user,
            title = 'Test Trip'
        )

        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + self.token_data.api_token_str
        )
        response = self.client.get( '/api/v1/trips/' )

        self.assertEqual( response.status_code, 200 )
        json_data = response.json()
        self.assertIn( 'sync', json_data )
        self.assertIn( 'as_of', json_data['sync'] )

    def test_ordered_by_created_datetime_desc( self ):
        """Test trips ordered by created_datetime descending."""
        TripSyntheticData.create_test_trip(
            user = self.user,
            title = 'First Trip'
        )
        TripSyntheticData.create_test_trip(
            user = self.user,
            title = 'Second Trip'
        )

        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + self.token_data.api_token_str
        )
        response = self.client.get( '/api/v1/trips/' )

        data = response.json()['data']
        self.assertEqual( len( data ), 2 )
        # Second trip created later, should be first
        self.assertEqual( data[0]['title'], 'Second Trip' )
        self.assertEqual( data[1]['title'], 'First Trip' )

    def test_response_includes_required_fields( self ):
        """Test response includes all required fields."""
        TripSyntheticData.create_test_trip(
            user = self.user,
            title = 'Test Trip',
            trip_status = TripStatus.CURRENT
        )

        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + self.token_data.api_token_str
        )
        response = self.client.get( '/api/v1/trips/' )

        self.assertEqual( response.status_code, 200 )
        data = response.json()['data'][0]
        self.assertIn( 'uuid', data )
        self.assertIn( 'title', data )
        self.assertIn( 'trip_status', data )
        self.assertIn( 'version', data )
        self.assertIn( 'created_datetime', data )


# =============================================================================
# TripItemView Tests
# =============================================================================

class TripItemViewTestCase( TestCase ):
    """Test GET /api/v1/trips/{uuid}/ endpoint."""

    @classmethod
    def setUpTestData( cls ):
        cls.user = User.objects.create_user(
            email = 'testuser@example.com',
            password = 'testpass123'
        )
        cls.other_user = User.objects.create_user(
            email = 'otheruser@example.com',
            password = 'testpass123'
        )
        cls.token_data = APITokenService.create_token(
            cls.user,
            'Test Token'
        )
        cls.trip = TripSyntheticData.create_test_trip(
            user = cls.user,
            title = 'Test Trip',
            trip_status = TripStatus.CURRENT
        )

    def setUp( self ):
        self.client = APIClient()

    def test_requires_authentication( self ):
        """Test endpoint requires authentication."""
        response = self.client.get( f'/api/v1/trips/{self.trip.uuid}/' )
        self.assertEqual( response.status_code, 401 )

    def test_returns_trip_for_owner( self ):
        """Test returns trip for owner."""
        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + self.token_data.api_token_str
        )
        response = self.client.get( f'/api/v1/trips/{self.trip.uuid}/' )

        self.assertEqual( response.status_code, 200 )
        data = response.json()['data']
        self.assertEqual( data['uuid'], str( self.trip.uuid ) )
        self.assertEqual( data['title'], 'Test Trip' )
        self.assertIn( 'version', data )
        self.assertIn( 'created_datetime', data )

    def test_returns_404_for_non_member( self ):
        """Test returns 404 for non-member (not 403)."""
        other_token_data = APITokenService.create_token(
            self.other_user,
            'Other Token'
        )

        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + other_token_data.api_token_str
        )
        response = self.client.get( f'/api/v1/trips/{self.trip.uuid}/' )

        self.assertEqual( response.status_code, 404 )

    def test_returns_404_for_nonexistent_trip( self ):
        """Test returns 404 for nonexistent UUID."""
        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + self.token_data.api_token_str
        )
        response = self.client.get( '/api/v1/trips/00000000-0000-0000-0000-000000000000/' )

        self.assertEqual( response.status_code, 404 )

    def test_viewer_can_access_shared_trip( self ):
        """Test viewer permission allows access."""
        shared_trip = TripSyntheticData.create_test_trip(
            user = self.other_user,
            title = 'Shared Trip'
        )
        TripSyntheticData.add_trip_member(
            trip = shared_trip,
            user = self.user,
            permission_level = TripPermissionLevel.VIEWER,
            added_by = self.other_user
        )

        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + self.token_data.api_token_str
        )
        response = self.client.get( f'/api/v1/trips/{shared_trip.uuid}/' )

        self.assertEqual( response.status_code, 200 )
        data = response.json()['data']
        self.assertEqual( data['title'], 'Shared Trip' )

    def test_response_includes_sync_envelope( self ):
        """Test response includes sync envelope."""
        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + self.token_data.api_token_str
        )
        response = self.client.get( f'/api/v1/trips/{self.trip.uuid}/' )

        self.assertEqual( response.status_code, 200 )
        json_data = response.json()
        self.assertIn( 'sync', json_data )
        self.assertIn( 'as_of', json_data['sync'] )
