"""
Synthetic data generators for Trip and TripMember models.

This module provides factory functions for creating test data following
the project's synthetic_data.py pattern. It creates real database objects
(never mocks) for use in Django tests.
"""

from tt.apps.trips.models import Trip, TripMember
from tt.apps.trips.enums import TripPermissionLevel, TripStatus


class TripSyntheticData:
    """Factory methods for creating Trip test data with proper relationships."""

    @staticmethod
    def create_test_trip(user, title='Test Trip', description='', trip_status=TripStatus.UPCOMING, **kwargs):
        """
        Create a Trip with an OWNER TripMember relationship.

        This is the standard way to create trips in tests. It automatically
        creates the TripMember relationship with OWNER permission.

        Args:
            user: The User who will own this trip
            title: Trip title (default: 'Test Trip')
            description: Trip description (default: '')
            trip_status: TripStatus enum value (default: TripStatus.UPCOMING)
            **kwargs: Additional fields to pass to Trip.objects.create()

        Returns:
            Trip: The created Trip instance with owner relationship established

        Example:
            trip = TripSyntheticData.create_test_trip(
                user=self.user,
                title='My Test Trip',
                trip_status=TripStatus.ACTIVE
            )
        """
        # Create the trip
        trip = Trip.objects.create(
            title=title,
            description=description,
            trip_status=trip_status,
            **kwargs
        )

        # Create the owner membership
        TripMember.objects.create(
            trip=trip,
            user=user,
            permission_level=TripPermissionLevel.OWNER,
            added_by=user,
        )

        return trip

    @staticmethod
    def add_trip_member(trip, user, permission_level=TripPermissionLevel.EDITOR, added_by=None):
        """
        Add a member to an existing trip with specified permission level.

        Args:
            trip: The Trip to add the member to
            user: The User to add as a member
            permission_level: TripPermissionLevel enum value (default: EDITOR)
            added_by: User who added this member (default: trip owner)

        Returns:
            TripMember: The created TripMember instance

        Example:
            member = TripSyntheticData.add_trip_member(
                trip=trip,
                user=other_user,
                permission_level=TripPermissionLevel.VIEWER
            )
        """
        if added_by is None:
            added_by = user

        return TripMember.objects.create(
            trip=trip,
            user=user,
            permission_level=permission_level,
            added_by=added_by,
        )
