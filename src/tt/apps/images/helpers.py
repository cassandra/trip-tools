from collections import defaultdict
from typing import List

from django.contrib.auth.models import User as UserType

from tt.apps.members.models import TripMember
from tt.apps.trips.context import TripPageContext
from tt.apps.trips.enums import TripPermissionLevel
from tt.apps.trips.models import Trip

from .enums import ImageAccessRole
from .models import TripImage


# Maximum files allowed per bulk upload batch (matches frontend limit)
MAX_UPLOAD_BATCH_SIZE = 50


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

        Ordering strategy:
        - Images from the same bulk upload (sharing upload_session_uuid) are
          grouped together and sorted by datetime_utc (photo capture time)
        - Groups are ordered by most recent uploaded_datetime DESC
        - This provides intuitive ordering where bulk uploads display in photo
          capture order rather than arbitrary server processing order

        Performance strategy:
        - Filters for editor+ permission levels only (typically 2-5 users)
        - Queries each editor's images separately (efficient single-user queries)
        - This approach scales well because IN clause + ORDER BY negates indexes,
          but individual user queries are index-friendly
        - Over-fetches by MAX_UPLOAD_BATCH_SIZE to ensure complete batches

        Args:
            trip: Trip instance
            limit: Maximum number of images to return (default: 50)

        Returns:
            List of TripImage instances grouped by upload session
        """
        editor_levels = [
            TripPermissionLevel.EDITOR,
            TripPermissionLevel.ADMIN,
            TripPermissionLevel.OWNER,
        ]

        editor_user_ids = TripMember.objects.filter(
            trip=trip,
            permission_level__in=editor_levels
        ).values_list('user_id', flat=True)

        # Over-fetch to ensure complete upload batches at boundary
        fetch_limit = limit + MAX_UPLOAD_BATCH_SIZE

        # Query each editor's recent images separately (efficient)
        all_images = []
        for user_id in editor_user_ids:
            user_images = list(
                TripImage.objects.filter(uploaded_by_id=user_id)
                .select_related('uploaded_by')
                .order_by('-uploaded_datetime')[:fetch_limit]
            )
            all_images.extend(user_images)

        # Group by upload_session_uuid (use image uuid as fallback for single uploads)
        groups = defaultdict(list)
        for img in all_images:
            key = img.upload_session_uuid or img.uuid
            groups[key].append(img)

        # Sort groups by most recent uploaded_datetime DESC
        sorted_groups = sorted(
            groups.values(),
            key=lambda g: max(i.uploaded_datetime for i in g),
            reverse=True,
        )

        # Within each group, sort by datetime_utc ASC (None values last)
        result = []
        for group in sorted_groups:
            group.sort(key=lambda i: (i.datetime_utc is None, i.datetime_utc))
            result.extend(group)

        return result[:limit]
