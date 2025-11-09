"""
Journal service layer for business logic.
"""
from django.contrib.auth import get_user_model

from tt.apps.common.html_sanitizer import sanitize_rich_text_html
from tt.apps.images.models import TripImage
from .enums import ImagePickerScope
from .utils import get_entry_date_boundaries

User = get_user_model()


class JournalImagePickerService:
    """Service for journal image picker operations."""

    @staticmethod
    def get_accessible_images_for_image_picker(trip, user, date, timezone, scope=ImagePickerScope.DEFAULT):
        """
        Get images accessible for journal image picker, ordered chronologically.

        Returns all images for the specified date in chronological order by datetime_utc.
        This is the single source of truth for image picker queries.

        Phase 1: All filtering is done client-side. The scope parameter is accepted
        but always returns all images regardless of value.

        Args:
            trip: Trip instance
            user: User instance for permission checking
            date: Date to fetch images for (date object)
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
