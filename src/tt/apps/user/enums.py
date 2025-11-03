from tt.apps.common.enums import LabeledEnum


class SigninErrorType( LabeledEnum ):
    """
    Error types that can be displayed on the signin page.
    """
    INVITATION_EXPIRED = (
        'Invitation Link Expired',
        'This invitation link has expired or has already been used. You have been added to the trip - just sign in below to access it.',
    )

    
class AccountPage(LabeledEnum):
    """
    Defines those features that appear on the main config (admin) home
    page and links to their content.  Each tab in the config pane will
    have an enum entry.
    """
    
    def __init__( self,
                  label        : str,
                  description  : str,
                  url_name     : str ):
        super().__init__( label, description )
        self.url_name = url_name
        return

    PROFILE     = ('Profile'      , ''   , 'user_account' )
    SETTINGS    = ('Preferences'  , ''   , 'config_settings' )

    @classmethod
    def default(cls):
        return cls.PROFILE
