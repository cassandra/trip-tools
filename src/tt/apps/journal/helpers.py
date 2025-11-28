"""
Helper classes for journal publishing workflow and UI.

Centralizes publishing-related context building and entry selection statistics.
"""
from tt.apps.travelog.models import Travelog

from .forms import JournalVisibilityForm
from .models import Journal
from .schemas import EntrySelectionStats, PublishingStatus


class JournalPublishContextBuilder:
    """Builds template context dictionaries for journal publishing modal views."""

    @classmethod
    def build_modal_context( cls,
                             journal            : Journal,
                             publishing_status  : PublishingStatus,
                             visibility_form    : JournalVisibilityForm ) -> dict:
        """
        Build complete context for publish modal display.

        Consolidates context building logic including entry counts
        and progressive disclosure state.
        """
        journal_entries = list( journal.entries.order_by('date') )
        stats = EntrySelectionStats.for_journal( journal = journal )

        return {
            'journal': journal,
            'trip': journal.trip,
            'publishing_status': publishing_status,
            'visibility_form': visibility_form,
            'journal_entries': journal_entries,
            'total_entries': stats.total_entries,
            'included_entries': stats.included_entries,
            'all_entries_included': stats.all_entries_included,
        }


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
        # Compare Journal content directly (title, description, reference_image are published fields)
        if journal.title != travelog.title:
            return True
        if journal.description != travelog.description:
            return True
        if journal.reference_image_id != travelog.reference_image_id:
            return True

        # Compare JournalEntry timestamps (entries modified after publish)
        # Only consider entries that are marked for publishing
        published_datetime = travelog.published_datetime
        if journal.entries.filter(
            include_in_publish=True,
            modified_datetime__gt=published_datetime
        ).exists():
            return True

        # Check if entry count changed (entries added or deleted)
        # Only count entries marked for publishing
        journal_entry_count = journal.entries.filter(include_in_publish=True).count()
        travelog_entry_count = travelog.entries.count()
        if journal_entry_count != travelog_entry_count:
            return True

        return False
    
