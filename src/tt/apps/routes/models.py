from django.db import models

from tt.apps.geo.models import GeoPointModelMixin

from . import managers


class Route(models.Model):
    """
    A route (driving, hiking, etc.) connecting multiple locations.
    """
    objects = managers.RouteManager()

    trip = models.ForeignKey(
        'trips.Trip',
        on_delete = models.CASCADE,
        related_name = 'routes',
    )

    notes = models.TextField( blank = True )

    created_datetime = models.DateTimeField( auto_now_add = True )
    modified_datetime = models.DateTimeField( auto_now = True )

    class Meta:
        verbose_name = 'Route'
        verbose_name_plural = 'Routes'
        ordering = ['-created_datetime']


class RouteWaypoint( GeoPointModelMixin, models.Model ):
    """
    Ordered waypoints in a route.
    """
    objects = managers.RouteWaypointManager()

    route = models.ForeignKey(
        Route,
        on_delete = models.CASCADE,
        related_name = 'waypoints',
    )

    at_datetime = models.DateTimeField(
        'Date/Time',
        null = True,
        blank = True,
    )
    order = models.PositiveIntegerField( default = 0 )

    notes = models.TextField( blank = True )

    class Meta:
        verbose_name = 'Route Waypoint'
        verbose_name_plural = 'Route Waypoints'
        ordering = ['route', 'order']
        unique_together = [('route', 'order')]
