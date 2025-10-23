import logging

from tt.apps.common.singleton import Singleton
from tt.apps.config.settings_mixins import SettingsMixin

logger = logging.getLogger(__name__)


class ConsoleManager( Singleton, SettingsMixin ):

    def __init_singleton__(self):
        self._was_initialized = False
        return

    def ensure_initialized(self):
        if self._was_initialized:
            return
        self._was_initialized = True
        return
