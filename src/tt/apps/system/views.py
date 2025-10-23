import logging

from tt.apps.config.enums import ConfigPageType
from tt.apps.config.views import ConfigPageView

logger = logging.getLogger(__name__)


class SystemInfoView( ConfigPageView ):

    @property
    def config_page_type(self) -> ConfigPageType:
        return ConfigPageType.SYSTEM_INFO
    
    def get_template_name( self ) -> str:
        return 'system/pages/system_info.html'

    def get_template_context( self, request, *args, **kwargs ):
        return {
        }
