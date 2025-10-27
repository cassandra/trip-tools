from django.db import models


class ReviewManager(models.Manager):
    """Manager for Review model."""

    def for_user(self, user):
        """Get all reviews for a specific user."""
        return self.filter(user=user)

    def for_location(self, location):
        """Get all reviews for a specific location."""
        return self.filter(location=location)

    def for_trip(self, trip):
        """Get all reviews for a specific trip."""
        return self.filter(trip=trip)

    def posted_externally(self):
        """Get reviews that have been posted to external sites."""
        return self.exclude(posted_to='')
