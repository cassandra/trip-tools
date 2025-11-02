from django.db import models


class RouteManager(models.Manager):

    def for_user(self, user):
        return self.filter( trip__members__user = user ).distinct()

    def for_trip(self, trip):
        return self.filter( trip = trip )


class RouteWaypointManager(models.Manager):

    def for_route(self, route):
        return self.filter(route=route)
