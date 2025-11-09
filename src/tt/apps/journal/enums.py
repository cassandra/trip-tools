from tt.apps.common.enums import LabeledEnum


class JournalVisibility(LabeledEnum):
    """
    Visibility levels for journal web view access.
    """
    PRIVATE   = ('Private'    , 'Only trip members can access')
    PROTECTED = ('Protected'  , 'Password-required access')
    PUBLIC    = ('Public'     , 'Anyone with URL can access')


class ImagePickerScope(LabeledEnum):
    """
    Scope filter for journal image picker.

    Phase 1: Single DEFAULT value - all filtering done client-side.
    """
    DEFAULT = ('All Images', 'Show all images for the selected date')
