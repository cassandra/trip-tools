from django.db import models


class ReviewManager(models.Manager):

    def for_user(self, user):
        return self.filter( trip__members__user = user ).distinct()

    def for_location(self, location):
        return self.filter( location = location )

    def for_trip(self, trip):
        return self.filter( trip = trip )

    def posted_externally(self):
        return self.exclude( posted_to = '' )
