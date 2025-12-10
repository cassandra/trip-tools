"""
Location service for CRUD operations.

Handles database operations for Location model, keeping business logic
separate from the API serializers and views.
"""
from typing import Any, Dict

from tt.apps.trips.models import Trip

from .models import Location, LocationSubCategory


class LocationService:
    """
    Service class for Location CRUD operations.
    """

    @classmethod
    def create(
        cls,
        trip: Trip,
        validated_data: Dict[str, Any],
    ) -> Location:
        """
        Create a Location from validated data.

        Args:
            trip: The Trip to associate the location with.
            validated_data: Validated data from serializer (API field names).

        Returns:
            Created Location instance.
        """
        # Handle subcategory_slug -> subcategory FK
        subcategory_slug = validated_data.pop( 'subcategory_slug', None )
        subcategory = None
        if subcategory_slug:
            subcategory = LocationSubCategory.objects.filter(
                slug = subcategory_slug
            ).first()

        # Remove trip_uuid from validated_data (trip passed separately)
        validated_data.pop( 'trip_uuid', None )

        # Handle desirability/advanced_booking enum strings
        desirability = validated_data.pop( 'desirability', None )
        advanced_booking = validated_data.pop( 'advanced_booking', None )

        location = Location.objects.create(
            trip = trip,
            subcategory = subcategory,
            desirability = desirability,
            advanced_booking = advanced_booking,
            **validated_data,
        )

        return location

    @classmethod
    def update(
        cls,
        location: Location,
        validated_data: Dict[str, Any],
    ) -> Location:
        """
        Update a Location with validated data.

        Args:
            location: The Location instance to update.
            validated_data: Validated data from serializer (only fields present will be updated).

        Returns:
            Updated Location instance.
        """
        # Handle subcategory if present
        if 'subcategory_slug' in validated_data:
            subcategory_slug = validated_data.pop( 'subcategory_slug' )
            if subcategory_slug:
                location.subcategory = LocationSubCategory.objects.filter(
                    slug = subcategory_slug
                ).first()
            else:
                location.subcategory = None

        # Update simple fields if present
        simple_fields = [
            'title', 'latitude', 'longitude', 'elevation_ft', 'gmm_id',
            'rating', 'desirability', 'advanced_booking', 'open_days_times',
        ]
        for field in simple_fields:
            if field in validated_data:
                setattr( location, field, validated_data[field] )

        location.save()
        return location
