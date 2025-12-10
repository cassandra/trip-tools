"""
Explicit serializers for client config API contract.

Using explicit serializers (not ModelSerializer) to maintain full control
over the API contract and ensure deliberate changes to the API interface.
"""

from typing import Any, Dict

from rest_framework import serializers

from tt.apps.api.constants import APIFields as F
from tt.apps.locations.models import LocationCategory, LocationSubCategory

from ..schemas import ClientConfig


class LocationSubCategorySerializer(serializers.Serializer):
    """
    Serializer for LocationSubCategory in client config.

    Explicitly maps model fields to API field names using APIFields constants.
    """

    def to_representation(self, instance: LocationSubCategory) -> Dict[str, Any]:
        return {
            F.ID: instance.id,
            F.NAME: instance.name,
            F.SLUG: instance.slug,
            F.ICON_CODE: instance.icon_code,
            F.COLOR_CODE: instance.color_code,
        }


class LocationCategorySerializer(serializers.Serializer):
    """
    Serializer for LocationCategory with nested subcategories.

    Subcategories are sorted alphabetically by name.
    """

    def to_representation(self, instance: LocationCategory) -> Dict[str, Any]:
        subcategories = instance.subcategories.order_by('name')
        return {
            F.ID: instance.id,
            F.NAME: instance.name,
            F.SLUG: instance.slug,
            F.ICON_CODE: instance.icon_code,
            F.COLOR_CODE: instance.color_code,
            F.SUBCATEGORIES: LocationSubCategorySerializer(subcategories, many=True).data,
        }


class ClientConfigSerializer(serializers.Serializer):
    """
    Serializer for ClientConfig dataclass.

    Converts the typed ClientConfig to the API response format.
    This defines the complete API contract for the client config endpoint.
    """

    def to_representation(self, instance: ClientConfig) -> Dict[str, Any]:
        return {
            F.CONFIG_VERSION: instance.config_version,
            F.SERVER_VERSION: instance.server_version,
            F.LOCATION_CATEGORIES: LocationCategorySerializer(
                instance.location_categories, many=True
            ).data,
            F.DESIRABILITY_TYPE: instance.desirability_type,
            F.ADVANCED_BOOKING_TYPE: instance.advanced_booking_type,
        }
