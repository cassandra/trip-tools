from django.db import models
from django.conf import settings

from tt.apps.common.model_fields import LabeledEnumField
from tt.apps.locations.models import Location
from tt.apps.routes.models import Route

from .enums import ItineraryItemType
from . import managers


class Itinerary(models.Model):
    """
    A day-by-day itinerary for a trip.
    """
    objects = managers.ItineraryManager()

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete = models.CASCADE,
        related_name = 'itineraries',
    )

    trip = models.ForeignKey(
        'trips.Trip',
        on_delete = models.CASCADE,
        related_name = 'itineraries',
    )

    title = models.CharField(max_length = 200)
    description = models.TextField(blank = True)

    created_datetime = models.DateTimeField(auto_now_add = True)
    modified_datetime = models.DateTimeField(auto_now = True)

    class Meta:
        verbose_name = 'Itinerary'
        verbose_name_plural = 'Itineraries'
        ordering = ['trip', 'title']


class ItineraryItem(models.Model):
    """
    Individual activities/events in an itinerary.
    """
    objects = managers.ItineraryItemManager()

    itinerary = models.ForeignKey(
        Itinerary,
        on_delete = models.CASCADE,
        related_name = 'items',
    )
    item_type = LabeledEnumField(
        ItineraryItemType,
        'Item Type',
    )
    title = models.CharField(
        max_length = 200,
    )
    description = models.TextField(
        blank = True,
    )
    notes = models.TextField(
        blank = True,
    )
    location = models.ForeignKey(
        Location,
        on_delete = models.SET_NULL,
        null = True,
        blank = True,
        related_name = 'itinerary_items',
    )
    route = models.ForeignKey(
        Route,
        null = True,
        blank = True,
        on_delete = models.SET_NULL,
        related_name = 'itinerary_items',
    )

    start_datetime = models.DateTimeField(
        'Start Time',
    )
    end_datetime = models.DateTimeField(
        'End Time',
        null = True,
        blank = True,
 
    )
    created_datetime = models.DateTimeField( auto_now_add = True )
    modified_datetime = models.DateTimeField( auto_now = True )

    class Meta:
        verbose_name = 'Itinerary Item'
        verbose_name_plural = 'Itinerary Items'
