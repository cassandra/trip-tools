from tt.apps.common.enums import LabeledEnum


class TripStatus( LabeledEnum ):

    UPCOMING  = ( 'Upcoming', '' )
    CURRENT   = ( 'Current', '' )
    PAST      = ( 'Past', '' )
