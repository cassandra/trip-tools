from dataclasses import dataclass
from typing import Optional

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


class PublishingStatusHelper:

    @classmethod
    def get_publishing_status(cls, journal: Journal) -> PublishingStatus:

        current_travelog = Travelog.objects.get_current( journal )
        has_published_version = current_travelog is not None

        if has_published_version:
            has_changes = cls._has_unpublished_changes( journal, current_travelog )
        else:
            has_changes = False

        return PublishingStatus(
            current_published_version = current_travelog,
            has_unpublished_changes = has_changes,
            has_published_version = has_published_version,
        )

    @classmethod
    def _has_unpublished_changes(cls, journal: Journal, travelog: Travelog) -> bool:
        """
        Check if journal has been modified since publication.

        For Journal metadata (title, description): compares content directly since
        Journal.modified_datetime updates during publish transaction.

        For JournalEntries: compares modification timestamps since entries aren't
        modified during publish.
        """
        # Compare Journal content directly (title and description are published fields)
        if journal.title != travelog.title:
            return True
        if journal.description != travelog.description:
            return True

        # Compare JournalEntry timestamps (entries modified after publish)
        published_datetime = travelog.published_datetime
        if journal.entries.filter(modified_datetime__gt=published_datetime).exists():
            return True

        # Check if entry count changed (entries added or deleted)
        journal_entry_count = journal.entries.count()
        travelog_entry_count = travelog.entries.count()
        if journal_entry_count != travelog_entry_count:
            return True

        return False
