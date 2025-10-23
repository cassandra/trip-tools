from tt.apps.config.setting_enums import SettingEnum, SettingDefinition
from tt.apps.attribute.enums import AttributeValueType

Label = 'Notifications'


class NotifySetting( SettingEnum ):

    NOTIFICATIONS_ENABLED = SettingDefinition(
        label = 'Enable Notifications',
        description = 'Whether to send notifications (e.g., emails).',
        value_type = AttributeValueType.BOOLEAN,
        value_range_str = '',
        is_editable = True,
        is_required = True,
        initial_value = True,
    )
    
