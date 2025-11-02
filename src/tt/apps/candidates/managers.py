from django.db import models


class CandidateGroupManager(models.Manager):

    def for_user(self, user):
        return self.filter( trip__members__user = user ).distinct()

    def for_trip(self, trip):
        return self.filter( trip = trip )

    def by_type(self, candidate_type):
        return self.filter( candidate_type = candidate_type )

    def for_location(self, location):
        return self.filter( location = location )


class CandidateManager(models.Manager):

    def for_group(self, group):
        return self.filter(group=group)

    def sorted_by_preference(self, group):
        return self.filter(group=group).order_by('preference_order')
