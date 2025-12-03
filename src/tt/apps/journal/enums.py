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


class JournalTheme(LabeledEnum):
    """
    Visual theme for travelog display.

    Each theme defines a color scheme via CSS class in travelog.css.
    """

    def __init__(self, label: str, description: str, css_classname: str):
        super().__init__(label, description)
        self.css_classname = css_classname

    DEFAULT = (
        'Default',
        'Teal & Coral - Default theme with teal primary and coral secondary colors',
        'theme-current'
    )

    SUNSET = (
        'Warm Sunset',
        'Amber & Red - Warm, inviting theme with sunset-inspired colors',
        'theme-sunset'
    )

    OCEAN = (
        'Ocean Blue',
        'Sky & Cyan - Cool, refreshing theme with ocean-inspired blues',
        'theme-ocean'
    )

    FOREST = (
        'Forest Green',
        'Emerald & Lime - Natural, earthy theme with green tones',
        'theme-forest'
    )

    PURPLE = (
        'Purple Dreams',
        'Violet & Pink - Bold, creative theme with purple and pink accents',
        'theme-purple'
    )

    EARTH = (
        'Earthy Terracotta',
        'Brown & Red - Warm, rustic theme with terracotta and brown tones',
        'theme-earth'
    )

    @classmethod
    def default(cls):
        """Default theme for new journals."""
        return JournalTheme.DEFAULT

    
class EntryPageType(LabeledEnum):

    DATED     = ( 'Dated'     , 'Journal entries with a date.' )
    PROLOGUE  = ( 'Prologue'  , 'Journal entries that are prologue.' )
    EPILOGUE  = ( 'Epilogue'  , 'Journal entries that are epilogue.' )
    
    
class ImagePickerScope(LabeledEnum):

    UNUSED  = ( 'Unused'  , 'Images that appear at least once in the content.' )
    USED    = ( 'Used'    , 'Images that do not appear in content.' )
    ALL     = ( 'All'     , 'All images matching search filters.' )
    
    @property
    def is_unused(self):
        return bool( self == ImagePickerScope.UNUSED )
    
    @property
    def is_used(self):
        return bool( self == ImagePickerScope.USED )
    
    @property
    def is_all(self):
        return bool( self == ImagePickerScope.ALL )
    
