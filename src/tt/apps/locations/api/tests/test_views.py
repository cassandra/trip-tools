"""
Tests for Location API views.

Tests the LocationCollectionView and LocationItemView endpoints.
"""
import logging
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from tt.apps.api.services import APITokenService
from tt.apps.locations.models import Location, LocationCategory, LocationNote, LocationSubCategory
from tt.apps.trips.enums import TripPermissionLevel, TripStatus
from tt.apps.trips.tests.synthetic_data import TripSyntheticData

logging.disable( logging.CRITICAL )

User = get_user_model()


# =============================================================================
# LocationCollectionView Tests - GET
# =============================================================================

class LocationCollectionViewGetTestCase( TestCase ):
    """Test GET /api/v1/locations/?trip={uuid} endpoint."""

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
        # Get or create a subcategory for testing
        cls.category, _ = LocationCategory.objects.get_or_create(
            slug = 'attractions',
            defaults = {
                'name': 'Attractions',
                'icon_code': '1535',
                'color_code': 'RGB(245,124,0)',
            }
        )
        cls.subcategory, _ = LocationSubCategory.objects.get_or_create(
            slug = 'museum',
            defaults = {
                'category': cls.category,
                'name': 'Museum',
                'icon_code': '1636',
                'color_code': 'RGB(245,124,0)',
            }
        )

    def setUp( self ):
        self.client = APIClient()

    def test_requires_authentication( self ):
        """Test endpoint requires authentication."""
        response = self.client.get( f'/api/v1/locations/?trip={self.trip.uuid}' )
        self.assertEqual( response.status_code, 401 )

    def test_requires_trip_parameter( self ):
        """Test endpoint requires trip query parameter."""
        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + self.token_data.api_token_str
        )
        response = self.client.get( '/api/v1/locations/' )

        self.assertEqual( response.status_code, 400 )
        self.assertIn( 'error', response.json() )

    def test_invalid_trip_uuid_returns_400( self ):
        """Test invalid trip UUID format returns 400."""
        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + self.token_data.api_token_str
        )
        response = self.client.get( '/api/v1/locations/?trip=invalid-uuid' )

        self.assertEqual( response.status_code, 400 )
        self.assertIn( 'error', response.json() )

    def test_returns_locations_for_trip( self ):
        """Test returns locations for specified trip."""
        location = Location.objects.create(
            trip = self.trip,
            title = 'Test Location',
            latitude = Decimal( '45.123456' ),
            longitude = Decimal( '-122.654321' ),
        )

        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + self.token_data.api_token_str
        )
        response = self.client.get( f'/api/v1/locations/?trip={self.trip.uuid}' )

        self.assertEqual( response.status_code, 200 )
        self.assertIn( 'data', response.json() )
        data = response.json()['data']
        self.assertEqual( len( data ), 1 )
        self.assertEqual( data[0]['uuid'], str( location.uuid ) )
        self.assertEqual( data[0]['title'], 'Test Location' )

    def test_returns_empty_list_for_trip_with_no_locations( self ):
        """Test returns empty list when trip has no locations."""
        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + self.token_data.api_token_str
        )
        response = self.client.get( f'/api/v1/locations/?trip={self.trip.uuid}' )

        self.assertEqual( response.status_code, 200 )
        data = response.json()['data']
        self.assertEqual( len( data ), 0 )

    def test_non_member_returns_404( self ):
        """Test non-member gets 404 (not 403) for privacy."""
        other_token_data = APITokenService.create_token(
            self.other_user,
            'Other Token'
        )

        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + other_token_data.api_token_str
        )
        response = self.client.get( f'/api/v1/locations/?trip={self.trip.uuid}' )

        self.assertEqual( response.status_code, 404 )

    def test_viewer_can_access_locations( self ):
        """Test viewer permission allows access."""
        TripSyntheticData.add_trip_member(
            trip = self.trip,
            user = self.other_user,
            permission_level = TripPermissionLevel.VIEWER,
            added_by = self.user
        )
        other_token_data = APITokenService.create_token(
            self.other_user,
            'Other Token'
        )
        Location.objects.create(
            trip = self.trip,
            title = 'Viewer Test Location',
        )

        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + other_token_data.api_token_str
        )
        response = self.client.get( f'/api/v1/locations/?trip={self.trip.uuid}' )

        self.assertEqual( response.status_code, 200 )
        data = response.json()['data']
        self.assertEqual( len( data ), 1 )

    def test_response_includes_nested_location_notes( self ):
        """Test response includes nested location_notes array."""
        location = Location.objects.create(
            trip = self.trip,
            title = 'Location With Notes',
        )
        LocationNote.objects.create(
            location = location,
            text = 'This is a test note',
            source_label = 'Test Source',
            source_url = 'https://example.com',
        )

        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + self.token_data.api_token_str
        )
        response = self.client.get( f'/api/v1/locations/?trip={self.trip.uuid}' )

        self.assertEqual( response.status_code, 200 )
        data = response.json()['data']
        self.assertEqual( len( data ), 1 )
        self.assertIn( 'location_notes', data[0] )
        notes = data[0]['location_notes']
        self.assertEqual( len( notes ), 1 )
        self.assertEqual( notes[0]['text'], 'This is a test note' )
        self.assertEqual( notes[0]['source_label'], 'Test Source' )
        self.assertEqual( notes[0]['source_url'], 'https://example.com' )

    def test_response_includes_all_required_fields( self ):
        """Test response includes all required location fields."""
        location = Location.objects.create(
            trip = self.trip,
            title = 'Complete Location',
            latitude = Decimal( '45.123456' ),
            longitude = Decimal( '-122.654321' ),
            elevation_ft = Decimal( '1234.56' ),
            subcategory = self.subcategory,
            rating = Decimal( '4.5' ),
            desirability = 'HIGH',
            advanced_booking = 'ADVISABLE',
            open_days_times = 'Mon-Fri 9am-5pm',
            gmm_id = 'gmm_abc123',
        )

        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + self.token_data.api_token_str
        )
        response = self.client.get( f'/api/v1/locations/?trip={self.trip.uuid}' )

        self.assertEqual( response.status_code, 200 )
        data = response.json()['data'][0]

        # Check all required fields
        self.assertEqual( data['uuid'], str( location.uuid ) )
        self.assertEqual( data['trip_uuid'], str( self.trip.uuid ) )
        self.assertEqual( data['title'], 'Complete Location' )
        self.assertEqual( data['latitude'], 45.123456 )
        self.assertEqual( data['longitude'], -122.654321 )
        self.assertEqual( data['elevation_ft'], 1234.56 )
        self.assertEqual( data['subcategory_slug'], 'museum' )
        self.assertEqual( data['rating'], 4.5 )
        self.assertEqual( data['desirability'], 'high' )
        self.assertEqual( data['advanced_booking'], 'advisable' )
        self.assertEqual( data['open_days_times'], 'Mon-Fri 9am-5pm' )
        self.assertEqual( data['gmm_id'], 'gmm_abc123' )
        self.assertIn( 'version', data )
        self.assertIn( 'created_datetime', data )
        self.assertIn( 'modified_datetime', data )
        self.assertIn( 'location_notes', data )


