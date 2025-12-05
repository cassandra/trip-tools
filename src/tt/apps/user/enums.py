from enum import Enum

from tt.apps.common.enums import LabeledEnum


class SigninErrorType( LabeledEnum ):
    """
    Error types that can be displayed on the signin page.
    """
    INVITATION_EXPIRED = (
        'Invitation Link Expired',
        'This invitation link has expired or has already been used. You have been added to the trip - just sign in below to access it.',
    )


class AccountPageType(str, Enum):
    """Enum for account-related pages."""

    PROFILE    = 'profile'
    API_KEYS   = 'api_keys'
