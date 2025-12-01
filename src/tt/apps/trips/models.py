import uuid

from django.db import models

from tt.apps.common.model_fields import LabeledEnumField

from .enums import TripPermissionLevel, TripStatus
from . import managers


class Trip(models.Model):
    """
    Core organizing entity for all trip-related data.
    Access controlled via TripMember permission model.
    """
    objects = managers.TripManager()

    uuid = models.UUIDField(
        default = uuid.uuid4,
        unique = True,
        editable = False,
    )
    title = models.CharField(
        max_length = 200,
    )
    description = models.TextField(
        blank = True,
    )
    reference_image = models.ForeignKey(
        'images.TripImage',
        on_delete = models.SET_NULL,
        null = True,
        blank = True,
        related_name = 'trip_references',
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

    def __repr__(self):
        return f'{self.title} [{self.pk}]'

    def __str__(self):
        return f'{self.title} [{self.pk}]'

    @property
    def owner(self):
        """Returns the user with OWNER permission. Cached to prevent N+1 queries."""
        if not hasattr(self, '_owner_cache'):
            owner_member = self.members.filter(
                permission_level = TripPermissionLevel.OWNER
            ).order_by( 'added_datetime' ).first()
            self._owner_cache = owner_member.user if owner_member else None
        return self._owner_cache
