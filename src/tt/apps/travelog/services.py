from django.contrib.auth.models import User as UserType
from django.db import transaction

from tt.apps.journal.models import Journal
from .models import Travelog, TravelogEntry


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
