from dataclasses import dataclass
from datetime import date
from typing import List, Optional, TYPE_CHECKING

from tt.apps.images.models import TripImage
from tt.apps.journal.models import Journal, JournalEntryContent

if TYPE_CHECKING:
    from tt.apps.journal.models import JournalEntry


@dataclass
class TravelogImageMetadata:
    """
    Metadata for a single image in a travelog.

    Extracted from HTML content and used for gallery/browse navigation.
    """
    uuid            : str       # TripImage UUID
    entry_date      : str       # Date of the journal entry (YYYY-MM-DD)
    layout          : str       # Image layout: 'float-right' or 'full-width'
    document_order  : int       # Order within the entire travelog (chronological)
    caption         : str = ''  # Caption from HTML content (empty if none)

    def to_dict(self) -> dict:
        """Serialize to dictionary for JSON caching."""
        return {
            'uuid': self.uuid,
            'entry_date': self.entry_date,
            'layout': self.layout,
            'document_order': self.document_order,
            'caption': self.caption,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'TravelogImageMetadata':
        """Deserialize from dictionary (from JSON cache)."""
        return cls(
            uuid = data['uuid'],
            entry_date = data['entry_date'],
            layout = data['layout'],
            document_order = data['document_order'],
            caption = data.get('caption', ''),  # Backward compatible
        )


@dataclass
class TravelogListItemData:
    """
    Display data for a journal/travelog in the user list view.

    Encapsulates the journal along with access metadata and display information.
    """
    journal              : Journal
    requires_password    : bool                 # True if PROTECTED and password not verified
    earliest_entry_date  : Optional[str]        = None  # YYYY-MM-DD format
    latest_entry_date    : Optional[str]        = None  # YYYY-MM-DD format
    day_count            : int                  = 0     # Number of dated entries (excluding special)
    display_image        : Optional[TripImage]  = None

    
@dataclass
class TocEntryData:
    """
    Display data for a single TOC sidebar entry.

    Wraps journal entry data with computed day number and active state,
    avoiding dynamic attribute mutation on model instances.
    """
    entry              : JournalEntryContent
    day_number         : Optional[int]   # None for prologue/epilogue
    is_active          : bool = False

    @property
    def display_title(self) -> str:
        """Format title with day number prefix."""
        title = self.entry.title
        if self.day_number:
            if title:
                return f"Day {self.day_number}: {title}"
            return f"Day {self.day_number}"
        return title or ""


@dataclass
class DayEntryNavData:
    """
    Navigation context for the current day entry.

    Wraps the actual entry with computed navigation state (prev/next dates)
    and day number, keeping the entry accessible for text/display methods.
    """
    entry      : 'JournalEntry'        # The actual entry (for text, display methods)
    day_number : Optional[int]         # None for prologue/epilogue
    prev_date  : Optional[date] = None
    next_date  : Optional[date] = None

    @property
    def has_previous(self) -> bool:
        return self.prev_date is not None

    @property
    def has_next(self) -> bool:
        return self.next_date is not None


@dataclass
class DayPageData:
    """
    Complete context for travelog day page rendering.

    Consolidates all computed data needed for the day page template,
    built by DayPageBuilder from raw entries.
    """
    toc_entries    : List[TocEntryData]
    current_entry  : DayEntryNavData
    day_count      : int
    first_day_date : Optional[date] = None
    last_day_date  : Optional[date] = None


@dataclass
class TocPageData:
    """
    Complete context for travelog TOC page rendering.

    Consolidates all computed data needed for the TOC page template,
    built by TocPageBuilder from raw entries.
    """
    toc_entries    : List[TocEntryData]
    day_count      : int
    first_day_date : Optional[date] = None
    last_day_date  : Optional[date] = None
