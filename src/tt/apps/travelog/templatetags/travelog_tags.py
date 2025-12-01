from datetime import date as date_type
from typing import Union, Optional
from uuid import UUID

from django import template
from django.urls import reverse
from urllib.parse import urlencode

from ..helpers import TravelogHelpers

register = template.Library()


@register.simple_tag
def trip_date_span(
    start_date: Optional[Union[date_type, str]],
    end_date: Optional[Union[date_type, str]]
) -> str:
    """
    Format a trip date span with smart consolidation.

    Returns empty string if either date is None (e.g., journal has only special entries).

    Args:
        start_date: The starting date - date object or 'YYYY-MM-DD' string
        end_date: The ending date - date object or 'YYYY-MM-DD' string

    Examples:
        {% trip_date_span first_day.date last_day.date %}
        {% trip_date_span "2024-03-13" "2024-03-20" %}
        → "March 13-20, 2024" (same month)
        → "March 28 - April 5, 2024" (different months)
        → "December 28, 2024 - January 5, 2025" (different years)
        → "" (if no dated entries)
    """
    if start_date is None or end_date is None:
        return ''

    # Parse string dates if needed
    if isinstance(start_date, str):
        start_date = date_type.fromisoformat(start_date)
    if isinstance(end_date, str):
        end_date = date_type.fromisoformat(end_date)

    return TravelogHelpers.format_trip_date_span(
        start_date = start_date,
        end_date = end_date,
    )


@register.simple_tag
def travelog_url(
    url_name     : str,
    journal_uuid : UUID,
    version      : Optional[Union[str, int]] = None,
    date         : Optional[Union[date_type, str]] = None,
    **kwargs
) -> str:
    """
    Build travelog URL with version and optional query parameters.

    Args:
        url_name: Django URL name (e.g., 'travelog_day', 'travelog_toc')
        journal_uuid: Journal UUID
        version: Version parameter - 'draft', 'view', or integer version number
        date: Entry date - datetime.date object or 'YYYY-MM-DD' string (for travelog_day)
        **kwargs: Additional URL kwargs (e.g., page_num=2, image_uuid=...)

    Returns:
        URL string with query parameters if provided

    Examples:
        {% travelog_url 'travelog_toc' journal.uuid %}
        {% travelog_url 'travelog_toc' journal.uuid version='draft' %}
        {% travelog_url 'travelog_day' journal.uuid date=entry.date version='draft' %}
        {% travelog_url 'travelog_day' journal.uuid date='2024-01-15' version=2 %}
    """
    # Handle date parameter - convert date objects to ISO string format
    if date is not None:
        if isinstance(date, date_type):
            kwargs['date'] = date.isoformat()
        else:
            # Already a string - pass through
            kwargs['date'] = date

    kwargs['journal_uuid'] = journal_uuid
    base_url = reverse( url_name, kwargs = kwargs )

    # Build query parameters
    if version:
        query = urlencode({'version': version})
        return f"{base_url}?{query}"

    return base_url
