from abc import abstractmethod
from datetime import date as date_class
import uuid
from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password
from django.db import models

from tt.apps.common.model_fields import LabeledEnumField
from tt.apps.common.utils import is_blank
from tt.apps.trips.models import Trip
from tt.apps.images.models import TripImage

from .enums import JournalVisibility, JournalTheme
from . import managers


class JournalContent( models.Model ):
    """
    Abstract base for journal-like containers (e.g., Journal and Travelog).
    Defines the common interface needed for unified content rendering.
    """

    uuid = models.UUIDField(
        default = uuid.uuid4,
        editable = False,
        unique = True,
    )
    title = models.CharField(
        max_length = 200,
    )
    description = models.TextField(
        blank = True,
    )
    reference_image = models.ForeignKey(
        TripImage,
        on_delete = models.SET_NULL,
        null = True,
        blank = True,
        related_name = '%(class)s_references',
    )

    class Meta:
        abstract = True
        
    @abstractmethod
    def get_entries(self):
        """
        Return queryset of entries for rendering.
          
        Returns:
            QuerySet of instances (e.g., JournalEntry, TravelogEntry)
        """
        raise NotImplementedError

    def __str__(self):
        return self.title

    
class JournalEntryContent(models.Model):
    """
    Abstract base for journal entry content (JournalEntry and TravelogEntry).
      Defines the common interface needed for unified entry rendering.
      """

    uuid = models.UUIDField(
        default = uuid.uuid4,
        unique = True,
        editable = False,
    )    
    date = models.DateField()
    timezone = models.CharField(
        max_length = 63,
        default = 'UTC',
        help_text = 'Timezone for this entry (pytz timezone name)',
    )

    # Content
    title = models.CharField(
        max_length = 200,
        blank = True,
    )
    text = models.TextField(
        blank = True,
        help_text = 'HTML formatted journal entry text (sanitized on save)',
    )
    reference_image = models.ForeignKey(
        TripImage,
        on_delete = models.SET_NULL,
        null = True,
        blank = True,
        related_name = '%(class)s_references',
    )
   
    class Meta:
        abstract = True
        
    def __str__(self):
        return f"{self.title} ({self.date})"


class Journal( JournalContent ):
    """
    Database supports multiple journals per trip for future flexibility.
    MVP will create/use a single journal per trip, but the schema allows
    expansion for future use cases (e.g., different perspectives, time periods).
    """
    objects = managers.JournalManager()

    trip = models.ForeignKey(
        Trip,
        on_delete = models.CASCADE,
        related_name = 'journals',
    )

    timezone = models.CharField(
        max_length = 63,
        default = 'UTC',
        help_text = 'Timezone for journal entries (pytz timezone name)',
    )

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
    password_version = models.IntegerField(
        default = 1,
        help_text = 'Version number incremented on each password change for session invalidation',
    )

    theme = LabeledEnumField(
        JournalTheme,
        'Travelog Theme',
        help_text = 'Visual color theme for published travelog pages',
    )

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

    def get_entries(self):
        return self.entries.all()

    def set_password( self, raw_password ):
        if raw_password:
            self._password = make_password( raw_password )
            # Increment version to invalidate all existing sessions
            self.password_version = ( self.password_version or 0 ) + 1
        else:
            self._password = None

    def check_password(self, raw_password):
        if not self._password:
            return False
        return check_password( raw_password, self._password )

    @property
    def has_password(self):
        return not is_blank( self._password )

    @property
    def is_misconfigured_protected(self):
        """
        Returns True if journal is set to PROTECTED visibility but has no password.
        This is a misconfiguration - PROTECTED journals should always have a password.
        When this occurs, the journal behaves as PRIVATE in authorization logic.
        """
        return bool(( self.visibility == JournalVisibility.PROTECTED )
                    and not self.has_password )


class JournalEntry( JournalEntryContent ):

    objects = managers.JournalEntryManager()

    journal = models.ForeignKey(
        Journal,
        on_delete = models.CASCADE,
        related_name = 'entries',
    )

    # Version control for optimistic locking
    edit_version = models.IntegerField(default = 1, editable = False)

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

    @classmethod
    def generate_default_title( cls, date_obj ) -> str:
        """
        Generate the default title for a given date.

        This is the single source of truth for default title generation.
        Used by save() for new entries and by autosave helpers for
        detecting when titles should be auto-regenerated on date changes.
        """
        if isinstance(date_obj, str):
            date_obj = date_class.fromisoformat(date_obj)
        return date_obj.strftime('%A, %B %d, %Y')

    def save(self, *args, **kwargs):
        """Override save to auto-generate title from date if empty."""
        if not self.title:
            self.title = self.generate_default_title(self.date)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.journal.title} - {self.date}"

    class Meta:
        verbose_name = 'Journal Entry'
        verbose_name_plural = 'Journal Entries'
        ordering = ['date']
        unique_together = [('journal', 'date')]
