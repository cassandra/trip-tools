from typing import Any, Dict

from rest_framework import serializers

from tt.apps.api.constants import APIFields as F
from tt.apps.locations.models import Location


class LocationSerializer(serializers.Serializer):
    """
    Explicit serializer for Location model with manual field mapping.

    Using explicit serializers (not ModelSerializer) to maintain full control
    over the API contract and ensure deliberate changes to the API interface.
    """
    uuid = serializers.UUIDField( read_only = True )
    title = serializers.CharField( max_length = 200 )
    latitude = serializers.DecimalField( max_digits = 10, decimal_places = 7 )
    longitude = serializers.DecimalField( max_digits = 10, decimal_places = 7 )
    subcategory_slug = serializers.CharField( allow_null = True, required = False )
    trip_uuid = serializers.UUIDField()
    created_datetime = serializers.DateTimeField( read_only = True )

    def to_representation( self, instance: Location ) -> Dict[str, Any]:
        return {
            F.UUID: str( instance.uuid ),
            F.TITLE: instance.title,
            F.LATITUDE: instance.latitude,
            F.LONGITUDE: instance.longitude,
            F.SUBCATEGORY_SLUG: instance.subcategory.slug if instance.subcategory else None,
            F.TRIP_UUID: str( instance.trip.uuid ),
            F.CREATED_DATETIME: instance.created_datetime.isoformat(),
        }
