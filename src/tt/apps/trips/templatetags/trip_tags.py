from django import template

from tt.apps.trips.enums import TripPermissionLevel

register = template.Library()


@register.simple_tag
def get_permission_levels():
    """Returns all TripPermissionLevel enum values for iteration in templates."""
    return list(TripPermissionLevel)