# =============================================================================
# LocationCollectionView Tests - POST
# =============================================================================

class LocationCollectionViewPostTestCase( TestCase ):
    """Test POST /api/v1/locations/ endpoint."""

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

        # Get or create subcategory
        cls.category, _ = LocationCategory.objects.get_or_create(
            slug = 'attractions',
            defaults = {
                'name': 'Attractions',
                'icon_code': '1535',
                'color_code': 'RGB(245,124,0)',
            }
        )
        cls.subcategory, _ = LocationSubCategory.objects.get_or_create(
            slug = 'museum',
            defaults = {
                'category': cls.category,
                'name': 'Museum',
                'icon_code': '1636',
                'color_code': 'RGB(245,124,0)',
            }
        )

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
        response = self.client.post(
            '/api/v1/locations/',
            data = {
                'trip_uuid': str( self.trip.uuid ),
                'title': 'New Location',
            },
            format = 'json'
        )
        self.assertEqual( response.status_code, 401 )

    def test_requires_trip_uuid( self ):
        """Test endpoint requires trip_uuid in body."""
        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + self.owner_token.api_token_str
        )
        response = self.client.post(
            '/api/v1/locations/',
            data = { 'title': 'New Location' },
            format = 'json'
        )

        self.assertEqual( response.status_code, 400 )
        self.assertIn( 'error', response.json() )

    def test_owner_can_create_location( self ):
        """Test owner can create location."""
        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + self.owner_token.api_token_str
        )
        response = self.client.post(
            '/api/v1/locations/',
            data = {
                'trip_uuid': str( self.trip.uuid ),
                'title': 'New Location',
                'latitude': '45.123456',
                'longitude': '-122.654321',
            },
            format = 'json'
        )

        self.assertEqual( response.status_code, 201 )
        data = response.json()['data']
        self.assertEqual( data['title'], 'New Location' )
        self.assertEqual( data['trip_uuid'], str( self.trip.uuid ) )
        self.assertIn( 'uuid', data )
        self.assertIn( 'version', data )

        # Verify persisted
        location = Location.objects.get( uuid = data['uuid'] )
        self.assertEqual( location.title, 'New Location' )
        self.assertEqual( location.trip, self.trip )

    def test_editor_can_create_location( self ):
        """Test editor can create location."""
        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + self.editor_token.api_token_str
        )
        response = self.client.post(
            '/api/v1/locations/',
            data = {
                'trip_uuid': str( self.trip.uuid ),
                'title': 'Editor Location',
            },
            format = 'json'
        )

        self.assertEqual( response.status_code, 201 )
        data = response.json()['data']
        self.assertEqual( data['title'], 'Editor Location' )

    def test_viewer_cannot_create_location( self ):
        """Test viewer cannot create location."""
        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + self.viewer_token.api_token_str
        )
        response = self.client.post(
            '/api/v1/locations/',
            data = {
                'trip_uuid': str( self.trip.uuid ),
                'title': 'Should Fail',
            },
            format = 'json'
        )

        self.assertEqual( response.status_code, 403 )

    def test_non_member_returns_404( self ):
        """Test non-member gets 404 (not 403) for privacy."""
        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + self.non_member_token.api_token_str
        )
        response = self.client.post(
            '/api/v1/locations/',
            data = {
                'trip_uuid': str( self.trip.uuid ),
                'title': 'Should Fail',
            },
            format = 'json'
        )

        self.assertEqual( response.status_code, 404 )

    def test_create_with_subcategory_slug( self ):
        """Test creating location with subcategory_slug."""
        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + self.owner_token.api_token_str
        )
        response = self.client.post(
            '/api/v1/locations/',
            data = {
                'trip_uuid': str( self.trip.uuid ),
                'title': 'Museum Location',
                'subcategory_slug': 'museum',
            },
            format = 'json'
        )

        self.assertEqual( response.status_code, 201 )
        data = response.json()['data']
        self.assertEqual( data['subcategory_slug'], 'museum' )

    def test_create_with_all_fields( self ):
        """Test creating location with all optional fields."""
        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + self.owner_token.api_token_str
        )
        response = self.client.post(
            '/api/v1/locations/',
            data = {
                'trip_uuid': str( self.trip.uuid ),
                'title': 'Complete Location',
                'latitude': '45.123456',
                'longitude': '-122.654321',
                'elevation_ft': '1234.56',
                'subcategory_slug': 'museum',
                'rating': '4.5',
                'desirability': 'HIGH',
                'advanced_booking': 'ADVISABLE',
                'open_days_times': 'Mon-Fri 9am-5pm',
                'gmm_id': 'gmm_test123',
            },
            format = 'json'
        )

        self.assertEqual( response.status_code, 201 )
        data = response.json()['data']
        self.assertEqual( data['title'], 'Complete Location' )
        self.assertEqual( data['latitude'], 45.123456 )
        self.assertEqual( data['longitude'], -122.654321 )
        self.assertEqual( data['elevation_ft'], 1234.56 )
        self.assertEqual( data['subcategory_slug'], 'museum' )
        self.assertEqual( data['rating'], 4.5 )
        self.assertEqual( data['desirability'], 'high' )
        self.assertEqual( data['advanced_booking'], 'advisable' )
        self.assertEqual( data['open_days_times'], 'Mon-Fri 9am-5pm' )
        self.assertEqual( data['gmm_id'], 'gmm_test123' )


