from dataclasses import dataclass

from .enums import TripPage
from .models import TripMember


@dataclass
class TripPageContext:
    """
    Encapsulates all data needed for trip trip_page navigation.

    Attributes:
        active_page: Which page in the sidebar should be highlighted
        request_member: The TripMember instance for the requesting user (for permission checks)
    """

    active_page       : TripPage
    request_member    : 'TripMember'

    @property
    def trip(self):
        return self.request_member.trip
    
