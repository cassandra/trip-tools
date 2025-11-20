from django.db import models
from django.conf import settings

from tt.apps.common.model_fields import LabeledEnumField
from tt.apps.trips.enums import TripPermissionLevel
from tt.apps.trips.models import Trip

from . import managers


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
    invitation_accepted_datetime = models.DateTimeField(
        null = True,
        blank = True,
        help_text = 'When the invitation was accepted. Used for one-time token validation.',
    )

    class Meta:
        verbose_name = 'Trip Member'
        verbose_name_plural = 'Trip Members'
        unique_together = [ ('trip', 'user') ]

    def __str__(self):
        return f'{self.user.email} - {self.trip.title} ({self.permission_level})'
    
    def has_trip_permission( self, required_level: TripPermissionLevel ) -> bool:
        """
        Check if user has at least the required permission level for the trip.
        """
        return bool( self.permission_level >= required_level )

    @property
    def can_manage_members( self ):
        return self.has_trip_permission( required_level = TripPermissionLevel.ADMIN )

    @property
    def can_edit_trip( self ):
        return self.has_trip_permission( required_level = TripPermissionLevel.EDITOR )

    def can_modify_member( self, other_member : 'TripMember' ):
        return bool( self.can_manage_members
                     and ( self.permission_level >= other_member.permission_level ))
