from tt.apps.common.enums import LabeledEnum

    
class BookingStatus( LabeledEnum ):

    TODO         = ( 'To-do', '' )
    IN_PROGRESS  = ( 'In progress', '' )
    DONE         = ( 'Done', '' )
    CANCELLED    = ( 'Cancelled', '' )

    
class PaymentStatus( LabeledEnum ):

    NO       = ( 'No', '' )
    PARTIAL  = ( 'Partial', '' )
    AUTOPAY  = ( 'Auto-pay', '' )
    YES      = ( 'Yes', '' )
