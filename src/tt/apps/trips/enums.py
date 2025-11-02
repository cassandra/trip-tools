from enum import Enum

from tt.apps.common.enums import LabeledEnum


class TripPage(str, Enum):
    """Enum for trip-related pages."""

    OVERVIEW   = 'trip_overview'
    ITINERARY  = 'itinerary'
    LOCATIONS  = 'locations'
    BOOKINGS   = 'bookings'
    NOTES      = 'notes'


class TripPermissionLevel( LabeledEnum ):
    """
    Permission levels for trip sharing.

    Ordered from highest to lowest permission, though enforcement
    is defined by TripPermissionMixin:PERMISSION_HIERARCHY.
    """
    OWNER   = ( 'Owner', 'Full control including deletion and sharing' )
    ADMIN   = ( 'Admin', 'Can edit and manage most aspects' )
    EDITOR  = ( 'Editor', 'Can edit trip content' )
    VIEWER  = ( 'Viewer', 'Can view trip content' )


class TripStatus( LabeledEnum ):

    UPCOMING  = ( 'Upcoming', '' )
    CURRENT   = ( 'Current', '' )
    PAST      = ( 'Past', '' )
