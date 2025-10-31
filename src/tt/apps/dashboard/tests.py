from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from tt.apps.trips.models import Trip
from tt.apps.trips.enums import TripStatus


User = get_user_model()


class DashboardViewTests(TestCase):
    """Tests for the dashboard view."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.dashboard_url = reverse('dashboard')

    def test_dashboard_requires_authentication(self):
        """Test that dashboard redirects unauthenticated users."""
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/user/signin', response.url)

    def test_dashboard_displays_for_authenticated_user(self):
        """Test that dashboard displays for authenticated users."""
        self.client.force_login(self.user)
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/pages/dashboard.html')

    def test_dashboard_shows_upcoming_trips(self):
        """Test that dashboard displays upcoming trips."""
        self.client.force_login(self.user)

        # Create an upcoming trip
        Trip.objects.create(
            user=self.user,
            title='Test Trip',
            description='Test Description',
            trip_status=TripStatus.UPCOMING
        )

        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Trip')
        self.assertEqual(len(response.context['upcoming_trips']), 1)
        self.assertEqual(response.context['total_trips'], 1)

    def test_dashboard_shows_past_trips(self):
        """Test that dashboard displays past trips separately."""
        self.client.force_login(self.user)

        # Create trips with different statuses
        Trip.objects.create(
            user=self.user,
            title='Upcoming Trip',
            trip_status=TripStatus.UPCOMING
        )
        Trip.objects.create(
            user=self.user,
            title='Past Trip',
            trip_status=TripStatus.PAST
        )

        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['upcoming_trips']), 1)
        self.assertEqual(len(response.context['past_trips']), 1)
        self.assertEqual(response.context['total_trips'], 2)

    def test_dashboard_only_shows_user_trips(self):
        """Test that dashboard only shows trips for the logged-in user."""
        # Create another user and their trip
        other_user = User.objects.create_user(
            email='other@example.com',
            password='testpass123'
        )
        Trip.objects.create(
            user=other_user,
            title='Other User Trip',
            trip_status=TripStatus.UPCOMING
        )

        # Create trip for test user
        Trip.objects.create(
            user=self.user,
            title='My Trip',
            trip_status=TripStatus.UPCOMING
        )

        self.client.force_login(self.user)
        response = self.client.get(self.dashboard_url)

        self.assertEqual(response.context['total_trips'], 1)
        self.assertContains(response, 'My Trip')
        self.assertNotContains(response, 'Other User Trip')