# =============================================================================
# LocationItemView Tests - GET
# =============================================================================

class LocationItemViewGetTestCase( TestCase ):
    """Test GET /api/v1/locations/{uuid}/ endpoint."""

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
        cls.location = Location.objects.create(
            trip = cls.trip,
            title = 'Test Location',
            latitude = Decimal( '45.123456' ),
            longitude = Decimal( '-122.654321' ),
        )

    def setUp( self ):
        self.client = APIClient()

    def test_requires_authentication( self ):
        """Test endpoint requires authentication."""
        response = self.client.get( f'/api/v1/locations/{self.location.uuid}/' )
        self.assertEqual( response.status_code, 401 )

    def test_returns_location_for_member( self ):
        """Test returns location for trip member."""
        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + self.token_data.api_token_str
        )
        response = self.client.get( f'/api/v1/locations/{self.location.uuid}/' )

        self.assertEqual( response.status_code, 200 )
        self.assertIn( 'data', response.json() )
        data = response.json()['data']
        self.assertEqual( data['uuid'], str( self.location.uuid ) )
        self.assertEqual( data['title'], 'Test Location' )

    def test_returns_404_for_non_member( self ):
        """Test returns 404 for non-member (not 403)."""
        other_token_data = APITokenService.create_token(
            self.other_user,
            'Other Token'
        )

        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + other_token_data.api_token_str
        )
        response = self.client.get( f'/api/v1/locations/{self.location.uuid}/' )

        self.assertEqual( response.status_code, 404 )

    def test_returns_404_for_nonexistent_location( self ):
        """Test returns 404 for nonexistent UUID."""
        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + self.token_data.api_token_str
        )
        response = self.client.get( '/api/v1/locations/00000000-0000-0000-0000-000000000000/' )

        self.assertEqual( response.status_code, 404 )

    def test_viewer_can_access_location( self ):
        """Test viewer permission allows access."""
        TripSyntheticData.add_trip_member(
            trip = self.trip,
            user = self.other_user,
            permission_level = TripPermissionLevel.VIEWER,
            added_by = self.user
        )
        other_token_data = APITokenService.create_token(
            self.other_user,
            'Other Token'
        )

        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + other_token_data.api_token_str
        )
        response = self.client.get( f'/api/v1/locations/{self.location.uuid}/' )

        self.assertEqual( response.status_code, 200 )
        data = response.json()['data']
        self.assertEqual( data['title'], 'Test Location' )

    def test_includes_location_notes( self ):
        """Test response includes nested location_notes."""
        LocationNote.objects.create(
            location = self.location,
            text = 'Test note text',
            source_label = 'Wikipedia',
            source_url = 'https://wikipedia.org',
        )

        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + self.token_data.api_token_str
        )
        response = self.client.get( f'/api/v1/locations/{self.location.uuid}/' )

        self.assertEqual( response.status_code, 200 )
        data = response.json()['data']
        self.assertIn( 'location_notes', data )
        self.assertEqual( len( data['location_notes'] ), 1 )
        self.assertEqual( data['location_notes'][0]['text'], 'Test note text' )


