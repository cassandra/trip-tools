from django import template
from django.contrib.auth.models import User as UserType

from tt.apps.console.console_helper import ConsoleSettingsHelper

from tt.units import UnitQuantity, get_display_quantity

register = template.Library()


@register.simple_tag( takes_context = True )
def format_quantity( context, quantity : UnitQuantity, fmt = "~H" ):
    """
    Formats a Pint unit quantity using the specified format.

    Usage:
    {% format_quantity my_quantity "~P" %}

    Available formats:
    - "P" (default): Compact human-readable
    - "~P": Removes unit definitions for a clean output (e.g., "10 ft")
    - "L": Latex formatted output
    - "H": HTML formatted output
    - "C": Compact notation
    """
    user = context.get( 'request' ).user if context.get( 'request' ) else None
    display_quantity = to_display_quantity( user, quantity )
    try:
        return f"{display_quantity:{fmt}}"
    except Exception:
        return str( display_quantity )


@register.simple_tag( takes_context = True )
def format_magnitude( context, quantity : UnitQuantity, decimal_places : int = 1  ):
    if not isinstance( quantity, UnitQuantity ):
        return str( quantity )

    user = context.get( 'request' ).user if context.get( 'request' ) else None
    display_quantity = to_display_quantity( user, quantity )
    try:
        return f"{display_quantity.magnitude:.{decimal_places}f}"
    except Exception:
        return str( display_quantity.magnitude )


@register.simple_tag( takes_context = True )
def format_units( context, quantity : UnitQuantity, fmt = "~H"  ):
    if not isinstance( quantity, UnitQuantity ):
        return str( quantity )

    user = context.get( 'request' ).user if context.get( 'request' ) else None
    display_quantity = to_display_quantity( user, quantity )
    try:
        return f"{display_quantity.units:{fmt}}"
    except Exception:
        return ""


@register.filter
def format_compass( quantity : UnitQuantity ):
    """Converts degrees into a compass direction (N, NE, E, etc.)."""
    if not isinstance( quantity, UnitQuantity ):
        return str( quantity )

    degrees = quantity.to("deg").magnitude % 360  # Normalize 0-360°
    directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                  "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    index = round( degrees / 22.5 ) % 16
    return directions[index]


def to_display_quantity( user : UserType, quantity : UnitQuantity ):
    if not isinstance( quantity, UnitQuantity ):
        return quantity
    display_units = ConsoleSettingsHelper().get_display_units( user = user )
    return get_display_quantity(
        quantity = quantity,
        display_units = display_units,
    )
