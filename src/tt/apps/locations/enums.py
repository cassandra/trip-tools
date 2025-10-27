from tt.apps.common.enums import LabeledEnum


class DesirabilityType( LabeledEnum ):
    LOW     = ( 'Low', '' )
    MEDIUM  = ( 'Medium', '' )
    HIGH    = ( 'High', '' )

    
class AdvancedBookingType( LabeledEnum ):

    NOT_AN_OPTION  = ( 'Not an option', '' )
    OPTIONAL       = ( 'Optional', '' )
    ADVISABLE      = ( 'Advisable', '' )
    REQUIRED       = ( 'Required', '' )

