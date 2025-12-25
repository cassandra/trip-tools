from typing import List

from django.contrib.auth import get_user_model
from django.db import transaction

from tt.apps.travelog.models import Travelog, TravelogEntry
from tt.apps.travelog.services import PublishingService

from .enums import JournalVisibility
from .forms import JournalVisibilityForm
from .models import Journal, JournalEntry

User = get_user_model()


class RestoreError(Exception):
    pass


class JournalPublishingService:

    @classmethod
    @transaction.atomic
    def publish_with_selections_and_visibility( cls,
                                                journal               : Journal,
                                                selected_entry_uuids  : List[str],
                                                visibility_form       : JournalVisibilityForm,
                                                user                  : User          ) -> Travelog:
        """
        Execute complete publishing workflow:
        1. Update entry selections (include_in_publish flags)
        2. Publish journal to travelog
        3. Apply visibility changes

        Raises:
            ValueError: If no entries selected or validation fails
        """
        cls._update_entry_selections(
            journal = journal,
            selected_entry_uuids = selected_entry_uuids,
        )
        travelog = PublishingService.publish_journal(
            journal = journal,
            user = user,
        )
        cls._apply_visibility_changes(
            journal = journal,
            visibility_form = visibility_form,
            user = user,
        )
        return travelog

    @classmethod
    def _update_entry_selections( cls,
                                  journal               : Journal,
                                  selected_entry_uuids  : List[str] ) -> int:
        """
        Update include_in_publish flags based on selection.

        Returns:
            Number of entries whose flags were changed
        """
        updated_count = 0
        for entry in journal.entries.all():
            should_include = str( entry.uuid ) in selected_entry_uuids
            if entry.include_in_publish != should_include:
                entry.include_in_publish = should_include
                entry.save( update_fields = ['include_in_publish'] )
                updated_count += 1
                continue

            continue

        return updated_count

    @classmethod
    def _apply_visibility_changes( cls,
                                   journal          : Journal,
                                   visibility_form  : JournalVisibilityForm,
                                   user             : User                  ) -> None:
        """
        Apply visibility and password changes from validated form.

        Note: Caller must ensure form.is_valid() before calling.
        """
        visibility_name = visibility_form.cleaned_data['visibility']
        visibility = JournalVisibility[visibility_name]

        journal.visibility = visibility

        if visibility_form.should_update_password():
            password = visibility_form.cleaned_data.get('password')
            journal.set_password( password )

        journal.modified_by = user
        journal.save()
        return


class JournalRestoreService:
    """Service for restoring journal working copy from a published travelog version."""

    @staticmethod
    @transaction.atomic
    def restore_from_version( journal   : Journal,
                              travelog  : Travelog,
                              user      : User     ) -> int:
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
        JournalEntry.objects.filter( journal = locked_journal ).delete()

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
            continue

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
