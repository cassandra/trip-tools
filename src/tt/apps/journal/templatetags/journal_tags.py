"""
Template tags for journal app.

Provides access to journal enums and utilities in templates.
"""

from django import template
from tt.apps.journal.enums import JournalVisibility

register = template.Library()


@register.simple_tag
def get_visibility_options():
    """
    Return all JournalVisibility enum values for iteration in templates.

    Returns:
        list: All JournalVisibility enum members

    Example:
        {% get_visibility_options as visibility_options %}
        {% for vis in visibility_options %}
            {{ vis.label }}
        {% endfor %}
    """
    return list(JournalVisibility)


@register.filter
def get_visibility_by_name(name):
    """
    Look up a JournalVisibility enum member by its string name.

    Args:
        name (str): The enum member name (e.g., 'PRIVATE', 'PROTECTED', 'PUBLIC')

    Returns:
        JournalVisibility: The enum member, or None if not found

    Example:
        {% with vis='PRIVATE'|get_visibility_by_name %}
            {% icon vis.icon_name %}
        {% endwith %}
    """
    try:
        return JournalVisibility[name]
    except KeyError:
        return None
