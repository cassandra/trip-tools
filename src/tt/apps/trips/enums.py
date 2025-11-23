from enum import Enum

from tt.apps.common.enums import LabeledEnum


class TripPage(str, Enum):
    """Enum for trip-related pages."""

    OVERVIEW   = 'trip_overview'
    ITINERARY  = 'itinerary'
    LOCATIONS  = 'locations'
    BOOKINGS   = 'bookings'
    REVIEWS    = 'reviews'
    JOURNAL    = 'journal'
    IMAGES     = 'images'
    MEMBERS    = 'members'


class TripPermissionLevel( LabeledEnum ):
    """
    Permission levels for trip sharing.
    """
    OWNER   = ( 'Owner', 'Full control including deletion and sharing' , 4 )
    ADMIN   = ( 'Admin', 'Can edit and manage most aspects'            , 3 )
    EDITOR  = ( 'Editor', 'Can edit trip content'                      , 2 )
    VIEWER  = ( 'Viewer', 'Can view trip content'                      , 1 )

    def __init__( self, label, description, priority ):
        super().__init__( label, description )
        self.priority = priority
        return

    def __lt__( self, other ):
        if not isinstance( other, TripPermissionLevel ):
            raise NotImplementedError()
        return bool( self.priority < other.priority )

    def __le__( self, other ):
        if not isinstance( other, TripPermissionLevel ):
            raise NotImplementedError()
        return bool( self.priority <= other.priority )

    def __gt__( self, other ):
        if not isinstance( other, TripPermissionLevel ):
            raise NotImplementedError()
        return bool( self.priority > other.priority )

    def __ge__( self, other ):
        if not isinstance( other, TripPermissionLevel ):
            raise NotImplementedError()
        return bool( self.priority >= other.priority )

    def __eq__( self, other ):
        if not isinstance( other, TripPermissionLevel ):
            raise NotImplementedError()
        return bool( self.priority == other.priority )

    @property
    def is_owner(self):
        return bool( self in [ TripPermissionLevel.OWNER ])

    @property
    def is_admin(self):
        return bool( self in [ TripPermissionLevel.OWNER,
                               TripPermissionLevel.ADMIN ])

    @property
    def is_editor(self):
        return bool( self in [ TripPermissionLevel.OWNER,
                               TripPermissionLevel.ADMIN,
                               TripPermissionLevel.EDITOR ])

    
class TripStatus( LabeledEnum ):

    UPCOMING  = ( 'Upcoming', '' )
    CURRENT   = ( 'Current', '' )
    PAST      = ( 'Past', '' )
