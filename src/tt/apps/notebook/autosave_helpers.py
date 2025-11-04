"""
Helper classes for notebook entry auto-save operations.

This module provides encapsulated business logic for handling
notebook entry auto-save, including version conflict detection,
date validation, diff generation, and atomic updates.
"""
import difflib
import html
import json
import logging
from dataclasses import dataclass
from datetime import date as date_class, datetime
from typing import Optional, Tuple

from django.contrib.auth import get_user_model
from django.db.models import F
from django.http import HttpRequest, JsonResponse
from django.template.loader import render_to_string

from tt.apps.common import antinode

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
    """Helper for generating visual diffs between notebook versions."""

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
        # Split texts into lines for difflib (preserving line endings)
        server_lines = server_text.splitlines(keepends=True)
        client_lines = client_text.splitlines(keepends=True)

        # Generate unified diff
        diff_lines = difflib.unified_diff(
            server_lines,
            client_lines,
            fromfile='Server Version (Latest)',
            tofile='Your Changes',
            lineterm='',
            n=3  # 3 lines of context (standard)
        )

        # Convert to list and check if there are any differences
        diff_list = list(diff_lines)
        if not diff_list:
            return '<div class="diff-no-changes">No differences detected</div>'

        # Build HTML with proper styling
        html_parts = ['<div class="unified-diff">']

        for line in diff_list:
            # Escape HTML to prevent XSS
            escaped_line = html.escape(line)

            # Apply styling based on line prefix
            if line.startswith('---') or line.startswith('+++'):
                # File headers
                html_parts.append(f'<div class="diff-header">{escaped_line}</div>')
            elif line.startswith('@@'):
                # Hunk headers (line number ranges)
                html_parts.append(f'<div class="diff-hunk">{escaped_line}</div>')
            elif line.startswith('-'):
                # Deleted lines (in server version, not in client)
                html_parts.append(f'<div class="diff-delete">{escaped_line}</div>')
            elif line.startswith('+'):
                # Added lines (in client, not in server)
                html_parts.append(f'<div class="diff-add">{escaped_line}</div>')
            else:
                # Context lines (unchanged)
                html_parts.append(f'<div class="diff-context">{escaped_line}</div>')

        html_parts.append('</div>')
        return ''.join(html_parts)


class NotebookConflictHelper:
    """Helper for handling edit conflicts in notebook entries."""

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
        if entry.modified_by:
            modified_by_name = entry.modified_by.get_full_name()
        else:
            modified_by_name = 'another user'

        logger.info(
            f'Version conflict for entry {entry.pk} (trip {entry.trip.pk}): '
            f'client version mismatch, server={entry.edit_version}, '
            f'modified_by={modified_by_name}'
        )

        # Generate unified diff HTML for modal display
        diff_html = NotebookDiffHelper.generate_unified_diff_html(
            server_text = entry.text,
            client_text = client_text
        )

        # Render modal template
        modal_html = render_to_string(
            'notebook/modals/edit_conflict.html',
            {
                'modified_by_name': modified_by_name,
                'modified_at_datetime': entry.modified_datetime,
                'diff_html': diff_html,
            },
            request=request
        )

        # Return modal HTML for frontend display
        return antinode.http_response(
            {
                'modal': modal_html,
                'server_version': entry.edit_version,
            },
            status=409
        )


class NotebookAutoSaveHelper:
    """Helper for notebook entry auto-save operations."""

    @classmethod
    def parse_autosave_request( cls,
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
            text=text,
            new_date=new_date,
            client_version=client_version
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
        entry.text = text
        entry.modified_by = user
        update_fields = ['text', 'edit_version', 'modified_by', 'modified_datetime']

        if new_date:
            entry.date = new_date
            update_fields.append('date')

        # Use F() expression for atomic increment to prevent race conditions
        entry.edit_version = F('edit_version') + 1
        entry.save(update_fields=update_fields)

        # Refresh to get the actual version value (F() expressions don't update in-memory)
        entry.refresh_from_db(fields=['edit_version', 'modified_datetime'])

        return entry
