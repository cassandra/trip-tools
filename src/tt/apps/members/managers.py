from django.db import models


class TripMemberManager(models.Manager):

    def for_trip(self, trip):
        """Get all members for a specific trip."""
        return self.filter( trip = trip )

    def for_user(self, user):
        """Get all trip memberships for a specific user."""
        return self.filter( user = user )
