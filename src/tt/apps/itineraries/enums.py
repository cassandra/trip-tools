from tt.apps.common.enums import LabeledEnum


class ItineraryItemType( LabeledEnum ):

    FLIGHT       = ( 'Flight', '' )
    RAIL         = ( 'Rail', '' )
    BUS          = ( 'Bus/Shuttle', '' )
    BOAT         = ( 'Boat', '' )
    CAR          = ( 'Boat', '' )
    CAR_RENTAL   = ( 'Car rental', '' )
    CAR_SERVICE  = ( 'Car service', '' )
    LODGING      = ( 'Lodging', '' )
    ACTIVITY        = ( 'Activity', '' )
    TOUR         = ( 'Tour', '' )
    OTHER        = ( 'Other', '' )
