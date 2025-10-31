from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from .models import Trip
from .enums import TripStatus


User = get_user_model()


class TripCreateModalViewTests(TestCase):
    """Tests for the trip creation modal view."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.trip_create_url = reverse('trip_create')

    def test_trip_create_requires_authentication(self):
        """Test that trip creation requires authentication."""
        response = self.client.get(self.trip_create_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/user/signin', response.url)

    def test_trip_create_modal_displays(self):
        """Test that trip creation modal displays for authenticated users."""
        self.client.force_login(self.user)
        response = self.client.get(self.trip_create_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create New Trip')

    def test_trip_create_success(self):
        """Test successful trip creation."""
        self.client.force_login(self.user)

        data = {
            'title': 'New Test Trip',
            'description': 'A test trip description',
        }

        response = self.client.post(self.trip_create_url, data)
        self.assertEqual(response.status_code, 200)

        # Verify trip was created
        trip = Trip.objects.get(user=self.user)
        self.assertEqual(trip.title, 'New Test Trip')
        self.assertEqual(trip.description, 'A test trip description')
        self.assertEqual(trip.trip_status, TripStatus.UPCOMING)

    def test_trip_create_validation_error(self):
        """Test trip creation with validation errors."""
        self.client.force_login(self.user)

        # Missing required title field
        data = {
            'description': 'A test trip description',
        }

        response = self.client.post(self.trip_create_url, data)
        self.assertEqual(response.status_code, 400)

        # Verify no trip was created
        self.assertEqual(Trip.objects.count(), 0)


class TripHomeViewTests(TestCase):
    """Tests for the trip home view."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.trip = Trip.objects.create(
            user=self.user,
            title='Test Trip',
            description='Test Description',
            trip_status=TripStatus.UPCOMING
        )
        self.trip_home_url = reverse('trip_home', kwargs={'trip_id': self.trip.pk})

    def test_trip_home_requires_authentication(self):
        """Test that trip home requires authentication."""
        response = self.client.get(self.trip_home_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/user/signin', response.url)

    def test_trip_home_displays(self):
        """Test that trip home displays correctly."""
        self.client.force_login(self.user)
        response = self.client.get(self.trip_home_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Trip')
        self.assertContains(response, 'Test Description')

    def test_trip_home_sets_session(self):
        """Test that visiting trip home sets the trip in session."""
        self.client.force_login(self.user)
        response = self.client.get(self.trip_home_url)
        self.assertEqual(response.status_code, 200)

        # Verify trip_id is set in session
        session = self.client.session
        self.assertEqual(int(session.get('trip_id')), self.trip.pk)

    def test_trip_home_only_shows_user_trips(self):
        """Test that trip home only shows trips for the logged-in user."""
        # Create another user and their trip
        other_user = User.objects.create_user(
            email='other@example.com',
            password='testpass123'
        )
        other_trip = Trip.objects.create(
            user=other_user,
            title='Other User Trip',
            trip_status=TripStatus.UPCOMING
        )

        self.client.force_login(self.user)
        other_trip_url = reverse('trip_home', kwargs={'trip_id': other_trip.pk})
        response = self.client.get(other_trip_url)

        # Should return a 404 since user doesn't own the trip
        self.assertEqual(response.status_code, 404)
