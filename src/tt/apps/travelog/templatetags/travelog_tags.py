from uuid import UUID

from django import template
from django.urls import reverse
from urllib.parse import urlencode

register = template.Library()


@register.simple_tag
def travelog_url( url_name : str, journal_uuid : UUID, version : int = None, **kwargs):
    """
    Build travelog URL with version query parameter preserved.

    Args:
        url_name: Django URL name (e.g., 'travelog_day', 'travelog_toc')
        journal_uuid: Journal UUID
        version: Version parameter - 'draft', 'view', or integer version number
        **kwargs: Additional URL kwargs (e.g., date='2024-01-15', page_num=2)

    Returns:
        URL string with version query parameter if provided

    Examples:
        {% travelog_url 'travelog_toc' journal.uuid %}
        {% travelog_url 'travelog_toc' journal.uuid version='draft' %}
        {% travelog_url 'travelog_day' journal.uuid date='2024-01-15' version=request.GET.version %}
    """
    kwargs['journal_uuid'] = journal_uuid
    base_url = reverse( url_name, kwargs = kwargs )

    if version:
        query = urlencode({ 'version': version })
        return f"{base_url}?{query}"

    return base_url