# =============================================================================
# LocationItemView Tests - PATCH
# =============================================================================

class LocationItemViewPatchTestCase( TestCase ):
    """Test PATCH /api/v1/locations/{uuid}/ endpoint."""

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

        # Get or create subcategory
        cls.category, _ = LocationCategory.objects.get_or_create(
            slug = 'attractions',
            defaults = {
                'name': 'Attractions',
                'icon_code': '1535',
                'color_code': 'RGB(245,124,0)',
            }
        )
        cls.subcategory, _ = LocationSubCategory.objects.get_or_create(
            slug = 'museum',
            defaults = {
                'category': cls.category,
                'name': 'Museum',
                'icon_code': '1636',
                'color_code': 'RGB(245,124,0)',
            }
        )
        cls.other_subcategory, _ = LocationSubCategory.objects.get_or_create(
            slug = 'park',
            defaults = {
                'category': cls.category,
                'name': 'Park',
                'icon_code': '1582',
                'color_code': 'RGB(245,124,0)',
            }
        )

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
        self.location = Location.objects.create(
            trip = self.trip,
            title = 'Original Title',
            latitude = Decimal( '45.000000' ),
            longitude = Decimal( '-122.000000' ),
        )

    def test_requires_authentication( self ):
        """Test endpoint requires authentication."""
        response = self.client.patch(
            f'/api/v1/locations/{self.location.uuid}/',
            data = { 'title': 'New Title' },
            format = 'json'
        )
        self.assertEqual( response.status_code, 401 )

    def test_owner_can_update_location( self ):
        """Test owner can update location."""
        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + self.owner_token.api_token_str
        )
        response = self.client.patch(
            f'/api/v1/locations/{self.location.uuid}/',
            data = { 'title': 'Updated Title' },
            format = 'json'
        )

        self.assertEqual( response.status_code, 200 )
        data = response.json()['data']
        self.assertEqual( data['title'], 'Updated Title' )

        # Verify persisted
        self.location.refresh_from_db()
        self.assertEqual( self.location.title, 'Updated Title' )

    def test_editor_can_update_location( self ):
        """Test editor can update location."""
        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + self.editor_token.api_token_str
        )
        response = self.client.patch(
            f'/api/v1/locations/{self.location.uuid}/',
            data = { 'title': 'Editor Updated' },
            format = 'json'
        )

        self.assertEqual( response.status_code, 200 )
        data = response.json()['data']
        self.assertEqual( data['title'], 'Editor Updated' )

    def test_viewer_cannot_update_location( self ):
        """Test viewer cannot update location."""
        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + self.viewer_token.api_token_str
        )
        response = self.client.patch(
            f'/api/v1/locations/{self.location.uuid}/',
            data = { 'title': 'Should Fail' },
            format = 'json'
        )

        self.assertEqual( response.status_code, 403 )

    def test_non_member_returns_404( self ):
        """Test non-member gets 404 (not 403) for privacy."""
        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + self.non_member_token.api_token_str
        )
        response = self.client.patch(
            f'/api/v1/locations/{self.location.uuid}/',
            data = { 'title': 'Should Fail' },
            format = 'json'
        )

        self.assertEqual( response.status_code, 404 )

    def test_partial_update_preserves_other_fields( self ):
        """Test partial update only changes specified fields."""
        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + self.owner_token.api_token_str
        )
        response = self.client.patch(
            f'/api/v1/locations/{self.location.uuid}/',
            data = { 'title': 'New Title Only' },
            format = 'json'
        )

        self.assertEqual( response.status_code, 200 )
        data = response.json()['data']
        self.assertEqual( data['title'], 'New Title Only' )
        self.assertEqual( data['latitude'], 45.0 )
        self.assertEqual( data['longitude'], -122.0 )

    def test_can_update_coordinates( self ):
        """Test can update latitude and longitude."""
        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + self.owner_token.api_token_str
        )
        response = self.client.patch(
            f'/api/v1/locations/{self.location.uuid}/',
            data = {
                'latitude': '46.123456',
                'longitude': '-123.654321',
            },
            format = 'json'
        )

        self.assertEqual( response.status_code, 200 )
        data = response.json()['data']
        self.assertEqual( data['latitude'], 46.123456 )
        self.assertEqual( data['longitude'], -123.654321 )

    def test_can_update_subcategory( self ):
        """Test can update subcategory_slug."""
        self.location.subcategory = self.subcategory
        self.location.save()

        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + self.owner_token.api_token_str
        )
        response = self.client.patch(
            f'/api/v1/locations/{self.location.uuid}/',
            data = { 'subcategory_slug': 'park' },
            format = 'json'
        )

        self.assertEqual( response.status_code, 200 )
        data = response.json()['data']
        self.assertEqual( data['subcategory_slug'], 'park' )

    def test_can_clear_subcategory( self ):
        """Test can clear subcategory by setting to null."""
        self.location.subcategory = self.subcategory
        self.location.save()

        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + self.owner_token.api_token_str
        )
        response = self.client.patch(
            f'/api/v1/locations/{self.location.uuid}/',
            data = { 'subcategory_slug': None },
            format = 'json'
        )

        self.assertEqual( response.status_code, 200 )
        data = response.json()['data']
        self.assertIsNone( data['subcategory_slug'] )

    def test_can_update_gmm_id( self ):
        """Test can update gmm_id field."""
        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + self.owner_token.api_token_str
        )
        response = self.client.patch(
            f'/api/v1/locations/{self.location.uuid}/',
            data = { 'gmm_id': 'new_gmm_123' },
            format = 'json'
        )

        self.assertEqual( response.status_code, 200 )
        data = response.json()['data']
        self.assertEqual( data['gmm_id'], 'new_gmm_123' )

    def test_nonexistent_location_returns_404( self ):
        """Test returns 404 for nonexistent UUID."""
        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + self.owner_token.api_token_str
        )
        response = self.client.patch(
            '/api/v1/locations/00000000-0000-0000-0000-000000000000/',
            data = { 'title': 'Test' },
            format = 'json'
        )

        self.assertEqual( response.status_code, 404 )


