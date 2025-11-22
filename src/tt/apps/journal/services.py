"""
Journal service layer for business logic.
"""
from datetime import date as date_type

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import QuerySet

from tt.apps.common.html_sanitizer import sanitize_rich_text_html
from tt.apps.images.models import TripImage
from tt.apps.travelog.models import Travelog, TravelogEntry
from tt.apps.trips.models import Trip

from .enums import ImagePickerScope
from .models import Journal, JournalEntry
from .utils import get_entry_date_boundaries

User = get_user_model()


class RestoreError(Exception):
    """Exception raised when publishing operations fail."""
    pass


class JournalImagePickerService:
    """Service for journal image picker operations."""

    @staticmethod
    def get_accessible_images_for_image_picker(
        trip     : Trip,
        user     : User,
        date     : date_type,
        timezone : str,
        scope    : ImagePickerScope = ImagePickerScope.DEFAULT
    ) -> QuerySet:
        """
        Get images accessible for journal image picker, ordered chronologically.

        Returns all images for the specified date in chronological order by datetime_utc.
        This is the single source of truth for image picker queries.

        Phase 1: All filtering is done client-side. The scope parameter is accepted
        but always returns all images regardless of value.

        Args:
            trip: Trip instance
            user: User instance for permission checking
            date: Date to fetch images for (datetime.date object)
            timezone: Timezone string for date boundary calculation
            scope: ImagePickerScope enum value (default: ImagePickerScope.DEFAULT)

        Returns:
            QuerySet of TripImage objects ordered by datetime_utc
        """
        start_dt, end_dt = get_entry_date_boundaries(date, timezone)
        images = TripImage.objects.accessible_to_user_in_trip_for_date_range(
            user=user,
            trip=trip,
            start_datetime=start_dt,
            end_datetime=end_dt,
        ).order_by('datetime_utc')

        return images


class JournalEntrySeederService:
    """Service for seeding JournalEntry instances from NotebookEntry data."""

    @staticmethod
    def create_from_notebook_entry(notebook_entry, journal, user):
        """
        Create a JournalEntry seeded from a NotebookEntry with HTML conversion.

        Converts plain text from NotebookEntry to properly formatted HTML with
        paragraph tags, then sanitizes and creates the JournalEntry.

        Args:
            notebook_entry: Source NotebookEntry instance to convert
            journal: Target Journal for the new entry
            user: User creating the entry

        Returns:
            Created JournalEntry instance with converted and sanitized HTML content
        """
        from .models import JournalEntry

        # Convert plain text to HTML
        html_text = JournalEntrySeederService.convert_plain_text_to_html(
            notebook_entry.text
        )

        # Sanitize the HTML (safety layer)
        sanitized_html = sanitize_rich_text_html(html_text)

        # Create the journal entry
        return JournalEntry.objects.create(
            journal=journal,
            date=notebook_entry.date,
            timezone=journal.timezone,
            text=sanitized_html,
            source_notebook_entry=notebook_entry,
            source_notebook_version=notebook_entry.edit_version,
            modified_by=user,
        )

    @staticmethod
    def convert_plain_text_to_html(plain_text):
        """
        Convert plain text to HTML with paragraph tags.

        Each line becomes its own paragraph. Newlines define paragraph boundaries.
        Empty or whitespace-only lines are skipped.

        Whitespace handling:
        - Leading/trailing whitespace is stripped from each line
        - Multiple consecutive spaces within a line are collapsed to single space
        - Empty/whitespace-only lines are skipped (no empty paragraphs)

        Args:
            plain_text: Raw plain text string (may contain newlines)

        Returns:
            HTML string with <p> tags wrapping each line, or empty string
            if input is empty/whitespace-only

        Examples:
            "Hello"           → "<p>Hello</p>"
            "Line 1\nLine 2"  → "<p>Line 1</p><p>Line 2</p>"
            "P1\n\nP2"        → "<p>P1</p><p>P2</p>"
            ""                → ""
            "   "             → ""
        """
        if not plain_text or not plain_text.strip():
            return ''

        # Normalize line endings to \n
        normalized = plain_text.replace('\r\n', '\n').replace('\r', '\n')

        # Split into lines and process each
        lines = normalized.split('\n')
        paragraphs = []

        for line in lines:
            # Strip whitespace and normalize internal spaces
            stripped = line.strip()
            if stripped:  # Skip empty/whitespace-only lines
                # Collapse multiple spaces to single space
                normalized_line = ' '.join(stripped.split())
                paragraphs.append(normalized_line)

        # Wrap each line in <p> tags
        html_paragraphs = [f'<p>{p}</p>' for p in paragraphs]

        return ''.join(html_paragraphs)


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
        locked_journal.description = travelog.description
        locked_journal.modified_by = user
        locked_journal.save(
            update_fields = [ 'modified_by',
                              'modified_datetime',
                              'title',
                              'description' ]
        )

        return len( entries_to_create )
