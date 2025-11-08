"""
Helper classes for notebook entry auto-save operations.

This module provides encapsulated business logic for handling
notebook entry auto-save, including version conflict detection,
date validation, and atomic updates.

Note: This module now uses shared utilities from tt.apps.common.autosave_helpers
for common auto-save functionality.
"""
import json
import logging
from dataclasses import dataclass
from datetime import date as date_class, datetime
from typing import Optional, Tuple

from django.contrib.auth import get_user_model
from django.http import HttpRequest, JsonResponse

from tt.apps.common.autosave_helpers import AutoSaveHelper as SharedAutoSaveHelper, ConflictHelper, DiffHelper

from .models import NotebookEntry

User = get_user_model()
logger = logging.getLogger(__name__)


@dataclass
class AutoSaveRequest:
    """Parsed and validated auto-save request data."""
    text            : str
    new_date        : Optional[date_class]
    client_version  : Optional[int]


class NotebookDiffHelper:
    """
    Helper for generating visual diffs between notebook versions.

    Wrapper around shared DiffHelper for backward compatibility.
    """

    @classmethod
    def generate_unified_diff_html( cls,
                                    server_text  : str,
                                    client_text  : str ) -> str:
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


class NotebookConflictHelper:
    """
    Helper for handling edit conflicts in notebook entries.

    Wrapper around shared ConflictHelper for backward compatibility.
    """

    @classmethod
    def build_conflict_response( cls,
                                 request      : HttpRequest,
                                 entry        : NotebookEntry,
                                 client_text  : str ) -> JsonResponse:
        """
        Build conflict response with diff modal for version conflicts.

        Args:
            request: Django request object
            entry: Locked notebook entry with conflicting version
            client_text: Text from client that caused conflict

        Returns:
            JsonResponse with modal HTML and server version (status 409)
        """
        return ConflictHelper.build_conflict_response(
            request=request,
            entry=entry,
            client_text=client_text,
        )


class NotebookAutoSaveHelper:
    """Helper for notebook entry auto-save operations."""

    @classmethod
    def parse_autosave_request(
            cls,
            request_body : bytes ) -> Tuple[Optional[AutoSaveRequest], Optional[JsonResponse]]:
        """
        Parse and validate auto-save request JSON.

        Args:
            request_body: Raw request body bytes

        Returns:
            Tuple of (AutoSaveRequest, None) on success, or (None, error_response) on failure
        """
        try:
            data = json.loads(request_body)
            text = data.get('text', '')
            date_str = data.get('date')
            client_version = data.get('version')
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

        return AutoSaveRequest(
            text = text,
            new_date = new_date,
            client_version = client_version
        ), None

    @classmethod
    def validate_date_uniqueness( cls,
                                  entry     : NotebookEntry,
                                  new_date  : date_class ) -> Optional[JsonResponse]:
        """
        Validate that new date doesn't conflict with existing entries.

        Args:
            entry: Entry being updated
            new_date: Proposed new date

        Returns:
            JsonResponse with error if conflict exists, None if valid
        """
        if new_date and new_date != entry.date:
            existing = NotebookEntry.objects.filter(
                trip=entry.trip,
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
                                 entry     : NotebookEntry,
                                 text      : str,
                                 user      : User,
                                 new_date  : Optional[date_class] = None ) -> NotebookEntry:
        """
        Update notebook entry with atomic version increment.

        Args:
            entry: Locked entry to update
            text: New text content
            user: User making the modification
            new_date: Optional new date for entry

        Returns:
            Updated entry with refreshed version
        """
        extra_updates = {}
        if new_date:
            extra_updates['date'] = new_date

        return SharedAutoSaveHelper.update_entry_atomically(
            entry=entry,
            text=text,
            user=user,
            extra_updates=extra_updates if extra_updates else None
        )
