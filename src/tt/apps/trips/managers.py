from django.db import models


class TripManager(models.Manager):

    def for_user(self, user):
        return self.filter( user = user )
