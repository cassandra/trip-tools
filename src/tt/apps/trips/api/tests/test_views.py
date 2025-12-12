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

    def test_response_does_not_include_sync( self ):
        """Test response does not include sync envelope (TtApiView, not SyncableAPIView)."""
        TripSyntheticData.create_test_trip(
            user = self.user,
            title = 'Test Trip'
        )

        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + self.token_data.api_token_str
        )
        response = self.client.get( '/api/v1/trips/' )

        self.assertEqual( response.status_code, 200 )
        self.assertNotIn( 'sync', response.json() )


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
        self.assertIn( 'data', response.json() )
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

    def test_response_does_not_include_sync( self ):
        """Test response does not include sync envelope (TtApiView, not SyncableAPIView)."""
        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + self.token_data.api_token_str
        )
        response = self.client.get( f'/api/v1/trips/{self.trip.uuid}/' )

        self.assertEqual( response.status_code, 200 )
        self.assertNotIn( 'sync', response.json() )

    def test_response_includes_gmm_map_id( self ):
        """Test response includes gmm_map_id field."""
        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + self.token_data.api_token_str
        )
        response = self.client.get( f'/api/v1/trips/{self.trip.uuid}/' )

        self.assertEqual( response.status_code, 200 )
        data = response.json()['data']
        self.assertIn( 'gmm_map_id', data )
        self.assertIsNone( data['gmm_map_id'] )


# =============================================================================
# TripItemView PATCH Tests
# =============================================================================

class TripItemViewPatchTestCase( TestCase ):
    """Test PATCH /api/v1/trips/{uuid}/ endpoint."""

    @classmethod
    def setUpTestData( cls ):
        cls.owner = User.objects.create_user(
            email = 'owner@example.com',
            password = 'testpass123'
        )
        cls.editor = User.objects.create_user(
            email = 'editor@example.com',
            password = 'testpass123'
        )
        cls.viewer = User.objects.create_user(
            email = 'viewer@example.com',
            password = 'testpass123'
        )
        cls.non_member = User.objects.create_user(
            email = 'nonmember@example.com',
            password = 'testpass123'
        )
        cls.owner_token = APITokenService.create_token( cls.owner, 'Owner Token' )
        cls.editor_token = APITokenService.create_token( cls.editor, 'Editor Token' )
        cls.viewer_token = APITokenService.create_token( cls.viewer, 'Viewer Token' )
        cls.non_member_token = APITokenService.create_token( cls.non_member, 'Non-member Token' )

    def setUp( self ):
        self.client = APIClient()
        self.trip = TripSyntheticData.create_test_trip(
            user = self.owner,
            title = 'Test Trip',
            trip_status = TripStatus.CURRENT
        )
        TripSyntheticData.add_trip_member(
            trip = self.trip,
            user = self.editor,
            permission_level = TripPermissionLevel.EDITOR,
            added_by = self.owner
        )
        TripSyntheticData.add_trip_member(
            trip = self.trip,
            user = self.viewer,
            permission_level = TripPermissionLevel.VIEWER,
            added_by = self.owner
        )

    def test_requires_authentication( self ):
        """Test endpoint requires authentication."""
        response = self.client.patch(
            f'/api/v1/trips/{self.trip.uuid}/',
            data = { 'gmm_map_id': 'abc123' },
            format = 'json'
        )
        self.assertEqual( response.status_code, 401 )

    def test_owner_can_update_gmm_map_id( self ):
        """Test owner can update gmm_map_id."""
        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + self.owner_token.api_token_str
        )
        response = self.client.patch(
            f'/api/v1/trips/{self.trip.uuid}/',
            data = { 'gmm_map_id': '1ABCxyz123' },
            format = 'json'
        )

        self.assertEqual( response.status_code, 200 )
        data = response.json()['data']
        self.assertEqual( data['gmm_map_id'], '1ABCxyz123' )

        # Verify persisted
        self.trip.refresh_from_db()
        self.assertEqual( self.trip.gmm_map_id, '1ABCxyz123' )

    def test_editor_can_update_gmm_map_id( self ):
        """Test editor can update gmm_map_id."""
        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + self.editor_token.api_token_str
        )
        response = self.client.patch(
            f'/api/v1/trips/{self.trip.uuid}/',
            data = { 'gmm_map_id': '2DEFxyz456' },
            format = 'json'
        )

        self.assertEqual( response.status_code, 200 )
        data = response.json()['data']
        self.assertEqual( data['gmm_map_id'], '2DEFxyz456' )

    def test_viewer_cannot_update( self ):
        """Test viewer cannot update trip."""
        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + self.viewer_token.api_token_str
        )
        response = self.client.patch(
            f'/api/v1/trips/{self.trip.uuid}/',
            data = { 'gmm_map_id': 'should-fail' },
            format = 'json'
        )

        self.assertEqual( response.status_code, 403 )

    def test_non_member_returns_404( self ):
        """Test non-member gets 404 (not 403) for privacy."""
        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + self.non_member_token.api_token_str
        )
        response = self.client.patch(
            f'/api/v1/trips/{self.trip.uuid}/',
            data = { 'gmm_map_id': 'should-fail' },
            format = 'json'
        )

        self.assertEqual( response.status_code, 404 )

    def test_can_update_title( self ):
        """Test can update title field."""
        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + self.owner_token.api_token_str
        )
        response = self.client.patch(
            f'/api/v1/trips/{self.trip.uuid}/',
            data = { 'title': 'New Title' },
            format = 'json'
        )

        self.assertEqual( response.status_code, 200 )
        data = response.json()['data']
        self.assertEqual( data['title'], 'New Title' )

    def test_partial_update_preserves_other_fields( self ):
        """Test partial update only changes specified fields."""
        # Set initial gmm_map_id
        self.trip.gmm_map_id = 'original-id'
        self.trip.save()

        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + self.owner_token.api_token_str
        )
        response = self.client.patch(
            f'/api/v1/trips/{self.trip.uuid}/',
            data = { 'title': 'Changed Title' },
            format = 'json'
        )

        self.assertEqual( response.status_code, 200 )
        data = response.json()['data']
        self.assertEqual( data['title'], 'Changed Title' )
        self.assertEqual( data['gmm_map_id'], 'original-id' )

    def test_can_clear_gmm_map_id( self ):
        """Test can clear gmm_map_id by setting to null."""
        self.trip.gmm_map_id = 'some-id'
        self.trip.save()

        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + self.owner_token.api_token_str
        )
        response = self.client.patch(
            f'/api/v1/trips/{self.trip.uuid}/',
            data = { 'gmm_map_id': None },
            format = 'json'
        )

        self.assertEqual( response.status_code, 200 )
        data = response.json()['data']
        self.assertIsNone( data['gmm_map_id'] )

    def test_nonexistent_trip_returns_404( self ):
        """Test returns 404 for nonexistent UUID."""
        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + self.owner_token.api_token_str
        )
        response = self.client.patch(
            '/api/v1/trips/00000000-0000-0000-0000-000000000000/',
            data = { 'gmm_map_id': 'test' },
            format = 'json'
        )

        self.assertEqual( response.status_code, 404 )


