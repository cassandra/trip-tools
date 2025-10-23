import logging

from django.contrib.auth.models import User as UserType

from tt.apps.common.singleton import Singleton
from tt.apps.config.settings_mixins import SettingsMixin

from .enums import DisplayUnits
from .settings import ConsoleSetting

logger = logging.getLogger(__name__)


class ConsoleSettingsHelper( Singleton, SettingsMixin ):

    def __init_singleton__(self):
        self._geo_location_map = dict()
        return

    def get_tz_name( self, user : UserType ) -> str:
        return self.settings_manager().get_setting_value(
            user = user,
            setting_enum = ConsoleSetting.TIMEZONE,
        )
            
    def get_display_units( self, user : UserType  ) -> DisplayUnits:
        display_units_str = self.settings_manager().get_setting_value(
            user = user,
            setting_enum = ConsoleSetting.DISPLAY_UNITS,
        )
        return DisplayUnits.from_name_safe( display_units_str )
