"""
Journal service layer for business logic.
"""
from django.contrib.auth import get_user_model
from django.db import transaction

from tt.apps.travelog.models import Travelog, TravelogEntry

from .models import Journal, JournalEntry

User = get_user_model()


class RestoreError(Exception):
    """Exception raised when publishing operations fail."""
    pass


class JournalRestoreService:
    """Service for restoring journal working copy from a published travelog version."""

    @staticmethod
    @transaction.atomic
    def restore_from_version( journal: Journal, travelog: Travelog, user: User ) -> int:
        """
        Restore journal working copy from a previous published version (travelog).

        DESTRUCTIVE: Deletes all current journal entries and replaces them with
        entries from the travelog snapshot. The published version (is_current) is NOT changed.

        Raises:
            RestoreError: If validation fails or business rules are violated
        """

        if travelog.journal_id != journal.id:
            raise RestoreError(
                "Cannot restore: Travelog does not belong to this journal"
            )

        travelog_entries = TravelogEntry.objects.filter( travelog = travelog )
        if not travelog_entries.exists():
            raise RestoreError(
                "Cannot restore from a version with no entries"
            )

        locked_journal = journal.__class__.objects.select_for_update().get( pk = journal.pk )
        JournalEntry.objects.filter( journal=locked_journal ).delete()

        entries_to_create = []
        for travelog_entry in travelog_entries:
            new_entry = JournalEntry(
                journal = locked_journal,
                date = travelog_entry.date,
                title = travelog_entry.title,
                text = travelog_entry.text,
                timezone = travelog_entry.timezone,
                reference_image = travelog_entry.reference_image,
                modified_by = user,
            )
            entries_to_create.append( new_entry )

        JournalEntry.objects.bulk_create( entries_to_create )

        locked_journal.title = travelog.title
        locked_journal.reference_image = travelog.reference_image
        locked_journal.description = travelog.description
        locked_journal.modified_by = user
        locked_journal.save(
            update_fields = [ 'modified_by',
                              'modified_datetime',
                              'title',
                              'description',
                              'reference_image' ]
        )

        return len( entries_to_create )
