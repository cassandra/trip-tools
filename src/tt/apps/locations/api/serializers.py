from typing import Any, Dict, List

from rest_framework import serializers

from tt.apps.api.constants import APIFields as F
from tt.apps.locations.models import Location, LocationNote


class LocationNoteSerializer( serializers.Serializer ):
    """
    Serializer for LocationNote model (nested in Location).
    """
    text = serializers.CharField()
    source_label = serializers.CharField( required = False, allow_blank = True )
    source_url = serializers.URLField( required = False, allow_blank = True )

    def to_representation( self, instance: LocationNote ) -> Dict[str, Any]:
        return {
            F.TEXT: instance.text,
            F.SOURCE_LABEL: instance.source_label,
            F.SOURCE_URL: instance.source_url,
        }


class LocationSerializer( serializers.Serializer ):
    """
    Explicit serializer for Location model with manual field mapping.

    Using explicit serializers (not ModelSerializer) to maintain full control
    over the API contract and ensure deliberate changes to the API interface.
    """
    uuid = serializers.UUIDField( read_only = True )
    title = serializers.CharField( max_length = 200 )
    latitude = serializers.DecimalField(
        max_digits = 9,
        decimal_places = 6,
        required = False,
        allow_null = True,
    )
    longitude = serializers.DecimalField(
        max_digits = 9,
        decimal_places = 6,
        required = False,
        allow_null = True,
    )
    elevation_ft = serializers.DecimalField(
        max_digits = 9,
        decimal_places = 2,
        required = False,
        allow_null = True,
    )
    subcategory_slug = serializers.CharField(
        required = False,
        allow_null = True,
        allow_blank = True,
    )
    trip_uuid = serializers.UUIDField()
    gmm_id = serializers.CharField(
        max_length = 255,
        required = False,
        allow_null = True,
        allow_blank = True,
    )
    rating = serializers.DecimalField(
        max_digits = 4,
        decimal_places = 1,
        required = False,
        allow_null = True,
    )
    desirability = serializers.CharField(
        required = False,
        allow_null = True,
        allow_blank = True,
    )
    advanced_booking = serializers.CharField(
        required = False,
        allow_null = True,
        allow_blank = True,
    )
    open_days_times = serializers.CharField(
        required = False,
        allow_blank = True,
    )
    location_notes = LocationNoteSerializer(
        many = True,
        required = False,
    )
    version = serializers.IntegerField( read_only = True )
    created_datetime = serializers.DateTimeField( read_only = True )
    modified_datetime = serializers.DateTimeField( read_only = True )

    def to_representation( self, instance: Location ) -> Dict[str, Any]:
        # Serialize location notes
        location_notes: List[Dict[str, Any]] = []
        for note in instance.location_notes.all():
            location_notes.append( LocationNoteSerializer().to_representation( note ) )

        return {
            F.UUID: str( instance.uuid ),
            F.TRIP_UUID: str( instance.trip.uuid ),
            F.GMM_ID: instance.gmm_id,
            F.VERSION: instance.version,
            F.TITLE: instance.title,
            F.SUBCATEGORY_SLUG: instance.subcategory.slug if instance.subcategory else None,
            F.CONTACT_INFO: None,  # TODO: Serialize contact_info when needed
            F.RATING: float( instance.rating ) if instance.rating else None,
            F.DESIRABILITY: str( instance.desirability ) if instance.desirability else None,
            F.ADVANCED_BOOKING: str( instance.advanced_booking ) if instance.advanced_booking else None,
            F.OPEN_DAYS_TIMES: instance.open_days_times,
            F.LATITUDE: float( instance.latitude ) if instance.latitude else None,
            F.LONGITUDE: float( instance.longitude ) if instance.longitude else None,
            F.ELEVATION_FT: float( instance.elevation_ft ) if instance.elevation_ft else None,
            F.CREATED_DATETIME: instance.created_datetime.isoformat(),
            F.MODIFIED_DATETIME: instance.modified_datetime.isoformat(),
            F.LOCATION_NOTES: location_notes,
        }
