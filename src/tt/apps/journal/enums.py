from tt.apps.common.enums import LabeledEnum


class JournalVisibility(LabeledEnum):
    """
    Visibility levels for journal web view access.

    Each visibility level includes:
    - label: Display name
    - description: Explanatory text
    - icon_name: Icon identifier for UI display
    - badge_color: Bootstrap badge color class (secondary/warning/success)
    """
    PRIVATE   = ('Private'   , 'Only trip members can access'  , 'lock'   , 'secondary')
    PROTECTED = ('Protected' , 'Password-required access'       , 'shield' , 'warning')
    PUBLIC    = ('Public'    , 'Anyone with URL can access'     , 'globe' , 'success')

    def __init__(self, label, description, icon_name, badge_color):
        super().__init__(label, description)
        self.icon_name = icon_name
        self.badge_color = badge_color


class ImagePickerScope(LabeledEnum):
    """
    Scope filter for journal image picker.

    Phase 1: Single DEFAULT value - all filtering done client-side.
    """
    DEFAULT = ('All Images', 'Show all images for the selected date')
