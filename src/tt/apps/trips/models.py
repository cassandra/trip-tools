from django.db import models
from django.conf import settings

from tt.apps.common.model_fields import LabeledEnumField

from .enums import TripStatus
from . import managers


class Trip(models.Model):
    """
    Core organizing entity for all trip-related data.
    Each trip belongs to a single user (multi-tenant).
    """
    objects = managers.TripManager()

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete = models.CASCADE,
        related_name = 'trips',
    )
    title = models.CharField(
        max_length = 200,
    )
    description = models.TextField(
        blank = True,
    )
    trip_status = LabeledEnumField(
        TripStatus,
        'Trip Status',
    )
    created_datetime = models.DateTimeField( auto_now_add = True )
    modified_datetime = models.DateTimeField( auto_now = True )

    class Meta:
        verbose_name = 'Trip'
        verbose_name_plural = 'Trips'
        ordering = [ '-created_datetime' ]
        indexes = [
            models.Index(fields=['user', '-created_datetime']),
        ]

    def __repr__(self):
        return f'{self.title} [{self.pk}]'

    def __str__(self):
        return f'{self.title} [{self.pk}]'
