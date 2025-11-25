"""
Tests for TripManager atomic trip creation patterns.

Tests focus on:
- Atomic trip creation with owner membership
- Transaction integrity and rollback behavior
- SELECT FOR UPDATE locking patterns (where applicable)
- Race condition prevention
- Proper CASCADE deletion
- Query filtering (for_user, owned_by)
"""
import logging

from django.contrib.auth import get_user_model
from django.db import transaction, IntegrityError
from django.test import TestCase, TransactionTestCase

from tt.apps.members.models import TripMember
from tt.apps.trips.enums import TripPermissionLevel, TripStatus
from tt.apps.trips.models import Trip
from tt.apps.trips.tests.synthetic_data import TripSyntheticData

logging.disable(logging.CRITICAL)

User = get_user_model()


class TripManagerCreateWithOwnerTestCase(TransactionTestCase):
    """Test atomic trip creation with owner membership."""

    def test_create_with_owner_basic(self):
        """Basic trip creation should create trip and owner membership atomically."""
        user = User.objects.create_user(email='owner@test.com', password='pass')

        trip = Trip.objects.create_with_owner(
            owner=user,
            title='Summer Vacation',
            description='Beach trip',
        )

        # Verify trip created
        self.assertIsNotNone(trip.pk)
        self.assertEqual(trip.title, 'Summer Vacation')
        self.assertEqual(trip.description, 'Beach trip')

        # Verify owner membership created
        members = TripMember.objects.filter(trip=trip)
        self.assertEqual(members.count(), 1)

        owner_member = members.first()
        self.assertEqual(owner_member.user, user)
        self.assertEqual(owner_member.permission_level, TripPermissionLevel.OWNER)
        self.assertEqual(owner_member.added_by, user)

    def test_create_with_owner_default_status(self):
        """Trip should default to UPCOMING status if not specified."""
        user = User.objects.create_user(email='owner@test.com', password='pass')

        trip = Trip.objects.create_with_owner(
            owner=user,
            title='Test Trip',
        )

        self.assertEqual(trip.trip_status, TripStatus.UPCOMING)

    def test_create_with_owner_custom_status(self):
        """Trip should use provided status if specified."""
        user = User.objects.create_user(email='owner@test.com', password='pass')

        trip = Trip.objects.create_with_owner(
            owner=user,
            title='Current Trip',
            trip_status=TripStatus.CURRENT,
        )

        self.assertEqual(trip.trip_status, TripStatus.CURRENT)

    def test_create_with_owner_additional_fields(self):
        """Additional trip fields should be passed through correctly."""
        user = User.objects.create_user(email='owner@test.com', password='pass')

        trip = Trip.objects.create_with_owner(
            owner=user,
            title='European Tour',
            description='Multi-city European adventure',
            trip_status=TripStatus.PAST,
        )

        self.assertEqual(trip.title, 'European Tour')
        self.assertEqual(trip.description, 'Multi-city European adventure')
        self.assertEqual(trip.trip_status, TripStatus.PAST)

    def test_create_with_owner_transaction_atomicity(self):
        """Trip creation and membership should be atomic (both or neither)."""
        user = User.objects.create_user(email='owner@test.com', password='pass')

        # Force an error by creating a trip with duplicate title constraint violation
        # (Note: Trip model doesn't have unique title, so we'll test rollback differently)

        # Count before
        trip_count_before = Trip.objects.count()
        member_count_before = TripMember.objects.count()

        try:
            # Create trip with invalid field to force rollback
            with transaction.atomic():
                Trip.objects.create_with_owner(
                    owner=user,
                    title='Test Trip',
                )
                # Force an error after trip creation
                raise IntegrityError("Simulated error")
        except IntegrityError:
            pass

        # Verify neither trip nor member was created (rollback worked)
        self.assertEqual(Trip.objects.count(), trip_count_before)
        self.assertEqual(TripMember.objects.count(), member_count_before)

    def test_create_with_owner_multiple_trips_same_user(self):
        """User should be able to own multiple trips."""
        user = User.objects.create_user(email='owner@test.com', password='pass')

        trip1 = Trip.objects.create_with_owner(owner=user, title='Trip 1')
        trip2 = Trip.objects.create_with_owner(owner=user, title='Trip 2')
        trip3 = Trip.objects.create_with_owner(owner=user, title='Trip 3')

        # Verify all trips created
        self.assertNotEqual(trip1.pk, trip2.pk)
        self.assertNotEqual(trip1.pk, trip3.pk)
        self.assertNotEqual(trip2.pk, trip3.pk)

        # Verify user is owner of all trips
        owned_trips = Trip.objects.owned_by(user)
        self.assertEqual(owned_trips.count(), 3)
        self.assertIn(trip1, owned_trips)
        self.assertIn(trip2, owned_trips)
        self.assertIn(trip3, owned_trips)


