from enum import Enum

from tt.apps.common.enums import LabeledEnum


class TripPage(str, Enum):
    """Enum for trip-related pages."""

    OVERVIEW   = 'trip_overview'
    ITINERARY  = 'itinerary'
    LOCATIONS  = 'locations'
    BOOKINGS   = 'bookings'
    NOTES      = 'notes'


class TripStatus( LabeledEnum ):

    UPCOMING  = ( 'Upcoming', '' )
    CURRENT   = ( 'Current', '' )
    PAST      = ( 'Past', '' )
