from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from tt.apps.trips.enums import TripPage, TripStatus
from tt.apps.trips.models import Trip

User = get_user_model()


class ItineraryHomeViewTests(TestCase):
    """Tests for the itinerary home view."""

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
        self.itinerary_home_url = reverse('itineraries_home', kwargs={'trip_pk': self.trip.pk})

    def test_itinerary_home_requires_authentication(self):
        """Test that itinerary home redirects unauthenticated users."""
        response = self.client.get(self.itinerary_home_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/user/signin', response.url)

    def test_itinerary_home_displays(self):
        """Test that itinerary home displays correctly."""
        self.client.force_login(self.user)
        response = self.client.get(self.itinerary_home_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'itineraries/pages/itinerary-home.html')
        self.assertIn('sidebar', response.context)
        self.assertEqual(response.context['sidebar'].trip, self.trip)
        self.assertContains(response, 'Test Trip')

    def test_itinerary_home_only_shows_user_trips(self):
        """Test that itinerary home only shows trips for the logged-in user."""
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
        other_trip_url = reverse('itineraries_home', kwargs={'trip_pk': other_trip.pk})
        response = self.client.get(other_trip_url)

        self.assertEqual(response.status_code, 404)

    def test_itinerary_home_url_pattern(self):
        """Test that URL pattern resolves correctly."""
        url = reverse('itineraries_home', kwargs={'trip_pk': self.trip.pk})
        self.assertEqual(url, f'/itineraries/trip/{self.trip.pk}/itinerary/')

    def test_itinerary_home_nonexistent_trip(self):
        """Test that requesting nonexistent trip returns 404."""
        self.client.force_login(self.user)
        url = reverse('itineraries_home', kwargs={'trip_pk': 99999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_itinerary_home_uses_trip_base_template(self):
        """Test that itinerary template extends trip_base.html."""
        self.client.force_login(self.user)
        response = self.client.get(self.itinerary_home_url)

        template_names = [t.name for t in response.templates]
        self.assertIn('trips/pages/trip_base.html', template_names)
        self.assertIn('pages/base.html', template_names)

    def test_itinerary_home_includes_sidebar_context(self):
        """Test that itinerary home includes sidebar context with proper active_page."""
        self.client.force_login(self.user)
        response = self.client.get(self.itinerary_home_url)

        self.assertEqual(response.status_code, 200)
        self.assertIn('sidebar', response.context)
        sidebar = response.context['sidebar']
        self.assertEqual(sidebar.trip, self.trip)
        self.assertEqual(sidebar.active_page, TripPage.ITINERARY)
