import logging

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from tt.apps.members.models import TripMember
from tt.apps.trips.enums import TripPermissionLevel, TripPage, TripStatus
from tt.apps.trips.models import Trip
from tt.apps.trips.tests.synthetic_data import TripSyntheticData

logging.disable(logging.CRITICAL)

User = get_user_model()


class TripCreateModalViewTests(TestCase):
    """Tests for the trip creation modal view."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.trips_create_url = reverse('trips_create')

    def test_trips_create_requires_authentication(self):
        """Test that trip creation requires authentication."""
        response = self.client.get(self.trips_create_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/user/signin', response.url)

    def test_trips_create_modal_displays(self):
        """Test that trip creation modal displays for authenticated users."""
        self.client.force_login(self.user)
        response = self.client.get(self.trips_create_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create New Trip')

    def test_trips_create_success(self):
        """Test successful trip creation."""
        self.client.force_login(self.user)

        data = {
            'title': 'New Test Trip',
            'description': 'A test trip description',
        }

        response = self.client.post(self.trips_create_url, data)
        self.assertEqual(response.status_code, 200)

        # Verify trip was created
        trip = Trip.objects.owned_by(self.user).get()
        self.assertEqual(trip.title, 'New Test Trip')
        self.assertEqual(trip.description, 'A test trip description')
        self.assertEqual(trip.trip_status, TripStatus.UPCOMING)

    def test_trips_create_validation_error(self):
        """Test trip creation with validation errors."""
        self.client.force_login(self.user)

        # Missing required title field
        data = {
            'description': 'A test trip description',
        }

        response = self.client.post(self.trips_create_url, data)
        self.assertEqual(response.status_code, 400)

        # Verify no trip was created
        self.assertEqual(Trip.objects.count(), 0)


class TripHomeViewTests(TestCase):
    """Tests for the trip home view."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        cls.trip = TripSyntheticData.create_test_trip(
            user=cls.user,
            title='Test Trip',
            description='Test Description',
            trip_status=TripStatus.UPCOMING
        )

    def setUp(self):
        self.client = Client()
        self.trips_home_url = reverse('trips_home', kwargs={'trip_uuid': self.trip.uuid})

    def test_trips_home_requires_authentication(self):
        """Test that trip home requires authentication."""
        response = self.client.get(self.trips_home_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/user/signin', response.url)

    def test_trips_home_displays(self):
        """Test that trip home displays correctly."""
        self.client.force_login(self.user)
        response = self.client.get(self.trips_home_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Trip')

    def test_trips_home_sets_session(self):
        """Test that visiting trip home sets the trip in session."""
        self.client.force_login(self.user)
        response = self.client.get(self.trips_home_url)
        self.assertEqual(response.status_code, 200)

        # Verify trip_id is set in session
        session = self.client.session
        self.assertEqual(int(session.get('trip_id')), self.trip.pk)

    def test_trips_home_only_shows_user_trips(self):
        """Test that trip home only shows trips for the logged-in user."""
        # Create another user and their trip
        other_user = User.objects.create_user(
            email='other@example.com',
            password='testpass123'
        )
        other_trip = TripSyntheticData.create_test_trip(
            user=other_user,
            title='Other User Trip',
            trip_status=TripStatus.UPCOMING
        )

        self.client.force_login(self.user)
        other_trip_url = reverse('trips_home', kwargs = { 'trip_uuid': other_trip.uuid })
        response = self.client.get(other_trip_url)

        # Should return a 404 since user doesn't own the trip
        self.assertEqual(response.status_code, 404)

    def test_trips_home_includes_trip_page_context(self):
        """Test that trip home includes trip_page context with proper active_page."""
        self.client.force_login(self.user)
        response = self.client.get(self.trips_home_url)

        self.assertEqual(response.status_code, 200)
        self.assertIn('trip_page', response.context)
        trip_page = response.context['trip_page']
        self.assertEqual(trip_page.trip, self.trip)
        self.assertEqual(trip_page.active_page, TripPage.OVERVIEW)

    def test_non_member_gets_404_not_403(self):
        """Non-members get 404 (not 403) to avoid information disclosure."""
        other_user = User.objects.create_user(
            email='other@test.com',
            password='testpass123'
        )
        self.client.force_login(other_user)

        response = self.client.get(self.trips_home_url)

        # Should be 404, not 403, to avoid revealing trip existence
        self.assertEqual(response.status_code, 404)

    def test_admin_can_view_trip(self):
        """User with ADMIN permission can view trip."""

        admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123'
        )
        TripMember.objects.create(
            trip=self.trip,
            user=admin_user,
            permission_level=TripPermissionLevel.ADMIN,
            added_by=self.user
        )

        self.client.force_login(admin_user)
        response = self.client.get(self.trips_home_url)

        self.assertEqual(response.status_code, 200)

    def test_editor_can_view_trip(self):
        """User with EDITOR permission can view trip."""

        editor_user = User.objects.create_user(
            email='editor@test.com',
            password='testpass123'
        )
        TripMember.objects.create(
            trip=self.trip,
            user=editor_user,
            permission_level=TripPermissionLevel.EDITOR,
            added_by=self.user
        )

        self.client.force_login(editor_user)
        response = self.client.get(self.trips_home_url)

        self.assertEqual(response.status_code, 200)

    def test_viewer_can_view_trip(self):
        """User with VIEWER permission can view trip."""

        viewer_user = User.objects.create_user(
            email='viewer@test.com',
            password='testpass123'
        )
        TripMember.objects.create(
            trip=self.trip,
            user=viewer_user,
            permission_level=TripPermissionLevel.VIEWER,
            added_by=self.user
        )

        self.client.force_login(viewer_user)
        response = self.client.get(self.trips_home_url)

        self.assertEqual(response.status_code, 200)

    def test_trips_home_nonexistent_trip(self):
        """Test that requesting nonexistent trip returns 404."""
        self.client.force_login(self.user)
        url = reverse('trips_home', kwargs={'trip_uuid': '32653d87-9b24-4c8f-adfb-8ab876418072'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


class TripsAllViewTests(TestCase):
    """Tests for the trips_all view that shows all trips with categorization."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.trips_all_url = reverse('trips_all')

    def test_trips_all_requires_authentication(self):
        """Test that trips_all redirects unauthenticated users."""
        response = self.client.get(self.trips_all_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/user/signin', response.url)

    def test_trips_all_displays_for_authenticated_user(self):
        """Test that trips_all displays for authenticated users."""
        self.client.force_login(self.user)
        response = self.client.get(self.trips_all_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'trips/pages/trips_all.html')

    def test_trips_all_shows_upcoming_trips(self):
        """Test that trips_all displays upcoming trips."""
        self.client.force_login(self.user)

        TripSyntheticData.create_test_trip(
            user=self.user,
            title='Test Trip',
            description='Test Description',
            trip_status=TripStatus.UPCOMING
        )

        response = self.client.get(self.trips_all_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Trip')
        self.assertEqual(len(response.context['owned_upcoming_trips']), 1)
        self.assertEqual(response.context['total_trips'], 1)

    def test_trips_all_shows_past_trips(self):
        """Test that trips_all displays past trips separately."""
        self.client.force_login(self.user)

        TripSyntheticData.create_test_trip(
            user=self.user,
            title='Upcoming Trip',
            trip_status=TripStatus.UPCOMING
        )
        TripSyntheticData.create_test_trip(
            user=self.user,
            title='Past Trip',
            trip_status=TripStatus.PAST
        )

        response = self.client.get(self.trips_all_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['owned_upcoming_trips']), 1)
        self.assertEqual(len(response.context['owned_past_trips']), 1)
        self.assertEqual(response.context['total_trips'], 2)

    def test_trips_all_only_shows_user_trips(self):
        """Test that trips_all only shows trips for the logged-in user."""
        other_user = User.objects.create_user(
            email='other@example.com',
            password='testpass123'
        )
        TripSyntheticData.create_test_trip(
            user=other_user,
            title='Other User Trip',
            trip_status=TripStatus.UPCOMING
        )

        TripSyntheticData.create_test_trip(
            user=self.user,
            title='My Trip',
            trip_status=TripStatus.UPCOMING
        )

        self.client.force_login(self.user)
        response = self.client.get(self.trips_all_url)

        self.assertEqual(response.context['total_trips'], 1)
        self.assertContains(response, 'My Trip')
        self.assertNotContains(response, 'Other User Trip')

    def test_trips_all_categorizes_trips_by_ownership_and_status(self):
        """Test that trips_all correctly categorizes trips by ownership and status."""
        self.client.force_login(self.user)

        other_user = User.objects.create_user(
            email='other@example.com',
            password='testpass123'
        )

        # Create owned upcoming trip
        TripSyntheticData.create_test_trip(
            user=self.user,
            title='Owned Upcoming Trip',
            trip_status=TripStatus.UPCOMING
        )

        # Create owned current trip (should be in owned_upcoming_trips)
        TripSyntheticData.create_test_trip(
            user=self.user,
            title='Owned Current Trip',
            trip_status=TripStatus.CURRENT
        )

        # Create owned past trip
        TripSyntheticData.create_test_trip(
            user=self.user,
            title='Owned Past Trip',
            trip_status=TripStatus.PAST
        )

        # Create shared upcoming trip (user is member but not owner)
        shared_upcoming = TripSyntheticData.create_test_trip(
            user=other_user,
            title='Shared Upcoming Trip',
            trip_status=TripStatus.UPCOMING
        )
        TripSyntheticData.add_trip_member(
            trip=shared_upcoming,
            user=self.user,
            permission_level=TripPermissionLevel.EDITOR,
            added_by=other_user
        )

        # Create shared current trip (should be in shared_trips)
        shared_current = TripSyntheticData.create_test_trip(
            user=other_user,
            title='Shared Current Trip',
            trip_status=TripStatus.CURRENT
        )
        TripSyntheticData.add_trip_member(
            trip=shared_current,
            user=self.user,
            permission_level=TripPermissionLevel.VIEWER,
            added_by=other_user
        )

        # Create shared past trip (not shown in any category per requirements)
        shared_past = TripSyntheticData.create_test_trip(
            user=other_user,
            title='Shared Past Trip',
            trip_status=TripStatus.PAST
        )
        TripSyntheticData.add_trip_member(
            trip=shared_past,
            user=self.user,
            permission_level=TripPermissionLevel.EDITOR,
            added_by=other_user
        )

        response = self.client.get(self.trips_all_url)
        self.assertEqual(response.status_code, 200)

        # Verify owned_upcoming_trips includes UPCOMING and CURRENT owned trips
        owned_upcoming_trips = response.context['owned_upcoming_trips']
        self.assertEqual(len(owned_upcoming_trips), 2)
        owned_upcoming_titles = {trip.title for trip in owned_upcoming_trips}
        self.assertEqual(owned_upcoming_titles, {'Owned Upcoming Trip', 'Owned Current Trip'})

        # Verify shared_trips includes UPCOMING and CURRENT shared trips
        shared_trips = response.context['shared_trips']
        self.assertEqual(len(shared_trips), 2)
        shared_titles = {trip.title for trip in shared_trips}
        self.assertEqual(shared_titles, {'Shared Upcoming Trip', 'Shared Current Trip'})

        # Verify owned_past_trips includes only PAST owned trips
        owned_past_trips = response.context['owned_past_trips']
        self.assertEqual(len(owned_past_trips), 1)
        self.assertEqual(owned_past_trips[0].title, 'Owned Past Trip')

        # Verify total_trips count includes all trips (owned + shared)
        self.assertEqual(response.context['total_trips'], 6)
