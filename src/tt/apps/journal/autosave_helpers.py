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

from django.contrib.auth import get_user_model
from django.http import HttpRequest, JsonResponse

from tt.apps.common.autosave_helpers import AutoSaveHelper as SharedAutoSaveHelper, ConflictHelper, DiffHelper
from tt.apps.common.html_sanitizer import sanitize_rich_text_html

from .models import JournalEntry

User = get_user_model()
logger = logging.getLogger(__name__)


@dataclass
class JournalAutoSaveRequest:
    """Parsed and validated auto-save request data for journal entries."""
    text                   : str
    client_version         : Optional[int]
    new_date               : Optional[date_class]
    new_title              : Optional[str]
    new_timezone           : Optional[str]
    new_reference_image_id : Optional[int]


class JournalDiffHelper:
    """
    Helper for generating visual diffs between journal entry versions.

    Wrapper around shared DiffHelper for consistency.
    """

    @classmethod
    def generate_unified_diff_html(cls,
                                   server_text: str,
                                   client_text: str) -> str:
        """
        Generate HTML-formatted unified diff comparing server text to client text.

        Shows changes from server version (what's on server) to client version
        (what user was trying to save). Uses standard unified diff format.

        Args:
            server_text: Current text on server (latest version)
            client_text: Text from client that caused conflict

        Returns:
            HTML string with styled unified diff, ready for display
        """
        return DiffHelper.generate_unified_diff_html(server_text, client_text)


class JournalConflictHelper:
    """
    Helper for handling edit conflicts in journal entries.

    Wrapper around shared ConflictHelper.
    """

    @classmethod
    def build_conflict_response(cls,
                                request: HttpRequest,
                                entry: JournalEntry,
                                client_text: str) -> JsonResponse:
        """
        Build conflict response with diff modal for version conflicts.

        Args:
            request: Django request object
            entry: Locked journal entry with conflicting version
            client_text: Text from client that caused conflict

        Returns:
            JsonResponse with modal HTML and server version (status 409)
        """
        return ConflictHelper.build_conflict_response(
            request=request,
            entry=entry,
            client_text=client_text,
        )


class JournalAutoSaveHelper:
    """Helper for journal entry auto-save operations with HTML sanitization."""

    @classmethod
    def parse_autosave_request(
            cls,
            request_body: bytes) -> Tuple[Optional[JournalAutoSaveRequest], Optional[JsonResponse]]:
        """
        Parse and validate auto-save request JSON for journal entries.

        Args:
            request_body: Raw request body bytes

        Returns:
            Tuple of (JournalAutoSaveRequest, None) on success, or (None, error_response) on failure
        """
        try:
            data = json.loads(request_body)
            text = data.get('text', '')
            client_version = data.get('version')
            date_str = data.get('date')
            title = data.get('title')
            timezone = data.get('timezone')
            reference_image_id = data.get('reference_image_id')
        except json.JSONDecodeError:
            logger.warning('Invalid JSON in auto-save request')
            return None, JsonResponse(
                {'status': 'error', 'message': 'Invalid JSON'},
                status=400
            )

        # Parse date if provided
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

        # Parse reference_image_id if provided
        new_reference_image_id = None
        if reference_image_id is not None:
            try:
                new_reference_image_id = int(reference_image_id)
            except (ValueError, TypeError):
                logger.warning(f'Invalid reference_image_id: {reference_image_id}')
                return None, JsonResponse(
                    {'status': 'error', 'message': 'Invalid reference_image_id'},
                    status=400
                )

        return JournalAutoSaveRequest(
            text = text,
            client_version = client_version,
            new_date = new_date,
            new_title = title,
            new_timezone = timezone,
            new_reference_image_id = new_reference_image_id
        ), None

    @classmethod
    def sanitize_html_content(cls, html_content: str) -> str:
        """
        Sanitize HTML content for journal entries.

        Uses Bleach library to sanitize HTML with configured whitelist of
        allowed tags and attributes.

        Args:
            html_content: Raw HTML content from client

        Returns:
            Sanitized HTML content safe for storage and display
        """
        try:
            return sanitize_rich_text_html(html_content)
        except Exception as e:
            logger.error(f'Error sanitizing HTML: {e}')
            # On error, return empty string for safety
            return ''

    @classmethod
    def validate_date_uniqueness(cls,
                                 entry: JournalEntry,
                                 new_date: date_class) -> Optional[JsonResponse]:
        """
        Validate that new date doesn't conflict with existing entries.

        Args:
            entry: Entry being updated
            new_date: Proposed new date

        Returns:
            JsonResponse with error if conflict exists, None if valid
        """
        if new_date and new_date != entry.date:
            existing = JournalEntry.objects.filter(
                journal=entry.journal,
                date=new_date
            ).exclude(pk=entry.pk).exists()

            if existing:
                return JsonResponse(
                    {
                        'status': 'error',
                        'message': f'An entry for {new_date.strftime("%B %d, %Y")} already exists.'
                    },
                    status=400
                )
        return None

    @classmethod
    def update_entry_atomically( cls,
                                 entry                  : JournalEntry,
                                 text                   : str,
                                 user                   : User,
                                 new_date               : Optional[date_class] = None,
                                 new_title              : Optional[str]        = None,
                                 new_timezone           : Optional[str]        = None,
                                 new_reference_image_id : Optional[int]        = None) -> JournalEntry:
        """
        Update journal entry with atomic version increment.

        Note: HTML sanitization should be performed before calling this method.

        Args:
            entry: Locked entry to update
            text: New text content (should already be sanitized)
            user: User making the modification
            new_date: Optional new date for entry
            new_title: Optional new title for entry
            new_timezone: Optional new timezone for entry
            new_reference_image_id: Optional new reference image ID (use -1 to clear)

        Returns:
            Updated entry with refreshed version
        """
        extra_updates = {}

        if new_date:
            extra_updates['date'] = new_date

        if new_title is not None:
            extra_updates['title'] = new_title

        if new_timezone:
            extra_updates['timezone'] = new_timezone

        # Handle reference_image_id: -1 means clear the reference, None means no change
        if new_reference_image_id is not None:
            if new_reference_image_id == -1:
                extra_updates['reference_image_id'] = None
            else:
                extra_updates['reference_image_id'] = new_reference_image_id

        return SharedAutoSaveHelper.update_entry_atomically(
            entry = entry,
            text = text,
            user = user,
            extra_updates = extra_updates if extra_updates else None
        )
