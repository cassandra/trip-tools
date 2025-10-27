from tt.apps.common.enums import LabeledEnum


class ContactType( LabeledEnum ):

    PHONE    = ( 'Phone', '' )
    EMAIL    = ( 'Email', '' )
    WEBSITE  = ( 'Website', '' )
    ADDRESS  = ( 'Address', '' )
    OTHER    = ( 'Other', '' )
