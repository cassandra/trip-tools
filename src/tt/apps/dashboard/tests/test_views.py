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

    def test_dashboard_home_shows_editable_trips(self):
        """Test that dashboard_home displays editable upcoming/current trips."""
        self.client.force_login(self.user)

        # Create an upcoming trip (user is owner, so editable)
        TripSyntheticData.create_test_trip(
            user=self.user,
            title='Test Trip',
            description='Test Description',
            trip_status=TripStatus.UPCOMING
        )

        response = self.client.get(self.dashboard_home_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Trip')
        self.assertEqual(len(response.context['dashboard_trips']), 1)

    def test_dashboard_home_excludes_editable_past_trips(self):
        """Test that dashboard_home excludes editable past trips."""
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
        # Only upcoming/current editable trips appear
        self.assertEqual(len(response.context['dashboard_trips']), 1)
        self.assertEqual(response.context['dashboard_trips'][0].title, 'Upcoming Trip')

    def test_dashboard_home_limits_trips_to_five(self):
        """Test that dashboard_home limits trips display to 5."""
        self.client.force_login(self.user)

        # Create 7 upcoming trips
        for i in range(7):
            TripSyntheticData.create_test_trip(
                user=self.user,
                title=f'Trip {i}',
                trip_status=TripStatus.UPCOMING
            )

        response = self.client.get(self.dashboard_home_url)
        self.assertEqual(response.status_code, 200)
        # Should be limited to 5 trips
        self.assertEqual(len(response.context['dashboard_trips']), 5)

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

        self.assertEqual(len(response.context['dashboard_trips']), 1)
        self.assertContains(response, 'My Trip')
        self.assertNotContains(response, 'Other User Trip')

    def test_dashboard_home_prioritizes_current_over_upcoming(self):
        """Test that CURRENT trips appear before UPCOMING trips."""
        self.client.force_login(self.user)

        # Create trips in reverse order to ensure ordering is by status, not creation
        TripSyntheticData.create_test_trip(
            user=self.user,
            title='Upcoming Trip',
            trip_status=TripStatus.UPCOMING
        )
        TripSyntheticData.create_test_trip(
            user=self.user,
            title='Current Trip',
            trip_status=TripStatus.CURRENT
        )

        response = self.client.get(self.dashboard_home_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['dashboard_trips']), 2)
        # Current should appear first
        self.assertEqual(response.context['dashboard_trips'][0].title, 'Current Trip')
        self.assertEqual(response.context['dashboard_trips'][1].title, 'Upcoming Trip')

    def test_dashboard_home_includes_shared_trips_when_under_limit(self):
        """Test that shared (view-only) trips fill remaining slots."""
        self.client.force_login(self.user)

        # Create another user who owns trips
        other_user = User.objects.create_user(
            email='other@example.com',
            password='testpass123'
        )

        # Create 2 editable trips for test user
        TripSyntheticData.create_test_trip(
            user=self.user,
            title='My Trip 1',
            trip_status=TripStatus.UPCOMING
        )
        TripSyntheticData.create_test_trip(
            user=self.user,
            title='My Trip 2',
            trip_status=TripStatus.CURRENT
        )

        # Create a shared trip (owned by other_user, shared with test user as VIEWER)
        shared_trip = TripSyntheticData.create_test_trip(
            user=other_user,
            title='Shared Trip',
            trip_status=TripStatus.UPCOMING
        )
        TripSyntheticData.add_trip_member(
            trip=shared_trip,
            user=self.user,
            permission_level=TripPermissionLevel.VIEWER,
            added_by=other_user,
        )

        response = self.client.get(self.dashboard_home_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['dashboard_trips']), 3)
        # Editable trips first (Current before Upcoming), then shared
        self.assertEqual(response.context['dashboard_trips'][0].title, 'My Trip 2')
        self.assertEqual(response.context['dashboard_trips'][1].title, 'My Trip 1')
        self.assertEqual(response.context['dashboard_trips'][2].title, 'Shared Trip')

    def test_dashboard_home_includes_shared_past_trips(self):
        """Test that shared PAST trips can appear (when there's room)."""
        self.client.force_login(self.user)

        other_user = User.objects.create_user(
            email='other@example.com',
            password='testpass123'
        )

        # Create a shared past trip
        shared_past_trip = TripSyntheticData.create_test_trip(
            user=other_user,
            title='Shared Past Trip',
            trip_status=TripStatus.PAST
        )
        TripSyntheticData.add_trip_member(
            trip=shared_past_trip,
            user=self.user,
            permission_level=TripPermissionLevel.VIEWER,
            added_by=other_user,
        )

        response = self.client.get(self.dashboard_home_url)
        self.assertEqual(response.status_code, 200)
        # Shared past trip should appear since there's room
        self.assertEqual(len(response.context['dashboard_trips']), 1)
        self.assertEqual(response.context['dashboard_trips'][0].title, 'Shared Past Trip')

    def test_dashboard_home_prioritizes_editable_over_shared(self):
        """Test that editable trips always appear before shared trips."""
        self.client.force_login(self.user)

        other_user = User.objects.create_user(
            email='other@example.com',
            password='testpass123'
        )

        # Create 5 editable trips
        for i in range(5):
            TripSyntheticData.create_test_trip(
                user=self.user,
                title=f'My Trip {i}',
                trip_status=TripStatus.UPCOMING
            )

        # Create a shared trip
        shared_trip = TripSyntheticData.create_test_trip(
            user=other_user,
            title='Shared Trip',
            trip_status=TripStatus.UPCOMING
        )
        TripSyntheticData.add_trip_member(
            trip=shared_trip,
            user=self.user,
            permission_level=TripPermissionLevel.VIEWER,
            added_by=other_user,
        )

        response = self.client.get(self.dashboard_home_url)
        self.assertEqual(response.status_code, 200)
        # Should show 5 editable trips, no room for shared
        self.assertEqual(len(response.context['dashboard_trips']), 5)
        trip_titles = [t.title for t in response.context['dashboard_trips']]
        self.assertNotIn('Shared Trip', trip_titles)
