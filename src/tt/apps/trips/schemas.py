from dataclasses import dataclass
from typing import List, Optional

from tt.apps.journal.models import Journal
from tt.apps.journal.schemas import PublishingStatus

from .models import Trip


@dataclass
class JournalOverviewSection:

    # Core state
    journal            : Journal
    can_edit           : bool
    publishing_status  : Optional[PublishingStatus]

    # Pre-computed URLs (None if not applicable)
    published_url      : Optional[str]
    draft_url          : Optional[str]

    @property
    def journal_exists(self) -> bool:
        return bool( self.journal is not None )


@dataclass
class TripOverviewData:
    """
    Container for all trip overview page display data.

    As more features are added to the overview page, add new section
    dataclasses here (e.g., itinerary_section, booking_section, etc.).
    """

    journal_section: JournalOverviewSection


@dataclass
class TripCategorizedDisplayData:

    current_trips  : List[Trip]
    shared_trips   : List[Trip]
    past_trips     : List[Trip]

    @property
    def total_trips(self) -> int:
        return len(self.current_trips) + len(self.shared_trips) + len(self.past_trips)
