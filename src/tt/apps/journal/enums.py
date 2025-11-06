from tt.apps.common.enums import LabeledEnum


class JournalVisibility(LabeledEnum):
    """
    Visibility levels for journal web view access.
    """
    PRIVATE   = ('Private'    , 'Only trip members can access')
    PROTECTED = ('Protected'  , 'Password-required access')
    PUBLIC    = ('Public'     , 'Anyone with URL can access')
