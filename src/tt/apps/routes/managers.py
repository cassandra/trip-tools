from django.db import models


class RouteManager(models.Manager):
    """Manager for Route model."""

    def for_user(self, user):
        """Get all routes for a specific user."""
        return self.filter(user=user)

    def for_trip(self, trip):
        """Get all routes for a specific trip."""
        return self.filter(trip=trip)


class RouteWaypointManager(models.Manager):
    """Manager for RouteWaypoint model."""

    def for_route(self, route):
        """Get all waypoints for a specific route."""
        return self.filter(route=route)
