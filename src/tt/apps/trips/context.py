from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from django.db.models import QuerySet

from .enums import TripPage

if TYPE_CHECKING:
    from .models import TripMember


@dataclass
class TripPageContext:
    """
    Encapsulates all data needed for trip trip_page navigation.

    Attributes:
        active_page: Which page in the sidebar should be highlighted
        request_member: The TripMember instance for the requesting user (for permission checks)
        notebook_entries: QuerySet of notebook entries for sidebar list (Notes pages only)
        notebook_entry_pk: PK of currently viewed notebook entry for highlighting (Notes editor only)
    """

    active_page       : TripPage
    request_member    : 'TripMember'
    notebook_entries  : Optional[QuerySet] = None
    notebook_entry_pk  : Optional[int] = None

    @property
    def trip(self):
        return self.request_member.trip
    
