from django.contrib.auth import get_user_model
from django.test import TestCase

from tt.apps.trips.models import TripMember
from tt.apps.trips.tests.synthetic_data import TripSyntheticData

User = get_user_model()


class TripMemberModelTests(TestCase):
    """Tests for TripMember model constraints and behavior."""

    def test_cascade_delete_trip_removes_members(self):
        """Deleting trip deletes all TripMembers."""
        user = User.objects.create_user(email='test@test.com', password='pass')
        trip = TripSyntheticData.create_test_trip(user=user, title='Test Trip')

        trip_id = trip.pk
        self.assertEqual(TripMember.objects.filter(trip_id=trip_id).count(), 1)

        trip.delete()

        self.assertEqual(TripMember.objects.filter(trip_id=trip_id).count(), 0)

    def test_cascade_delete_user_removes_memberships(self):
        """Deleting user deletes all TripMembers for that user."""
        user = User.objects.create_user(email='test@test.com', password='pass')
        TripSyntheticData.create_test_trip(user=user, title='Test Trip')

        user_id = user.pk
        self.assertEqual(TripMember.objects.filter(user_id=user_id).count(), 1)

        user.delete()

        self.assertEqual(TripMember.objects.filter(user_id=user_id).count(), 0)
