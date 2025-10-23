import logging
from threading import Lock
from typing import List

from django.contrib.auth.models import User as UserType

from tt.apps.common.singleton import Singleton

from .models import Subsystem, SubsystemAttribute
from .setting_enums import SettingEnum

logger = logging.getLogger(__name__)


class SettingsManager( Singleton ):

    def __init_singleton__( self ):
        self._subsystem_list = list()
        self._was_initialized = False
        self._subsystems_lock = Lock()
        return

    def ensure_initialized(self):
        
        with self._subsystems_lock:
            if self._was_initialized:
                return
            self._subsystem_list = list( Subsystem.objects.all() )
        self._was_initialized = True
        return
    
    def get_subsystem( self, subsystem_id : int ) -> List[ Subsystem ]:
        for subsystem in self._subsystem_list:
            if subsystem.id == subsystem_id:
                return subsystem
            continue
        raise Subsystem.DoesNotExist()
    
    def get_subsystems(self) -> List[ Subsystem ]:
        return self._subsystem_list

    def get_setting_value( self, user : UserType, setting_enum : SettingEnum ):
        if user.is_anonymous:
            return setting_enum.definition.initial_value
        try:
            db_attribute = SubsystemAttribute.objects.get(
                user = user,
                setting_key = setting_enum.key,
            )
            return db_attribute.value
        except SubsystemAttribute.DoesNotExist:
            # Setting attributes for a user are lazily created on viewing
            # the config page.  If the user had never edited their
            # settings, then they will just get the default value, which
            # would also be the initial value upon creatingf in the
            # database.
            return setting_enum.definition.initial_value
