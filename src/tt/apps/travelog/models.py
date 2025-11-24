from django.conf import settings
from django.db import models

from tt.apps.journal.models import Journal, JournalEntry, JournalContent, JournalEntryContent

from . import managers


class Travelog( JournalContent ):
    """
    Published version of a Journal - immutable snapshot.

    Each Travelog represents a complete published snapshot of a journal at a specific point in time.
    Multiple versions can exist for a single journal, but only one can be marked as "current" (publicly
    visible).
    """

    objects = managers.TravelogManager()

    # Source & Version Management
    journal = models.ForeignKey(
        Journal,
        on_delete = models.CASCADE,
        related_name = 'travelogs',
    )
    version_number = models.IntegerField()

    is_current = models.BooleanField(
        default = False,
    )

    # Publication Metadata
    published_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete = models.SET_NULL,
        null = True,
        blank = True,
        related_name = 'published_travelogs',
        editable = False,
    )
    published_datetime = models.DateTimeField(
        auto_now_add = True,
    )

    class Meta:
        verbose_name = 'Travelog'
        verbose_name_plural = 'Travelogs'
        ordering = ['-version_number']
        unique_together = [('journal', 'version_number')]

    def get_entries(self):
        return self.entries.all()

    def __str__(self):
        current_indicator = ' [CURRENT]' if self.is_current else ''
        return f"{self.title} (v{self.version_number}){current_indicator}"


class TravelogEntry( JournalEntryContent ):
    """
    Published version of a JournalEntry - immutable snapshot.

    Each TravelogEntry represents an immutable snapshot of a journal entry's content
    at the time of publication. The snapshot preserves the exact state including all
    content, formatting, and metadata.
    """

    objects = managers.TravelogEntryManager()

    # Parent Publication & Source
    travelog = models.ForeignKey(
        Travelog,
        on_delete = models.CASCADE,
        related_name = 'entries',
    )
    source_entry = models.ForeignKey(
        JournalEntry,
        on_delete = models.SET_NULL,
        null = True,
        blank = True,
        related_name = 'travelog_snapshots',
    )

    class Meta:
        verbose_name = 'Travelog Entry'
        verbose_name_plural = 'Travelog Entries'
        ordering = ['date']

    def __str__(self):
        return f"{self.title} ({self.date})"
