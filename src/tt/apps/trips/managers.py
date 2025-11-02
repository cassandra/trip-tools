from django.db import models, transaction


class TripManager(models.Manager):

    def for_user(self, user):
        """Get all trips where user is a member (any permission level)."""
        return self.filter( members__user = user ).distinct()

    def owned_by(self, user):
        """Get all trips where user is the owner."""
        from .enums import TripPermissionLevel
        return self.filter(
            members__user = user,
            members__permission_level = TripPermissionLevel.OWNER,
        ).distinct()

    def create_with_owner(self, owner, **trip_fields):
        """
        Create a new trip with the specified owner.

        Atomically creates both the Trip and the owner's TripMember record.
        Sets trip_status to UPCOMING if not provided.

        Args:
            owner: User instance who will own the trip
            **trip_fields: Field values for the Trip (title, description, etc.)

        Returns:
            Trip: The newly created trip instance

        Example:
            trip = Trip.objects.create_with_owner(
                owner=request.user,
                title='Summer Vacation',
                description='A fun trip'
            )
        """
        from .enums import TripPermissionLevel, TripStatus
        from .models import TripMember

        # Set default status if not provided
        if 'trip_status' not in trip_fields:
            trip_fields['trip_status'] = TripStatus.UPCOMING

        with transaction.atomic():
            trip = self.create( **trip_fields )

            TripMember.objects.create(
                trip = trip,
                user = owner,
                permission_level = TripPermissionLevel.OWNER,
                added_by = owner,
            )

        return trip


class TripMemberManager(models.Manager):

    def for_trip(self, trip):
        """Get all members for a specific trip."""
        return self.filter( trip = trip )

    def for_user(self, user):
        """Get all trip memberships for a specific user."""
        return self.filter( user = user )
