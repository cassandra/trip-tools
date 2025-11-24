"""
Reusable helper classes for auto-save operations across different entry types.

This module provides generic business logic for handling auto-save operations,
including version conflict detection, diff generation, and atomic updates.
"""
import difflib
import html
import json
import logging
from dataclasses import dataclass
from typing import Optional, Tuple, TypeVar

from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import F
from django.http import HttpRequest, JsonResponse
from django.template.loader import render_to_string

from tt.apps.common import antinode

User = get_user_model()
logger = logging.getLogger(__name__)

# Generic type variable for model instances
T = TypeVar('T', bound=models.Model)


@dataclass
class AutoSaveRequest:
    """Parsed and validated auto-save request data."""
    text           : str
    client_version : Optional[int]
    extra_fields   : dict


class DiffHelper:
    """Helper for generating visual diffs between text versions."""

    @classmethod
    def generate_unified_diff_html( cls,
                                    server_text  : str,
                                    client_text  : str) -> str:
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


class ConflictHelper:
    """Helper for handling edit conflicts in entries with version control."""

    @classmethod
    def build_conflict_response(
            cls,
            request         : HttpRequest,
            entry           : models.Model,
            client_text     : str,
            modal_template  : str    = 'common/modals/edit_conflict.html' ) -> JsonResponse:
        """
        Build conflict response with diff modal for version conflicts.

        Args:
            request: Django request object
            entry: Locked entry with conflicting version 
                   (must have text, edit_version, modified_by, modified_datetime)
            client_text: Text from client that caused conflict
            modal_template: Path to modal template (if override needed)

        Returns:
            JsonResponse with modal HTML and server version (status 409)
        """
        if hasattr(entry, 'modified_by') and entry.modified_by:
            modified_by_name = entry.modified_by.get_full_name()
        else:
            modified_by_name = 'another user'

        logger.info(
            f'Version conflict for entry {entry.pk}: '
            f'client version mismatch, server={entry.edit_version}, '
            f'modified_by={modified_by_name}'
        )

        # Generate unified diff HTML for modal display
        diff_html = DiffHelper.generate_unified_diff_html(
            server_text=entry.text,
            client_text=client_text
        )

        # Render modal template
        modal_html = render_to_string(
            modal_template,
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


class AutoSaveHelper:
    """Generic helper for auto-save operations on versioned entries."""

    @classmethod
    def parse_autosave_request(
            cls,
            request_body        : bytes,
            extra_field_parsers : dict = None ) -> Tuple[Optional[AutoSaveRequest], Optional[JsonResponse]]:
        """
        Parse and validate auto-save request JSON.

        Args:
            request_body: Raw request body bytes
            extra_field_parsers: Dict of field_name -> parser_function for additional fields

        Returns:
            Tuple of (AutoSaveRequest, None) on success, or (None, error_response) on failure
        """
        try:
            data = json.loads(request_body)
            text = data.get('text', '')
            client_version = data.get('version')
        except json.JSONDecodeError:
            logger.warning('Invalid JSON in auto-save request')
            return None, JsonResponse(
                {'status': 'error', 'message': 'Invalid JSON'},
                status=400
            )

        # Parse extra fields if provided
        extra_fields = {}
        if extra_field_parsers:
            for field_name, parser_func in extra_field_parsers.items():
                value = data.get(field_name)
                if value is not None:
                    try:
                        extra_fields[field_name] = parser_func(value)
                    except (ValueError, TypeError) as e:
                        logger.warning(f'Invalid {field_name}: {value}, error: {e}')
                        return None, JsonResponse(
                            {'status': 'error', 'message': f'Invalid {field_name}'},
                            status=400
                        )

        return AutoSaveRequest(
            text=text,
            client_version=client_version,
            extra_fields=extra_fields
        ), None

    @classmethod
    def update_entry_atomically( cls,
                                 entry         : T,
                                 text          : str,
                                 user          : User,
                                 extra_updates : dict = None) -> T:
        """
        Update entry with atomic version increment.

        Args:
            entry: Locked entry to update (must have edit_version field)
            text: New text content
            user: User making the modification
            extra_updates: Dict of field_name -> value for additional updates

        Returns:
            Updated entry with refreshed version
        """
        entry.text = text
        if hasattr(entry, 'modified_by'):
            entry.modified_by = user

        update_fields = ['text', 'edit_version', 'modified_datetime']
        if hasattr(entry, 'modified_by'):
            update_fields.append('modified_by')

        # Apply extra updates if provided
        if extra_updates:
            for field_name, value in extra_updates.items():
                setattr(entry, field_name, value)
                update_fields.append(field_name)

        # Use F() expression for atomic increment to prevent race conditions
        entry.edit_version = F('edit_version') + 1
        entry.save(update_fields=update_fields)

        # Refresh to get the actual version value (F() expressions don't update in-memory)
        entry.refresh_from_db(fields=['edit_version', 'modified_datetime'])

        return entry
