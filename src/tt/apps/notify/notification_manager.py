import logging

from tt.apps.common.singleton import Singleton
from tt.apps.config.settings_mixins import SettingsMixin

logger = logging.getLogger(__name__)


class NotificationManager( Singleton, SettingsMixin ):

    def __init_singleton__(self):
        self._was_initialized = False
        return

    def ensure_initialized(self):
        if self._was_initialized:
            return
        # Any future heavyweight initializations go here (e.g., any DB operations).
        self._was_initialized = True
        return
