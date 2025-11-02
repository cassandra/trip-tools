from django.db import models
from django.conf import settings

from tt.apps.common.model_fields import LabeledEnumField

from .enums import TripPermissionLevel, TripStatus
from . import managers


class Trip(models.Model):
    """
    Core organizing entity for all trip-related data.
    Access controlled via TripMember permission model.
    """
    objects = managers.TripManager()

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

    def __repr__(self):
        return f'{self.title} [{self.pk}]'

    def __str__(self):
        return f'{self.title} [{self.pk}]'

    @property
    def owner(self):
        """Returns the user with OWNER permission. Cached to prevent N+1 queries."""
        if not hasattr(self, '_owner_cache'):
            owner_member = self.members.filter( permission_level = TripPermissionLevel.OWNER ).first()
            self._owner_cache = owner_member.user if owner_member else None
        return self._owner_cache

    def get_user_permission(self, user):
        """Returns the permission level for a user, or None if not a member."""
        try:
            member = self.members.get( user = user )
            if isinstance( member.permission_level, TripPermissionLevel ):
                return member.permission_level
            return TripPermissionLevel.from_name( member.permission_level )
        except TripMember.DoesNotExist:
            return None


class TripMember(models.Model):
    """
    Through model for Trip-User many-to-many relationship with permissions.
    Tracks who has access to a trip and at what permission level.
    """
    objects = managers.TripMemberManager()

    trip = models.ForeignKey(
        Trip,
        on_delete = models.CASCADE,
        related_name = 'members',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete = models.CASCADE,
        related_name = 'trip_memberships',
    )
    permission_level = LabeledEnumField(
        TripPermissionLevel,
        'Permission Level',
    )
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete = models.SET_NULL,
        null = True,
        related_name = 'trips_shared_by_me',
    )
    added_datetime = models.DateTimeField( auto_now_add = True )

    class Meta:
        verbose_name = 'Trip Member'
        verbose_name_plural = 'Trip Members'
        unique_together = [ ('trip', 'user') ]
        indexes = [
            models.Index( fields = ['user', 'trip'] ),
            models.Index( fields = ['trip', 'permission_level'] ),
        ]

    def __str__(self):
        return f'{self.user.email} - {self.trip.title} ({self.permission_level})'
