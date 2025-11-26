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
from django.http import HttpRequest, JsonResponse

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
    def validate_date_uniqueness(cls,
                                 entry: JournalEntry,
                                 new_date: date_class) -> Optional[JsonResponse]:
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
