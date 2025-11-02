from django.db import models


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


class TripMemberManager(models.Manager):

    def for_trip(self, trip):
        """Get all members for a specific trip."""
        return self.filter( trip = trip )

    def for_user(self, user):
        """Get all trip memberships for a specific user."""
        return self.filter( user = user )
