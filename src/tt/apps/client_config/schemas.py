"""
Typed dataclasses for client configuration data.

These dataclasses define the internal data structures used by ClientConfigService.
They are converted to API responses via serializers in api/serializers.py.
"""

from dataclasses import dataclass, field
from typing import Dict, List

from tt.apps.locations.models import LocationCategory


@dataclass
class ClientConfig:
    """
    Complete client configuration with version hash.

    The config_version is an MD5 hash of the serialized config content,
    used for efficient sync detection by clients.

    The location_categories is a List (not QuerySet) to ensure the data is
    evaluated and immutable at construction time.

    The desirability_type and advanced_booking_type fields provide enum definitions
    for dropdown population in the extension UI.

    The server_version is included to ensure cache invalidation when the server
    is updated, even if database content hasn't changed.
    """

    config_version: str
    server_version: str
    location_categories: List[LocationCategory]
    desirability_type: List[Dict[str, str]] = field(default_factory=list)
    advanced_booking_type: List[Dict[str, str]] = field(default_factory=list)
