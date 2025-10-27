from django.db import models


class LocationCategoryManager(models.Manager):

    def by_slug(self, slug):
        return self.get(slug=slug)


class LocationSubCategoryManager(models.Manager):

    def for_category(self, category):
        return self.filter(category=category)


class LocationManager(models.Manager):

    def for_user(self, user):
        return self.filter(user=user)

    def for_trip(self, trip):
        return self.filter(trip=trip)

    def by_category(self, category):
        return self.filter(category=category)


class LocationNoteManager(models.Manager):

    def for_location(self, location):
        return self.filter(location=location)
