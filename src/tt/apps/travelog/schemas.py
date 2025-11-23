from dataclasses import dataclass
from typing import Optional

from tt.apps.images.models import TripImage
from tt.apps.journal.models import Journal


@dataclass
class TravelogImageMetadata:
    """
    Metadata for a single image in a travelog.

    Extracted from HTML content and used for gallery/browse navigation.
    """
    uuid            : str  # TripImage UUID
    entry_date      : str  # Date of the journal entry (YYYY-MM-DD)
    layout          : str  # Image layout: 'float-right' or 'full-width'
    document_order  : int  # Order within the entire travelog (chronological)

    def to_dict(self) -> dict:
        """Serialize to dictionary for JSON caching."""
        return {
            'uuid': self.uuid,
            'entry_date': self.entry_date,
            'layout': self.layout,
            'document_order': self.document_order,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'TravelogImageMetadata':
        """Deserialize from dictionary (from JSON cache)."""
        return cls(
            uuid = data['uuid'],
            entry_date = data['entry_date'],
            layout = data['layout'],
            document_order = data['document_order'],
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
    display_image        : Optional[TripImage]  = None
