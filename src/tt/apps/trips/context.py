from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from django.db.models import QuerySet

from .enums import TripPage

if TYPE_CHECKING:
    from .models import Trip


@dataclass
class TripSidebarContext:
    """
    Encapsulates all data needed for trip sidebar navigation.

    Attributes:
        trip: The Trip instance being viewed
        active_page: Which page in the sidebar should be highlighted
        notebook_entries: QuerySet of notebook entries for sidebar list (Notes pages only)
        current_entry_pk: PK of currently viewed notebook entry for highlighting (Notes editor only)
    """

    trip: 'Trip'
    active_page: TripPage
    notebook_entries: Optional[QuerySet] = None
    current_entry_pk: Optional[int] = None
