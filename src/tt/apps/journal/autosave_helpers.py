"""
Helper classes for journal entry auto-save operations.

This module provides business logic for handling journal entry auto-save,
including HTML sanitization, version conflict detection, date validation,
and atomic updates.
"""
import json
import logging
from dataclasses import dataclass
from datetime import date as date_class, datetime
from typing import Optional, Tuple
from uuid import UUID

from django.contrib.auth import get_user_model
from django.db import IntegrityError, DatabaseError
from django.http import HttpRequest, JsonResponse
from django.template.loader import render_to_string

from tt.apps.common.autosave_helpers import AutoSaveHelper as SharedAutoSaveHelper, ConflictHelper
from tt.apps.common.html_sanitizer import sanitize_rich_text_html
from tt.apps.images.models import TripImage

from .models import JournalEntry


User = get_user_model()
logger = logging.getLogger(__name__)


@dataclass
class JournalAutoSaveRequest:
    """Parsed and validated auto-save request data for journal entries."""
    text                     : str
    client_version           : Optional[int]
    new_date                 : Optional[date_class]
    new_title                : Optional[str]
    new_timezone             : Optional[str]
    new_reference_image_uuid : Optional[str]


@dataclass
class DateChangeResult:
    """Result of processing date change with title auto-generation."""
    date_changed    : bool
    title_updated   : bool
    final_title     : Optional[str]
    final_date      : Optional[date_class]


class DateChangeOrchestrator:
    """
    Handles date change detection and title auto-regeneration business rules.

    Business Rule: When the date of a journal entry changes, if the current title
    matches the default pattern for the OLD date, auto-regenerate the title for
    the new date. This provides a seamless experience when users change dates
    but haven't customized the title.
    """

    @classmethod
    def process_date_change( cls,
                             entry     : 'JournalEntry',
                             new_date  : Optional[date_class],
                             new_title : Optional[str]) -> DateChangeResult:
        """
        Process date change with title auto-regeneration business rules.

        Args:
            entry: Current journal entry being edited
            new_date: Requested new date (None = no date change requested)
            new_title: Requested new title (None = no title change requested)

        Returns:
            DateChangeResult with computed values for date_changed, title_updated,
            final_title, and final_date
        """
        original_date = entry.date
        original_title = entry.title

        # Default to no changes
        date_changed = False
        title_updated = False
        final_title = new_title
        final_date = None

        # Process date change
        if new_date and ( new_date != original_date ):
            date_changed = True
            final_date = new_date

            # Auto-regenerate title if it matches old date's default pattern
            sent_title = new_title or original_title
            if JournalAutoSaveHelper.is_default_title_for_date(sent_title, original_date):
                final_title = JournalEntry.generate_default_title(new_date)
                title_updated = True

        return DateChangeResult(
            date_changed = date_changed,
            title_updated = title_updated,
            final_title = final_title,
            final_date = final_date,
        )


class AutosaveResponseBuilder:
    """
    Builds JSON responses for autosave operations.

    Centralizes response format knowledge and handles optional modal rendering
    for date-changed notifications.
    """

    @classmethod
    def build_success_response( cls,
                                request         : HttpRequest,
                                updated_entry   : 'JournalEntry',
                                date_changed    : bool,
                                title_updated   : bool) -> JsonResponse:
        """
        Build successful autosave JSON response with optional modal.

        Args:
            request: HTTP request for template rendering context
            updated_entry: Successfully updated journal entry
            date_changed: Whether date was modified during save
            title_updated: Whether title was auto-regenerated

        Returns:
            JsonResponse with success status and metadata
        """
        response_data = {
            'status': 'success',
            'version': updated_entry.edit_version,
            'modified_datetime': updated_entry.modified_datetime.isoformat(),
            'date_changed': date_changed,
            'title_updated': title_updated,
        }

        # Include date change notification modal
        if date_changed:
            response_data['modal'] = render_to_string(
                'journal/modals/date_changed.html',
                {},
                request = request
            )

        return JsonResponse(response_data)


class ExceptionResponseBuilder:
    """
    Centralized exception handling for autosave operations.

    Converts exceptions to appropriate JSON error responses with consistent
    logging and status codes.
    """

    @classmethod
    def handle_autosave_exception( cls,
                                   exception : Exception,
                                   entry     : 'JournalEntry') -> JsonResponse:
        """
        Convert autosave exception to appropriate JSON error response.

        Args:
            exception: Exception that occurred during autosave
            entry: Journal entry being saved (for logging context)

        Returns:
            JsonResponse with appropriate error status and message
        """
        if isinstance(exception, JournalEntry.DoesNotExist):
            logger.error(f'Entry {entry.pk} not found during atomic update')
            return JsonResponse(
                {'status': 'error', 'message': 'Entry not found'},
                status = 404
            )
        elif isinstance(exception, IntegrityError):
            logger.warning(f'Integrity constraint violation for entry {entry.pk}: {exception}')
            return JsonResponse(
                {'status': 'error', 'message': 'Unable to save - entry date conflicts with another entry'},
                status = 409
            )
        elif isinstance(exception, DatabaseError):
            logger.error(f'Database error auto-saving journal entry {entry.pk}: {exception}')
            return JsonResponse(
                {'status': 'error', 'message': 'Database error occurred'},
                status = 500
            )
        else:
            # Unexpected exception - log full details
            logger.error(f'Unexpected error in autosave for entry {entry.pk}: {exception}', exc_info=True)
            return JsonResponse(
                {'status': 'error', 'message': 'An unexpected error occurred'},
                status = 500
            )


