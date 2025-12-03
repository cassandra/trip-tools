from dataclasses import dataclass
from datetime import date as date_class
from typing import Optional

from django.db.models import QuerySet

from tt.apps.images.models import TripImage
from tt.apps.travelog.models import Travelog

from .models import Journal


@dataclass
class PublishingStatus:

    current_published_version  : Optional[Travelog]
    has_unpublished_changes    : bool
    has_published_version      : bool

    @property
    def is_published_with_changes(self) -> bool:
        return bool( self.has_published_version and self.has_unpublished_changes )

    @property
    def is_published_without_changes(self) -> bool:
        return bool( self.has_published_version and not self.has_unpublished_changes )

    @property
    def is_unpublished(self) -> bool:
        return not self.has_published_version


@dataclass
class EntrySelectionStats:
    """Statistics about journal entry publishing selections."""

    total_entries    : int
    included_entries : int

    @property
    def excluded_entries(self) -> int:
        return self.total_entries - self.included_entries

    @property
    def all_entries_included(self) -> bool:
        return self.included_entries == self.total_entries

    @property
    def none_included(self) -> bool:
        return self.included_entries == 0

    @classmethod
    def for_journal(cls, journal: Journal) -> 'EntrySelectionStats':
        """Calculate selection statistics for a journal."""
        entries = list(journal.entries.all())
        included = sum(1 for entry in entries if entry.include_in_publish)
        return cls(
            total_entries=len(entries),
            included_entries=included
        )


@dataclass
class EditorImagePickerData:
    """
    Encapsulates context data for the journal editor image picker component.
    """

    accessible_images       : QuerySet[TripImage]
    is_recent_mode          : bool
    filter_date             : Optional[date_class]
    image_display_timezone  : str
