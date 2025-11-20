from tt.apps.common.enums import LabeledEnum


class ImageAccessRole( LabeledEnum ):

    NONE    = ( 'None', '' )
    VIEWER  = ( 'Viewer', '' )
    EDITOR  = ( 'Editor', '' )
    OWNER   = ( 'Owner', '' )

    @property
    def can_access(self):
        return bool( self in [ ImageAccessRole.VIEWER,
                               ImageAccessRole.EDITOR,
                               ImageAccessRole.OWNER ] )

    @property
    def can_edit(self):
        return bool( self in [ ImageAccessRole.EDITOR,
                               ImageAccessRole.OWNER ] )
                     
