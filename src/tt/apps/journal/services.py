"""
Journal service layer for business logic.
"""
from datetime import date as date_class

from tt.apps.images.models import TripImage
from .utils import get_entry_date_boundaries


class JournalImagePickerService:
    """Service for journal image picker operations."""

    @staticmethod
    def get_accessible_images_for_image_picker(trip, user, date, timezone, scope='all'):
        """
        Get images accessible for journal image picker, ordered chronologically.

        Returns images for the specified date in chronological order by datetime_utc.
        This is the single source of truth for image picker queries.

        Args:
            trip: Trip instance
            user: User instance for permission checking
            date: Date to fetch images for (date object)
            timezone: Timezone string for date boundary calculation
            scope: Filter scope - 'all', 'unused', or 'in-use' (default: 'all')
                   NOTE: Only 'all' is implemented currently. Filtering logic
                   will be added when text editing is implemented.

        Returns:
            QuerySet of TripImage objects ordered by datetime_utc
        """
        start_dt, end_dt = get_entry_date_boundaries(date, timezone)
        images = TripImage.objects.accessible_to_user_in_trip_for_date_range(
            user=user,
            trip=trip,
            start_datetime=start_dt,
            end_datetime=end_dt,
        ).order_by('datetime_utc')

        # TODO: Apply scope filtering when text editing is implemented
        # if scope == 'unused':
        #     # Filter to images not used in this entry
        #     pass
        # elif scope == 'in-use':
        #     # Filter to images used in this entry
        #     pass

        return images
