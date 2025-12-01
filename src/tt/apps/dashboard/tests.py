from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from tt.apps.trips.enums import TripPermissionLevel, TripStatus
from tt.apps.trips.tests.synthetic_data import TripSyntheticData


User = get_user_model()


class DashboardViewTests(TestCase):
    """Tests for the dashboard view."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.dashboard_home_url = reverse('dashboard_home')

    def test_dashboard_home_requires_authentication(self):
        """Test that dashboard_home redirects unauthenticated users."""
        response = self.client.get(self.dashboard_home_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/user/signin', response.url)

    def test_dashboard_home_displays_for_authenticated_user(self):
        """Test that dashboard_home displays for authenticated users."""
        self.client.force_login(self.user)
        response = self.client.get(self.dashboard_home_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/pages/dashboard_home.html')

    def test_dashboard_home_shows_upcoming_trips(self):
        """Test that dashboard_home displays upcoming trips."""
        self.client.force_login(self.user)

        # Create an upcoming trip
        TripSyntheticData.create_test_trip(
            user=self.user,
            title='Test Trip',
            description='Test Description',
            trip_status=TripStatus.UPCOMING
        )

        response = self.client.get(self.dashboard_home_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Trip')
        self.assertEqual(len(response.context['owned_upcoming_trips']), 1)
        self.assertEqual(response.context['total_trips'], 1)

    def test_dashboard_home_shows_past_trips(self):
        """Test that dashboard_home displays past trips separately."""
        self.client.force_login(self.user)

        # Create trips with different statuses
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

        response = self.client.get(self.dashboard_home_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['owned_upcoming_trips']), 1)
        self.assertEqual(len(response.context['owned_past_trips']), 1)
        self.assertEqual(response.context['total_trips'], 2)

    def test_dashboard_home_only_shows_user_trips(self):
        """Test that dashboard_home only shows trips for the logged-in user."""
        # Create another user and their trip
        other_user = User.objects.create_user(
            email='other@example.com',
            password='testpass123'
        )
        TripSyntheticData.create_test_trip(
            user=other_user,
            title='Other User Trip',
            trip_status=TripStatus.UPCOMING
        )

        # Create trip for test user
        TripSyntheticData.create_test_trip(
            user=self.user,
            title='My Trip',
            trip_status=TripStatus.UPCOMING
        )

        self.client.force_login(self.user)
        response = self.client.get(self.dashboard_home_url)

        self.assertEqual(response.context['total_trips'], 1)
        self.assertContains(response, 'My Trip')
        self.assertNotContains(response, 'Other User Trip')

    def test_dashboard_categorizes_trips_by_ownership_and_status(self):
        """Test that dashboard correctly categorizes trips by ownership and status."""
        self.client.force_login(self.user)

        # Create another user
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

        response = self.client.get(self.dashboard_home_url)
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
