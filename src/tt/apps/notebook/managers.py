from django.db import models


class NotebookEntryManager(models.Manager):
    """Manager for NotebookEntry model."""

    def for_user(self, user):
        """Get all notebook entries for a specific user."""
        return self.filter(user=user)

    def for_trip(self, trip):
        """Get all notebook entries for a specific trip."""
        return self.filter(trip=trip)

    def for_date(self, trip, date):
        """Get notebook entry for a specific date."""
        try:
            return self.get(trip=trip, date=date)
        except self.model.DoesNotExist:
            return None
