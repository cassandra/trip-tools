from django.db import models

from tt.apps.api.models import SyncableModel
from tt.apps.common.model_fields import LabeledEnumField

from .enums import TripPermissionLevel, TripStatus
from . import managers


class Trip( SyncableModel ):
    """
    Core organizing entity for all trip-related data.
    Access controlled via TripMember permission model.

    Inherits from SyncableModel:
    - uuid: External identifier
    - version: Auto-incremented on save for change detection
    - created_datetime: Record creation timestamp
    - modified_datetime: Last modification timestamp
    """
    objects = managers.TripManager()

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
