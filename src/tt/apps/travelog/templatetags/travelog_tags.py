from datetime import date as date_type
from typing import Union, Optional
from uuid import UUID

from django import template
from django.urls import reverse
from urllib.parse import urlencode

register = template.Library()


@register.simple_tag
def travelog_url(
    url_name     : str,
    journal_uuid : UUID,
    version      : Optional[Union[str, int]] = None,
    date         : Optional[Union[date_type, str]] = None,
    **kwargs
) -> str:
    """
    Build travelog URL with version query parameter preserved.

    Args:
        url_name: Django URL name (e.g., 'travelog_day', 'travelog_toc')
        journal_uuid: Journal UUID
        version: Version parameter - 'draft', 'view', or integer version number
        date: Entry date - datetime.date object or 'YYYY-MM-DD' string (for travelog_day)
        **kwargs: Additional URL kwargs (e.g., page_num=2, image_uuid=...)

    Returns:
        URL string with version query parameter if provided

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

    if version:
        query = urlencode({ 'version': version })
        return f"{base_url}?{query}"

    return base_url