# =============================================================================
# TripByGmmMapView Tests
# =============================================================================

class TripByGmmMapViewTestCase( TestCase ):
    """Test GET /api/v1/trips/by-gmm-map/{gmm_map_id}/ endpoint."""

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
        cls.other_token_data = APITokenService.create_token(
            cls.other_user,
            'Other Token'
        )

    def setUp( self ):
        self.client = APIClient()
        self.trip = TripSyntheticData.create_test_trip(
            user = self.user,
            title = 'Test Trip',
            trip_status = TripStatus.CURRENT
        )
        self.trip.gmm_map_id = '1ABCxyz123'
        self.trip.save()

    def test_requires_authentication( self ):
        """Test endpoint requires authentication."""
        response = self.client.get( '/api/v1/trips/by-gmm-map/1ABCxyz123/' )
        self.assertEqual( response.status_code, 401 )

    def test_returns_trip_when_found_and_user_is_member( self ):
        """Test returns trip when found and user is a member."""
        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + self.token_data.api_token_str
        )
        response = self.client.get( '/api/v1/trips/by-gmm-map/1ABCxyz123/' )

        self.assertEqual( response.status_code, 200 )
        self.assertIn( 'data', response.json() )
        data = response.json()['data']
        self.assertEqual( data['uuid'], str( self.trip.uuid ) )
        self.assertEqual( data['title'], 'Test Trip' )
        self.assertEqual( data['gmm_map_id'], '1ABCxyz123' )

    def test_returns_404_when_gmm_map_id_not_found( self ):
        """Test returns 404 when no trip has the given GMM map ID."""
        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + self.token_data.api_token_str
        )
        response = self.client.get( '/api/v1/trips/by-gmm-map/nonexistent-id/' )

        self.assertEqual( response.status_code, 404 )

    def test_returns_404_when_user_not_member( self ):
        """Test returns 404 (not 403) when user is not a member of the trip."""
        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + self.other_token_data.api_token_str
        )
        response = self.client.get( '/api/v1/trips/by-gmm-map/1ABCxyz123/' )

        # Returns 404 to avoid leaking existence of trips
        self.assertEqual( response.status_code, 404 )

    def test_viewer_can_access_shared_trip( self ):
        """Test viewer permission allows access via GMM map ID."""
        shared_trip = TripSyntheticData.create_test_trip(
            user = self.other_user,
            title = 'Shared Trip'
        )
        shared_trip.gmm_map_id = '2DEFxyz456'
        shared_trip.save()

        TripSyntheticData.add_trip_member(
            trip = shared_trip,
            user = self.user,
            permission_level = TripPermissionLevel.VIEWER,
            added_by = self.other_user
        )

        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + self.token_data.api_token_str
        )
        response = self.client.get( '/api/v1/trips/by-gmm-map/2DEFxyz456/' )

        self.assertEqual( response.status_code, 200 )
        data = response.json()['data']
        self.assertEqual( data['title'], 'Shared Trip' )

    def test_response_includes_required_fields( self ):
        """Test response includes all required fields."""
        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + self.token_data.api_token_str
        )
        response = self.client.get( '/api/v1/trips/by-gmm-map/1ABCxyz123/' )

        self.assertEqual( response.status_code, 200 )
        data = response.json()['data']
        self.assertIn( 'uuid', data )
        self.assertIn( 'title', data )
        self.assertIn( 'trip_status', data )
        self.assertIn( 'version', data )
        self.assertIn( 'created_datetime', data )
        self.assertIn( 'gmm_map_id', data )
