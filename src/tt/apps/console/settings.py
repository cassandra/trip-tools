from tt.apps.config.setting_enums import SettingEnum, SettingDefinition
from tt.apps.attribute.enums import AttributeValueType
from tt.apps.attribute.value_ranges import PredefinedValueRanges

from .enums import Theme, DisplayUnits

Label = 'Console'


class ConsoleSetting( SettingEnum ):

    TIMEZONE = SettingDefinition(
        label = 'Timezone',
        description = 'Timezone to use for display',
        value_type = AttributeValueType.ENUM,
        value_range_str = PredefinedValueRanges.TIMEZONE_CHOICES_ID,
        is_editable = True,
        is_required = True,
        initial_value = 'America/Chicago',
    )
    DISPLAY_UNITS = SettingDefinition(
        label = 'Display Units',
        description = 'Units used when displaying',
        value_type = AttributeValueType.ENUM,
        value_range_str = PredefinedValueRanges.UNITS_CHOICES_ID,
        is_editable = True,
        is_required = True,
        initial_value = str( DisplayUnits.default() ),
    )
    THEME = SettingDefinition(
        label = 'Theme',
        description = 'Overall look and feel of interfaces',
        value_type = AttributeValueType.ENUM,
        value_range_str = PredefinedValueRanges.THEME_CHOICES_ID,
        is_editable = True,
        is_required = True,
        initial_value = str( Theme.default() ),
    )
    
