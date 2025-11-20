import uuid
from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password
from django.db import models

from tt.apps.common.model_fields import LabeledEnumField
from tt.apps.trips.models import Trip
from tt.apps.notebook.models import NotebookEntry
from tt.apps.images.models import TripImage

from .enums import JournalVisibility
from . import managers


class Journal(models.Model):
    """
    Container for published trip journal with visibility controls.

    Database supports multiple journals per trip for future flexibility.
    MVP will create/use a single journal per trip, but the schema allows
    expansion for future use cases (e.g., different perspectives, time periods).
    """
    objects = managers.JournalManager()

    # UUID for public URL access (non-guessable)
    uuid = models.UUIDField(
        default = uuid.uuid4,
        unique = True,
        editable = False,
    )

    # Many-to-one relationship with Trip (allows multiple journals per trip)
    trip = models.ForeignKey(
        Trip,
        on_delete = models.CASCADE,
        related_name = 'journals',
    )

    # Content
    title = models.CharField(max_length = 200)
    description = models.TextField(blank = True)
    timezone = models.CharField(
        max_length = 63,
        default = 'UTC',
        help_text = 'Timezone for journal entries (pytz timezone name)',
    )

    # Visibility settings for journal web view
    visibility = LabeledEnumField(
        JournalVisibility,
        'Visibility',
    )
    _password = models.CharField(
        max_length = 128,
        null = True,
        blank = True,
        db_column = 'password',
        help_text = 'Hashed password for PROTECTED visibility mode',
    )

    # Timestamps and tracking
    created_datetime = models.DateTimeField(auto_now_add = True)
    modified_datetime = models.DateTimeField(auto_now = True)
    modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete = models.SET_NULL,
        null = True,
        blank = True,
        related_name = 'modified_journals',
    )

    def __str__(self):
        return f"{self.title} (Journal for {self.trip.title})"

    class Meta:
        verbose_name = 'Journal'
        verbose_name_plural = 'Journals'
        ordering = ['-created_datetime']

    def set_password(self, raw_password):
        """Set the password using Django's password hashing."""
        if raw_password:
            self._password = make_password(raw_password)
        else:
            self._password = None

    def check_password(self, raw_password):
        """
        Check if the provided password matches the stored hashed password.
        Returns True if password matches, False otherwise.
        """
        if not self._password:
            return False
        return check_password(raw_password, self._password)

    @property
    def has_password(self):
        """Check if a password is set for this journal."""
        return bool(self._password)


class JournalEntry(models.Model):
    """
    Individual journal entry for a specific date with markdown text.
    One entry per date per journal.
    """
    objects = managers.JournalEntryManager()

    # Relationship to journal
    journal = models.ForeignKey(
        Journal,
        on_delete = models.CASCADE,
        related_name = 'entries',
    )

    # Reference image for table of contents display
    reference_image = models.ForeignKey(
        TripImage,
        on_delete = models.SET_NULL,
        null = True,
        blank = True,
        related_name = 'journal_entries_as_reference',
    )

    # Date and timezone
    date = models.DateField()
    timezone = models.CharField(
        max_length = 63,
        default = 'UTC',
        help_text = 'Timezone for this entry (pytz timezone name)',
    )

    # Content
    title = models.CharField(max_length = 200, blank = True)
    text = models.TextField(
        blank = True,
        help_text = 'HTML formatted journal entry text (sanitized on save)',
    )

    # Source tracking (for seeding from notebook)
    source_notebook_entry = models.ForeignKey(
        NotebookEntry,
        on_delete = models.SET_NULL,
        null = True,
        blank = True,
        related_name = 'journal_entries',
    )
    source_notebook_version = models.IntegerField(
        null = True,
        blank = True,
        help_text = 'Version of source notebook entry when last synced',
    )

    # Version control for optimistic locking
    edit_version = models.IntegerField(default = 1, editable = False)

    # Timestamps and tracking
    created_datetime = models.DateTimeField(auto_now_add = True)
    modified_datetime = models.DateTimeField(auto_now = True)
    modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete = models.SET_NULL,
        null = True,
        blank = True,
        related_name = 'modified_journal_entries',
        editable = False,
    )

    @property
    def is_synced_with_source(self) -> bool:
        """Check if journal entry is in sync with source notebook entry."""
        if not self.source_notebook_entry:
            return True  # No source, nothing to sync
        return bool( self.source_notebook_version == self.source_notebook_entry.edit_version )

    @property
    def has_source_notebook_changed(self) -> bool:
        """Check if the source notebook entry has changed since this journal entry was created."""
        return bool(bool(self.source_notebook_entry) and not self.is_synced_with_source)

    def save(self, *args, **kwargs):
        """Override save to auto-generate title from date if empty."""
        if not self.title:
            # Ensure date is a date object (Django may pass string initially)
            from datetime import date as date_class
            if isinstance(self.date, str):
                date_obj = date_class.fromisoformat(self.date)
            else:
                date_obj = self.date
            self.title = date_obj.strftime('%A, %B %d, %Y')
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.journal.title} - {self.date}"

    class Meta:
        verbose_name = 'Journal Entry'
        verbose_name_plural = 'Journal Entries'
        ordering = ['date']
        unique_together = [('journal', 'date')]
