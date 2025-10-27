from django.db import models


class CandidateGroupManager(models.Manager):
    """Manager for CandidateGroup model."""

    def for_user(self, user):
        """Get all candidate groups for a specific user."""
        return self.filter(user=user)

    def for_trip(self, trip):
        """Get all candidate groups for a specific trip."""
        return self.filter(trip=trip)

    def by_type(self, candidate_type):
        """Get candidate groups by type."""
        return self.filter(candidate_type=candidate_type)

    def for_location(self, location):
        """Get candidate groups associated with a specific location."""
        return self.filter(location=location)


class CandidateManager(models.Manager):
    """Manager for Candidate model."""

    def for_group(self, group):
        """Get all candidates for a specific group."""
        return self.filter(group=group)

    def sorted_by_preference(self, group):
        """Get candidates for a group sorted by preference order."""
        return self.filter(group=group).order_by('preference_order')
