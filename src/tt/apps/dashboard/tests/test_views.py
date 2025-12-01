from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from tt.apps.trips.enums import TripStatus
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

    def test_dashboard_home_shows_recent_trips(self):
        """Test that dashboard_home displays recent upcoming/current trips."""
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
        self.assertEqual(len(response.context['recent_trips']), 1)

    def test_dashboard_home_excludes_past_trips_from_recent(self):
        """Test that dashboard_home excludes past trips from recent trips."""
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
        # Only upcoming/current trips appear in recent_trips
        self.assertEqual(len(response.context['recent_trips']), 1)
        self.assertEqual(response.context['recent_trips'][0].title, 'Upcoming Trip')

    def test_dashboard_home_limits_recent_trips_to_three(self):
        """Test that dashboard_home limits recent trips display to 3."""
        self.client.force_login(self.user)

        # Create 5 upcoming trips
        for i in range(5):
            TripSyntheticData.create_test_trip(
                user=self.user,
                title=f'Trip {i}',
                trip_status=TripStatus.UPCOMING
            )

        response = self.client.get(self.dashboard_home_url)
        self.assertEqual(response.status_code, 200)
        # Should be limited to 3 recent trips
        self.assertEqual(len(response.context['recent_trips']), 3)

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

        self.assertEqual(len(response.context['recent_trips']), 1)
        self.assertContains(response, 'My Trip')
        self.assertNotContains(response, 'Other User Trip')
