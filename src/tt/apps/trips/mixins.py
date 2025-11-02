from django.contrib.auth import get_user_model

from .enums import TripPermissionLevel
from .models import Trip

User = get_user_model()


class TripPermissionMixin:
    """
    Mixin providing trip permission checking functionality.
    """

    PERMISSION_HIERARCHY = {
        TripPermissionLevel.OWNER: 4,
        TripPermissionLevel.ADMIN: 3,
        TripPermissionLevel.EDITOR: 2,
        TripPermissionLevel.VIEWER: 1,
    }

    def has_trip_permission(
        self,
        user: User,
        trip: Trip,
        required_level: TripPermissionLevel,
    ) -> bool:
        """
        Check if user has at least the required permission level for the trip.

        Returns True if user's permission level is >= required_level.
        Permission hierarchy: Owner > Admin > Editor > Viewer
        """
        user_permission = trip.get_user_permission( user )

        if user_permission is None:
            return False

        user_level = self.PERMISSION_HIERARCHY.get( user_permission, 0 )
        required_level_value = self.PERMISSION_HIERARCHY.get( required_level, 0 )

        return bool( user_level >= required_level_value )