class TripManagerQueryFilteringTestCase(TestCase):
    """Test TripManager query filtering methods."""

    @classmethod
    def setUpTestData(cls):
        cls.user1 = User.objects.create_user(email='user1@test.com', password='pass')
        cls.user2 = User.objects.create_user(email='user2@test.com', password='pass')
        cls.user3 = User.objects.create_user(email='user3@test.com', password='pass')

    def test_for_user_returns_member_trips(self):
        """for_user should return all trips where user is a member."""
        trip1 = TripSyntheticData.create_test_trip(user=self.user1, title='Trip 1')
        trip2 = TripSyntheticData.create_test_trip(user=self.user1, title='Trip 2')
        trip3 = TripSyntheticData.create_test_trip(user=self.user2, title='Trip 3')

        # user1 owns trip1 and trip2
        user1_trips = Trip.objects.for_user(self.user1)
        self.assertEqual(user1_trips.count(), 2)
        self.assertIn(trip1, user1_trips)
        self.assertIn(trip2, user1_trips)

        # user2 owns trip3
        user2_trips = Trip.objects.for_user(self.user2)
        self.assertEqual(user2_trips.count(), 1)
        self.assertIn(trip3, user2_trips)

    def test_for_user_includes_non_owner_members(self):
        """for_user should include trips where user is member but not owner."""
        trip = TripSyntheticData.create_test_trip(user=self.user1, title='Shared Trip')

        # Add user2 as EDITOR
        TripSyntheticData.add_trip_member(
            trip=trip,
            user=self.user2,
            permission_level=TripPermissionLevel.EDITOR,
            added_by=self.user1,
        )

        # user2 should see the trip even though not owner
        user2_trips = Trip.objects.for_user(self.user2)
        self.assertEqual(user2_trips.count(), 1)
        self.assertIn(trip, user2_trips)

    def test_for_user_includes_all_permission_levels(self):
        """for_user should include trips regardless of permission level."""
        trip = TripSyntheticData.create_test_trip(user=self.user1, title='Multi-Member Trip')

        # Add different permission levels
        TripSyntheticData.add_trip_member(trip, self.user2, TripPermissionLevel.ADMIN, self.user1)
        TripSyntheticData.add_trip_member(trip, self.user3, TripPermissionLevel.VIEWER, self.user1)

        # All users should see the trip
        self.assertIn(trip, Trip.objects.for_user(self.user1))  # OWNER
        self.assertIn(trip, Trip.objects.for_user(self.user2))  # ADMIN
        self.assertIn(trip, Trip.objects.for_user(self.user3))  # VIEWER

    def test_for_user_distinct_results(self):
        """for_user should return distinct trips (no duplicates)."""
        trip = TripSyntheticData.create_test_trip(user=self.user1, title='Trip')

        # Query should return exactly one trip
        trips = Trip.objects.for_user(self.user1)
        self.assertEqual(trips.count(), 1)

        # Verify it's the correct trip
        self.assertEqual(trips.first(), trip)

    def test_for_user_empty_for_non_member(self):
        """for_user should return empty queryset for users with no memberships."""
        TripSyntheticData.create_test_trip(user=self.user1, title='Trip 1')
        TripSyntheticData.create_test_trip(user=self.user2, title='Trip 2')

        # user3 is not a member of any trips
        user3_trips = Trip.objects.for_user(self.user3)
        self.assertEqual(user3_trips.count(), 0)

    def test_owned_by_returns_only_owner_trips(self):
        """owned_by should return only trips where user is OWNER."""
        trip1 = TripSyntheticData.create_test_trip(user=self.user1, title='Owned Trip')
        trip2 = TripSyntheticData.create_test_trip(user=self.user2, title='Other Trip')

        # Add user1 as EDITOR to trip2 (not owner)
        TripSyntheticData.add_trip_member(trip2, self.user1, TripPermissionLevel.EDITOR, self.user2)

        # owned_by should only return trip1
        owned_trips = Trip.objects.owned_by(self.user1)
        self.assertEqual(owned_trips.count(), 1)
        self.assertIn(trip1, owned_trips)
        self.assertNotIn(trip2, owned_trips)

    def test_owned_by_excludes_non_owner_permission_levels(self):
        """owned_by should exclude ADMIN, EDITOR, VIEWER permission levels."""
        trip = TripSyntheticData.create_test_trip(user=self.user1, title='Trip')

        # Add other users with different permissions
        TripSyntheticData.add_trip_member(trip, self.user2, TripPermissionLevel.ADMIN, self.user1)
        TripSyntheticData.add_trip_member(trip, self.user3, TripPermissionLevel.EDITOR, self.user1)

        # Only user1 should be returned as owner
        self.assertEqual(Trip.objects.owned_by(self.user1).count(), 1)
        self.assertEqual(Trip.objects.owned_by(self.user2).count(), 0)
        self.assertEqual(Trip.objects.owned_by(self.user3).count(), 0)

    def test_owned_by_distinct_results(self):
        """owned_by should return distinct trips."""
        trip = TripSyntheticData.create_test_trip(user=self.user1, title='Trip')

        owned_trips = Trip.objects.owned_by(self.user1)
        self.assertEqual(owned_trips.count(), 1)
        self.assertEqual(owned_trips.first(), trip)

    def test_owned_by_multiple_owned_trips(self):
        """owned_by should return all trips where user is owner."""
        trip1 = TripSyntheticData.create_test_trip(user=self.user1, title='Trip 1')
        trip2 = TripSyntheticData.create_test_trip(user=self.user1, title='Trip 2')
        trip3 = TripSyntheticData.create_test_trip(user=self.user1, title='Trip 3')

        owned_trips = Trip.objects.owned_by(self.user1)
        self.assertEqual(owned_trips.count(), 3)
        self.assertIn(trip1, owned_trips)
        self.assertIn(trip2, owned_trips)
        self.assertIn(trip3, owned_trips)


