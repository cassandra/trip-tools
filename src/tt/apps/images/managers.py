from django.db import models


class TripImageManager(models.Manager):
    """Manager for TripImage model."""

    def for_user(self, user) -> models.QuerySet:
        """
        Get all images uploaded by the user.
        TODO: Extend to include images accessible via journal permissions.
        """
        return self.filter(uploaded_by=user)

    def accessible_to_user_in_trip(self, user, trip) -> models.QuerySet:
        """
        Get all images accessible to user in the context of a trip.

        Returns images from all current trip members (including the user).

        Args:
            user: User requesting access
            trip: Trip context for permission check

        Returns:
            QuerySet of TripImage instances accessible to user in this trip
        """
        if not user or not user.is_authenticated:
            return self.none()

        # Get all current trip member user IDs
        from tt.apps.trips.models import TripMember
        member_user_ids = TripMember.objects.filter(
            trip=trip
        ).values_list('user_id', flat=True)

        # Return images uploaded by any current member
        return self.filter(uploaded_by__id__in=member_user_ids)

    def accessible_to_user_in_trip_for_date_range(
        self,
        user,
        trip,
        start_datetime,
        end_datetime
    ) -> models.QuerySet:
        """
        Get images accessible to user in trip, filtered by date range.

        This is the primary method for journal entry editing - shows images
        from all current trip members within the entry's day boundaries.

        Args:
            user: User requesting access
            trip: Trip context for permission check
            start_datetime: Start of date range (timezone-aware datetime)
            end_datetime: End of date range (timezone-aware datetime)

        Returns:
            QuerySet of TripImage instances within date range
        """
        # Get base accessible images
        accessible_images = self.accessible_to_user_in_trip(user, trip)

        # Filter by date range
        # Note: Images with null datetime_utc are excluded
        return accessible_images.filter(
            datetime_utc__gte=start_datetime,
            datetime_utc__lt=end_datetime,
        ).select_related('uploaded_by')

    def for_trip(self, trip) -> models.QuerySet:
        """
        Get all images from trip members (following codebase .for_trip() pattern).

        Note: This doesn't check permissions, just returns images from trip members.
        For permission-aware queries, use accessible_to_user_in_trip().

        Args:
            trip: Trip instance

        Returns:
            QuerySet of TripImage instances from trip members
        """
        from tt.apps.trips.models import TripMember
        member_user_ids = TripMember.objects.filter(
            trip=trip
        ).values_list('user_id', flat=True)

        return self.filter(uploaded_by__id__in=member_user_ids)
