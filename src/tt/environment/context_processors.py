from django.conf import settings

from .client import ClientConfig
from .constants import TtConst
from .url_patterns import TtUrlPatterns


def client_config(request):
    """
    Provides client-side configuration to templates.

    Creates a structured configuration object that gets injected into
    JavaScript as TtClientConfig, providing a single source of truth for
    all client configuration needs.

    Fails fast on missing required data - no masking of interface problems.

    Returns:
        dict: Context variables for templates
    """
    config = ClientConfig(
        DEBUG = settings.DEBUG,
        ENVIRONMENT = settings.ENV.environment_name,
        VERSION = settings.ENV.VERSION,
        TRIP_ID = request.view_parameters.trip_id,
    )

    return {
        'tt_client_config': config,
    }


def shared_constants(request):
    return {
        'TtConst': TtConst,
        'TtUrlPatterns': TtUrlPatterns(),
    }
    
