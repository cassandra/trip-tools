from typing import List

from django.contrib.auth.models import User as UserType

from tt.apps.members.models import TripMember
from tt.apps.trips.context import TripPageContext
from tt.apps.trips.enums import TripPermissionLevel
from tt.apps.trips.models import Trip

from .enums import ImageAccessRole
from .models import TripImage


class TripImageHelpers:

    @classmethod
    def get_image_access_mode( cls,
                               user               : UserType,
                               trip_image         : TripImage,
                               trip_page_context  : TripPageContext = None ) -> ImageAccessRole:

        if not user or not user.is_authenticated:
            return ImageAccessRole.NONE
        if trip_image.uploaded_by == user:
            return ImageAccessRole.OWNER
        if trip_page_context:
            if trip_page_context.request_member.can_edit_trip:
                return ImageAccessRole.EDITOR
            else:
                return ImageAccessRole.VIEWER
        return ImageAccessRole.NONE

    @classmethod
    def get_recent_images_for_trip_editors(cls, trip: Trip, limit: int = 50) -> List[TripImage]:
        """
        Get recent images from trip members with editor+ permissions.

        This is used as a fallback when date-based image picker queries return
        no results. Only includes images from users with EDITOR, ADMIN, or OWNER
        permission levels.

        Performance strategy:
        - Filters for editor+ permission levels only (typically 2-5 users)
        - Queries each editor's images separately (efficient single-user queries)
        - Merges and sorts in Python by uploaded_datetime DESC
        - This approach scales well because IN clause + ORDER BY negates indexes,
          but individual user queries are index-friendly

        Args:
            trip: Trip instance
            limit: Maximum number of images to return (default: 50)

        Returns:
            List of TripImage instances ordered by uploaded_datetime DESC
        """
        # Get editor+ permission levels
        editor_levels = [
            TripPermissionLevel.EDITOR,
            TripPermissionLevel.ADMIN,
            TripPermissionLevel.OWNER,
        ]

        # Get user IDs of trip members with editor+ permissions
        editor_user_ids = TripMember.objects.filter(
            trip=trip,
            permission_level__in=editor_levels
        ).values_list('user_id', flat=True)

        # Query each editor's recent images separately (efficient)
        all_images = []
        for user_id in editor_user_ids:
            user_images = list(
                TripImage.objects.filter(uploaded_by_id=user_id)
                .select_related('uploaded_by')
                .order_by('-uploaded_datetime')[:limit]
            )
            all_images.extend(user_images)

        # Merge and sort in Python
        all_images.sort(key=lambda img: img.uploaded_datetime, reverse=True)
        return all_images[:limit]