class JournalConflictHelper:
    """
    Helper for handling edit conflicts in journal entries.

    Wrapper around shared ConflictHelper.
    """

    @classmethod
    def build_conflict_response(cls,
                                request      : HttpRequest,
                                entry        : JournalEntry,
                                client_text  : str) -> JsonResponse:
        """
        Returns:
            JsonResponse with modal HTML and server version (status 409)
        """
        return ConflictHelper.build_conflict_response(
            request = request,
            entry = entry,
            client_text = client_text,
        )


class JournalAutoSaveHelper:
    """Helper for journal entry auto-save operations with HTML sanitization."""

    @classmethod
    def is_default_title_for_date( cls, title: str, date_obj: date_class ) -> bool:
        return bool( title == JournalEntry.generate_default_title(date_obj) )

    @classmethod
    def parse_autosave_request(
            cls,
            request_body: bytes) -> Tuple[Optional[JournalAutoSaveRequest], Optional[JsonResponse]]:
        try:
            data = json.loads(request_body)
            text = data.get('text', '')
            client_version = data.get('version')
            date_str = data.get('new_date')
            title = data.get('new_title')
            timezone = data.get('new_timezone')
            reference_image_uuid = data.get('reference_image_uuid')
        except json.JSONDecodeError:
            logger.warning('Invalid JSON in auto-save request')
            return None, JsonResponse(
                {'status': 'error', 'message': 'Invalid JSON'},
                status=400
            )

        new_date = None
        if date_str:
            try:
                new_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                logger.warning(f'Invalid date format: {date_str}')
                return None, JsonResponse(
                    {'status': 'error', 'message': 'Invalid date format'},
                    status=400
                )

        new_reference_image_uuid = None
        if reference_image_uuid is not None:
            if reference_image_uuid == '':
                # Empty string means clear reference image
                new_reference_image_uuid = ''
            else:
                try:
                    UUID(reference_image_uuid)
                    new_reference_image_uuid = reference_image_uuid
                except (ValueError, TypeError):
                    logger.warning(f'Invalid reference_image_uuid: {reference_image_uuid}')
                    return None, JsonResponse(
                        {'status': 'error', 'message': 'Invalid reference_image_uuid format'},
                        status=400
                    )

        return JournalAutoSaveRequest(
            text = text,
            client_version = client_version,
            new_date = new_date,
            new_title = title,
            new_timezone = timezone,
            new_reference_image_uuid = new_reference_image_uuid
        ), None

    @classmethod
    def sanitize_html_content(cls, html_content: str) -> str:
        try:
            return sanitize_rich_text_html(html_content)
        except Exception as e:
            logger.error(f'Error sanitizing HTML: {e}')
            # On error, return empty string for safety
            return ''

    @classmethod
    def validate_date_uniqueness( cls,
                                  entry     : JournalEntry,
                                  new_date  : date_class) -> Optional[JsonResponse]:
        if new_date and ( new_date != entry.date ):
            # Prevent date changes on special entries (prologue/epilogue)
            if entry.is_special_entry:
                return JsonResponse(
                    {
                        'status': 'error',
                        'message': f'Cannot change the date of the {entry.page_type.label}.'
                    },
                    status=400
                )

            # Check for duplicate dates
            existing_entry = JournalEntry.objects.filter(
                journal=entry.journal,
                date=new_date
            ).exclude(pk=entry.pk).first()

            if existing_entry:
                if existing_entry.is_special_entry:
                    error_message = f'The {existing_entry.page_type.label} already exists.'
                else:
                    error_message = f'An entry for {existing_entry.display_date_medium} already exists.'

                return JsonResponse(
                    {
                        'status': 'error',
                        'message': error_message
                    },
                    status=400
                )
        return None

    @classmethod
    def update_entry_atomically( cls,
                                 entry                    : JournalEntry,
                                 text                     : str,
                                 user                     : User,
                                 new_date                 : Optional[date_class] = None,
                                 new_title                : Optional[str]        = None,
                                 new_timezone             : Optional[str]        = None,
                                 new_reference_image_uuid : Optional[str]        = None) -> JournalEntry:
        extra_updates = {}

        if new_date is not None:
            extra_updates['date'] = new_date

        if new_title is not None:
            extra_updates['title'] = new_title

        if new_timezone is not None:
            extra_updates['timezone'] = new_timezone

        if new_reference_image_uuid is not None:
            if new_reference_image_uuid == '':
                extra_updates['reference_image_id'] = None
            else:
                try:
                    trip_image = TripImage.objects.get(uuid=new_reference_image_uuid)
                    extra_updates['reference_image_id'] = trip_image.pk
                except TripImage.DoesNotExist:
                    logger.warning(f'TripImage not found for UUID: {new_reference_image_uuid}')
                    # Skip update - don't change reference_image

        return SharedAutoSaveHelper.update_entry_atomically(
            entry = entry,
            text = text,
            user = user,
            extra_updates = extra_updates if extra_updates else None
        )