# =============================================================================
# LocationItemView Tests - DELETE
# =============================================================================

class LocationItemViewDeleteTestCase( TestCase ):
    """Test DELETE /api/v1/locations/{uuid}/ endpoint."""

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
        self.location = Location.objects.create(
            trip = self.trip,
            title = 'Location To Delete',
        )

    def test_requires_authentication( self ):
        """Test endpoint requires authentication."""
        response = self.client.delete( f'/api/v1/locations/{self.location.uuid}/' )
        self.assertEqual( response.status_code, 401 )

    def test_owner_can_delete_location( self ):
        """Test owner can delete location."""
        location_uuid = self.location.uuid

        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + self.owner_token.api_token_str
        )
        response = self.client.delete( f'/api/v1/locations/{location_uuid}/' )

        self.assertEqual( response.status_code, 204 )

        # Verify deleted
        self.assertFalse( Location.objects.filter( uuid = location_uuid ).exists() )

    def test_editor_can_delete_location( self ):
        """Test editor can delete location."""
        location_uuid = self.location.uuid

        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + self.editor_token.api_token_str
        )
        response = self.client.delete( f'/api/v1/locations/{location_uuid}/' )

        self.assertEqual( response.status_code, 204 )

        # Verify deleted
        self.assertFalse( Location.objects.filter( uuid = location_uuid ).exists() )

    def test_viewer_cannot_delete_location( self ):
        """Test viewer cannot delete location."""
        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + self.viewer_token.api_token_str
        )
        response = self.client.delete( f'/api/v1/locations/{self.location.uuid}/' )

        self.assertEqual( response.status_code, 403 )

        # Verify not deleted
        self.assertTrue( Location.objects.filter( uuid = self.location.uuid ).exists() )

    def test_non_member_returns_404( self ):
        """Test non-member gets 404 (not 403) for privacy."""
        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + self.non_member_token.api_token_str
        )
        response = self.client.delete( f'/api/v1/locations/{self.location.uuid}/' )

        self.assertEqual( response.status_code, 404 )

        # Verify not deleted
        self.assertTrue( Location.objects.filter( uuid = self.location.uuid ).exists() )

    def test_nonexistent_location_returns_404( self ):
        """Test returns 404 for nonexistent UUID."""
        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + self.owner_token.api_token_str
        )
        response = self.client.delete(
            '/api/v1/locations/00000000-0000-0000-0000-000000000000/'
        )

        self.assertEqual( response.status_code, 404 )

    def test_delete_cascades_to_location_notes( self ):
        """Test deleting location also deletes associated notes."""
        LocationNote.objects.create(
            location = self.location,
            text = 'Test note',
        )
        location_uuid = self.location.uuid

        self.client.credentials(
            HTTP_AUTHORIZATION = 'Bearer ' + self.owner_token.api_token_str
        )
        response = self.client.delete( f'/api/v1/locations/{location_uuid}/' )

        self.assertEqual( response.status_code, 204 )

        # Verify notes also deleted
        self.assertEqual( LocationNote.objects.filter( location__uuid = location_uuid ).count(), 0 )
