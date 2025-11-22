from django.contrib.auth.models import User as UserType
from django.db import transaction
from django.http import Http404

from tt.apps.journal.models import Journal, JournalContent
from .models import Travelog, TravelogEntry
from .transient_models import TravelogPageContext
from .enums import ContentType


class PublishingError(Exception):
    """Exception raised when publishing operations fail."""
    pass


class PublishingService:

    @classmethod
    @transaction.atomic
    def publish_journal( cls, journal : Journal, user : UserType ) -> Travelog:
        """
        Publish a journal as a new Travelog version.

        Creates an immutable snapshot of the journal and all its entries.
        Manages version numbering and ensures only one version is marked as current.
        """
        journal_entries = journal.entries.all()
        if not journal_entries.exists():
            raise ValueError("Cannot publish journal with no entries")

        # Lock the journal row for this transaction to prevent race conditions
        locked_journal = Journal.objects.select_for_update().get( pk = journal.pk )

        next_version = Travelog.objects.get_next_version_number( locked_journal )

        Travelog.objects.filter(
            journal = locked_journal,
            is_current = True
        ).update( is_current = False )

        travelog = Travelog.objects.create(
            journal = locked_journal,
            version_number = next_version,
            is_current = True,
            published_by = user,

            # Copy journal content
            title = locked_journal.title,
            description = locked_journal.description,
        )

        for journal_entry in journal_entries:
            TravelogEntry.objects.create(
                travelog = travelog,

                # Copy entry content
                date = journal_entry.date,
                timezone = journal_entry.timezone,
                title = journal_entry.title,
                text = journal_entry.text,
                reference_image = journal_entry.reference_image,
            )

        return travelog

    @staticmethod
    @transaction.atomic
    def set_as_current( journal: Journal, travelog: Travelog ) -> Travelog:
        """
        Set a specific travelog version as the current published version.

        This operation only changes which version is publicly visible.
        It does not affect the journal's working entries.

        Raises:
            PublishingError: If validation fails
        """
        if travelog.journal_id != journal.id:
            raise PublishingError(
                "Cannot set as current: Travelog does not belong to this journal"
            )

        if travelog.is_current:
            raise PublishingError(
                "This version is already the current published version"
            )

        Travelog.objects.filter( journal=journal ).update( is_current = False )
        travelog.is_current = True
        travelog.save(update_fields=['is_current'])

        return travelog


class ContentResolutionService:

    @staticmethod
    def resolve_content(travelog_page_context: TravelogPageContext) -> JournalContent:
        """
        Returns:
            JournalContent instance - either Journal (for DRAFT) or Travelog (for VIEW/VERSION)

        Raises:
            Http404: If requested version doesn't exist
        """
        if travelog_page_context.content_type == ContentType.DRAFT:
            return travelog_page_context.journal

        elif travelog_page_context.content_type == ContentType.VIEW:
            travelog = Travelog.objects.get_current(travelog_page_context.journal)
            if not travelog:
                raise Http404()
            return travelog

        elif travelog_page_context.content_type == ContentType.VERSION:
            travelog = Travelog.objects.get_version(
                travelog_page_context.journal,
                travelog_page_context.version_number
            )
            if not travelog:
                raise Http404()
            return travelog

        else:
            # This should never happen with proper enum handling
            raise ValueError(f"Unknown content type: {travelog_page_context.content_type}")

