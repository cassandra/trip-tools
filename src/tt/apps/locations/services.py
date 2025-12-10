"""
Location service for CRUD operations.

Handles database operations for Location model, keeping business logic
separate from the API serializers and views.
"""
from typing import Any, Dict, List

from django.db import transaction

from tt.apps.trips.models import Trip

from .heuristics import apply_note_heuristics
from .models import Location, LocationNote, LocationSubCategory


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
        with transaction.atomic():
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

            # Handle location_notes if present (replace all strategy)
            if 'location_notes' in validated_data:
                cls._replace_location_notes( location, validated_data['location_notes'] )

        return location

    @classmethod
    def _replace_location_notes(
        cls,
        location: Location,
        notes_data: List[Dict[str, Any]],
    ) -> None:
        """
        Replace all location notes with new data using bulk operations.

        Deletes existing notes and creates new ones from the provided data.
        Empty notes (no text) are filtered out. Source attribution heuristics
        are applied to each note before creation.

        Args:
            location: The Location to update notes for.
            notes_data: List of note dicts with text, source_label, source_url.
        """
        # Delete existing notes
        location.location_notes.all().delete()

        # Build note instances with heuristics applied
        notes_to_create = []
        sort_order = 0
        for note_data in notes_data:
            text = ( note_data.get( 'text' ) or '' ).strip()
            if not text:
                continue

            note = LocationNote(
                location = location,
                text = text,
                source_label = note_data.get( 'source_label' ) or '',
                source_url = note_data.get( 'source_url' ) or '',
                sort_order = sort_order,
            )
            apply_note_heuristics( note )
            notes_to_create.append( note )
            sort_order += 1

        # Bulk create all notes
        if notes_to_create:
            LocationNote.objects.bulk_create( notes_to_create )
