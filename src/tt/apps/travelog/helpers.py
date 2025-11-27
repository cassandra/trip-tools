"""
Helper classes for travelog list operations.
"""
from typing import Callable, List, Optional, Tuple, TYPE_CHECKING

from django.core.exceptions import PermissionDenied
from django.http import Http404

from tt.apps.images.models import TripImage
from tt.apps.journal.models import Journal
from tt.apps.trips.models import Trip

from .exceptions import PasswordRequiredException
from .schemas import TravelogListItemData

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser


class TravelogPublicListBuilder:
    """
    Builds a sorted list of public travelogs for a user.

    Encapsulates all business logic for:
    - Querying journals with published travelogs
    - Filtering by access permissions
    - Computing date ranges (excluding special entries)
    - Selecting display images (preferring dated entries)
    - Sorting chronologically
    """

    @classmethod
    def build(
        cls,
        target_user: 'AbstractUser',
        access_checker: Callable[[Journal], None]
    ) -> List[TravelogListItemData]:
        """
        Build a sorted list of accessible travelogs for a user.

        Args:
            target_user: The user whose travelogs to list
            access_checker: Callable that checks journal access. Should raise
                PasswordRequiredException, Http404, or PermissionDenied as needed.

        Returns:
            List of TravelogListItemData sorted by latest date (newest first)
        """
        # Query journals with published travelogs
        trips = Trip.objects.owned_by(target_user)
        journals = Journal.objects.filter(
            trip__in=trips,
            travelogs__is_current=True
        ).distinct().select_related('trip').prefetch_related(
            'entries', 'entries__reference_image'
        )

        # Filter by access and build list items
        items = []
        for journal in journals:
            requires_password = False

            try:
                access_checker(journal)
            except PasswordRequiredException:
                requires_password = True
            except (Http404, PermissionDenied):
                continue

            items.append(cls._build_list_item(journal, requires_password))

        # Sort by latest date (newest first)
        return sorted(
            items,
            key=lambda item: item.latest_entry_date or '',
            reverse=True
        )

    @classmethod
    def _build_list_item(
        cls,
        journal: Journal,
        requires_password: bool
    ) -> TravelogListItemData:
        """
        Build a single TravelogListItemData from a journal.
        """
        entries = list(journal.entries.order_by('date'))

        earliest_date, latest_date = cls._compute_date_range(journal, entries)
        display_image = cls._select_display_image(journal, entries)

        return TravelogListItemData(
            journal=journal,
            requires_password=requires_password,
            earliest_entry_date=earliest_date,
            latest_entry_date=latest_date,
            display_image=display_image
        )

    @classmethod
    def _compute_date_range(
        cls,
        journal: Journal,
        entries: List
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Compute earliest and latest dates from dated entries only.

        Excludes prologue/epilogue entries (which use sentinel dates).
        Falls back to published_datetime or created_datetime if no dated entries.
        """
        dated_entries = [e for e in entries if not e.is_special_entry]

        if dated_entries:
            earliest_date = dated_entries[0].date.strftime('%Y-%m-%d')
            latest_date = dated_entries[-1].date.strftime('%Y-%m-%d')
        else:
            current_travelog = journal.travelogs.filter(is_current=True).first()
            if current_travelog:
                fallback_date = current_travelog.published_datetime.strftime('%Y-%m-%d')
            else:
                fallback_date = journal.created_datetime.strftime('%Y-%m-%d')
            earliest_date = fallback_date
            latest_date = fallback_date

        return earliest_date, latest_date

    @classmethod
    def _select_display_image(
        cls,
        journal: Journal,
        entries: List
    ) -> Optional[TripImage]:
        """
        Select display image, preferring dated entries over special entries.
        """
        if journal.reference_image:
            return journal.reference_image

        for entry in entries:
            if not entry.is_special_entry and entry.reference_image:
                return entry.reference_image

        for entry in entries:
            if entry.is_special_entry and entry.reference_image:
                return entry.reference_image

        return None