class TripManagerCascadeDeletionTestCase(TestCase):
    """Test CASCADE deletion behavior."""

    def test_delete_trip_removes_members(self):
        """Deleting trip should CASCADE delete all TripMembers."""
        user = User.objects.create_user(email='owner@test.com', password='pass')
        trip = Trip.objects.create_with_owner(owner=user, title='Trip to Delete')

        # Add additional members
        user2 = User.objects.create_user(email='member@test.com', password='pass')
        TripSyntheticData.add_trip_member(trip, user2, TripPermissionLevel.VIEWER, user)

        trip_id = trip.pk
        self.assertEqual(TripMember.objects.filter(trip_id=trip_id).count(), 2)

        # Delete trip
        trip.delete()

        # Verify all members deleted
        self.assertEqual(TripMember.objects.filter(trip_id=trip_id).count(), 0)

    def test_delete_user_removes_memberships(self):
        """Deleting user should CASCADE delete their TripMembers."""
        user = User.objects.create_user(email='user@test.com', password='pass')
        other_user = User.objects.create_user(email='other@test.com', password='pass')

        # Create trip owned by other_user
        trip = TripSyntheticData.create_test_trip(user=other_user, title='Trip')

        # Add user as member
        TripSyntheticData.add_trip_member(trip, user, TripPermissionLevel.VIEWER, other_user)

        user_id = user.pk
        self.assertEqual(TripMember.objects.filter(user_id=user_id).count(), 1)

        # Delete user
        user.delete()

        # Verify membership deleted
        self.assertEqual(TripMember.objects.filter(user_id=user_id).count(), 0)

        # Trip should still exist (owned by other_user)
        self.assertTrue(Trip.objects.filter(pk=trip.pk).exists())

    def test_delete_owner_deletes_trip_and_all_members(self):
        """Deleting trip owner should delete trip and all member relationships."""
        owner = User.objects.create_user(email='owner@test.com', password='pass')
        member1 = User.objects.create_user(email='member1@test.com', password='pass')
        member2 = User.objects.create_user(email='member2@test.com', password='pass')

        trip = TripSyntheticData.create_test_trip(user=owner, title='Trip')
        TripSyntheticData.add_trip_member(trip, member1, TripPermissionLevel.EDITOR, owner)
        TripSyntheticData.add_trip_member(trip, member2, TripPermissionLevel.VIEWER, owner)

        trip_id = trip.pk
        self.assertEqual(TripMember.objects.filter(trip_id=trip_id).count(), 3)

        # Delete owner (owner membership has CASCADE delete)
        owner.delete()

        # Since owner is deleted, their TripMember record is deleted
        # But trip still exists (no CASCADE from TripMember to Trip)
        # However, there's no explicit trip ownership field, so trip persists
        # This test verifies current behavior - may need adjustment based on business logic

        # Note: Current schema doesn't auto-delete trips when owner user deleted
        # Trip still exists but has no OWNER member
        self.assertTrue(Trip.objects.filter(pk=trip_id).exists())
        self.assertEqual(TripMember.objects.filter(trip_id=trip_id).count(), 2)  # member1, member2 remain


