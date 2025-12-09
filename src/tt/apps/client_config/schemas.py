"""
Typed dataclasses for client configuration data.

These dataclasses define the internal data structures used by ClientConfigService.
They are converted to API responses via serializers in api/serializers.py.
"""

from dataclasses import dataclass
from typing import List

from tt.apps.locations.models import LocationCategory


@dataclass
class ClientConfig:
    """
    Complete client configuration with version hash.

    The version is an MD5 hash of the serialized location categories,
    used for efficient sync detection by clients.

    The location_categories is a List (not QuerySet) to ensure the data is
    evaluated and immutable at construction time.
    """

    version: str
    location_categories: List[LocationCategory]
