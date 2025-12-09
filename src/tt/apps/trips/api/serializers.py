from typing import Any, Dict

from rest_framework import serializers

from tt.apps.api.constants import APIFields as F
from tt.apps.trips.models import Trip


class TripSerializer( serializers.Serializer ):
    """
    Explicit serializer for Trip model with manual field mapping.

    Using explicit serializers (not ModelSerializer) to maintain full control
    over the API contract and ensure deliberate changes to the API interface.
    """
    uuid = serializers.UUIDField( read_only = True )
    title = serializers.CharField( max_length = 200 )
    description = serializers.CharField( required = False, allow_blank = True )
    trip_status = serializers.CharField( read_only = True )
    version = serializers.IntegerField( read_only = True )
    created_datetime = serializers.DateTimeField( read_only = True )
    gmm_map_id = serializers.CharField(
        max_length = 255,
        required = False,
        allow_null = True,
        allow_blank = True,
    )

    def to_representation( self, instance: Trip ) -> Dict[str, Any]:
        return {
            F.UUID: str( instance.uuid ),
            F.TITLE: instance.title,
            F.DESCRIPTION: instance.description,
            F.TRIP_STATUS: str( instance.trip_status ),
            F.VERSION: instance.version,
            F.CREATED_DATETIME: instance.created_datetime.isoformat(),
            F.GMM_MAP_ID: instance.gmm_map_id,
        }

    def update( self, instance: Trip, validated_data: Dict[str, Any] ) -> Trip:
        """
        Update Trip instance with validated data.
        Only updates fields that are present in validated_data.
        """
        if 'gmm_map_id' in validated_data:
            instance.gmm_map_id = validated_data['gmm_map_id']
        if 'title' in validated_data:
            instance.title = validated_data['title']
        if 'description' in validated_data:
            instance.description = validated_data['description']
        instance.save()
        return instance