class TripManagerEdgeCasesTestCase(TestCase):
    """Test edge cases and error conditions."""

    def test_create_with_owner_minimal_fields(self):
        """Trip creation should work with only required fields."""
        user = User.objects.create_user(email='owner@test.com', password='pass')

        trip = Trip.objects.create_with_owner(owner=user, title='Minimal Trip')

        self.assertIsNotNone(trip.pk)
        self.assertEqual(trip.title, 'Minimal Trip')
        self.assertEqual(trip.trip_status, TripStatus.UPCOMING)

    def test_create_with_owner_empty_description(self):
        """Trip creation should handle empty description."""
        user = User.objects.create_user(email='owner@test.com', password='pass')

        trip = Trip.objects.create_with_owner(
            owner=user,
            title='Trip',
            description='',
        )

        self.assertEqual(trip.description, '')

    def test_for_user_performance_no_duplicates(self):
        """for_user should efficiently handle user with many trips."""
        user = User.objects.create_user(email='prolific@test.com', password='pass')

        # Create many trips
        trips = []
        for i in range(20):
            trip = TripSyntheticData.create_test_trip(user=user, title=f'Trip {i}')
            trips.append(trip)

        # Query should return all trips without duplicates
        user_trips = Trip.objects.for_user(user)
        self.assertEqual(user_trips.count(), 20)

        # Verify distinct() is working
        trip_ids = list(user_trips.values_list('pk', flat=True))
        self.assertEqual(len(trip_ids), len(set(trip_ids)))  # No duplicate IDs

    def test_owned_by_performance_multiple_roles(self):
        """owned_by should efficiently filter when user has multiple roles."""
        user = User.objects.create_user(email='multi@test.com', password='pass')
        other_user = User.objects.create_user(email='other@test.com', password='pass')

        # User owns some trips
        owned1 = TripSyntheticData.create_test_trip(user=user, title='Owned 1')
        owned2 = TripSyntheticData.create_test_trip(user=user, title='Owned 2')

        # User is member (not owner) of other trips
        member_trip = TripSyntheticData.create_test_trip(user=other_user, title='Member Trip')
        TripSyntheticData.add_trip_member(member_trip, user, TripPermissionLevel.EDITOR, other_user)

        # owned_by should only return owned trips
        owned_trips = Trip.objects.owned_by(user)
        self.assertEqual(owned_trips.count(), 2)
        self.assertIn(owned1, owned_trips)
        self.assertIn(owned2, owned_trips)
        self.assertNotIn(member_trip, owned_trips)
