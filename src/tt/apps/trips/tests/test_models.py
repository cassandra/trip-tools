from django.contrib.auth import get_user_model
from django.test import TestCase

from tt.apps.trips.enums import TripPermissionLevel
from tt.apps.trips.models import TripMember
from tt.apps.trips.tests.synthetic_data import TripSyntheticData

User = get_user_model()


class TripOwnerPropertyTests(TestCase):
    """Tests for Trip.owner property."""

    def test_owner_property_returns_owner_user(self):
        """Trip.owner returns user with OWNER permission."""
        user = User.objects.create_user(email='owner@test.com', password='pass')
        trip = TripSyntheticData.create_test_trip(user=user, title='Test Trip')

        self.assertEqual(trip.owner, user)

    def test_owner_property_returns_first_owner_when_multiple(self):
        """Trip.owner returns first owner when multiple owners exist."""
        user1 = User.objects.create_user(email='owner1@test.com', password='pass')
        user2 = User.objects.create_user(email='owner2@test.com', password='pass')

        trip = TripSyntheticData.create_test_trip(user=user1, title='Test Trip')

        # Add second owner
        TripMember.objects.create(
            trip=trip,
            user=user2,
            permission_level=TripPermissionLevel.OWNER,
            added_by=user1
        )

        # Should return one of the owners (implementation returns first found)
        owner = trip.owner
        self.assertIn(owner, [user1, user2])

    def test_owner_property_caches_result(self):
        """Trip.owner caches result to prevent N+1 queries."""
        user = User.objects.create_user(email='owner@test.com', password='pass')
        trip = TripSyntheticData.create_test_trip(user=user, title='Test Trip')

        # First access - queries database
        owner1 = trip.owner
        self.assertEqual(owner1, user)

        # Second access - should use cache (no additional query)
        owner2 = trip.owner
        self.assertEqual(owner2, user)
        self.assertIs(owner1, owner2)  # Same object instance


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

    def test_trip_with_no_owner_returns_none(self):
        """Trip.owner returns None if no OWNER exists (edge case)."""
        # Create trip with owner
        user = User.objects.create_user(email='owner@test.com', password='pass')
        trip = TripSyntheticData.create_test_trip(user=user, title='Test Trip')

        # Manually remove owner (shouldn't happen in practice, but test edge case)
        TripMember.objects.filter(trip=trip, permission_level=TripPermissionLevel.OWNER).delete()

        self.assertIsNone(trip.owner)
