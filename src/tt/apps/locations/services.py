"""
Location service for CRUD operations.

Handles database operations for Location model, keeping business logic
separate from the API serializers and views.
"""
from typing import Any, Dict, List

from django.db import transaction

from tt.apps.api.constants import APIFields as F
from tt.apps.contacts.models import ContactInfo
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
        with transaction.atomic():
            # Handle subcategory_slug -> subcategory FK
            subcategory_slug = validated_data.pop( F.SUBCATEGORY_SLUG, None )
            subcategory = None
            if subcategory_slug:
                subcategory = LocationSubCategory.objects.filter(
                    slug = subcategory_slug
                ).first()

            # Remove trip_uuid from validated_data (trip passed separately)
            validated_data.pop( F.TRIP_UUID, None )

            # Handle desirability/advanced_booking enum strings
            desirability = validated_data.pop( F.DESIRABILITY, None )
            advanced_booking = validated_data.pop( F.ADVANCED_BOOKING, None )

            # Extract contact_info before creating location
            contact_info_data = validated_data.pop( F.CONTACT_INFO, None )

            location = Location.objects.create(
                trip = trip,
                subcategory = subcategory,
                desirability = desirability,
                advanced_booking = advanced_booking,
                **validated_data,
            )

            # Create contact info records if provided
            if contact_info_data:
                cls._create_contact_info( location, contact_info_data )

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
            if F.SUBCATEGORY_SLUG in validated_data:
                subcategory_slug = validated_data.pop( F.SUBCATEGORY_SLUG )
                if subcategory_slug:
                    location.subcategory = LocationSubCategory.objects.filter(
                        slug = subcategory_slug
                    ).first()
                else:
                    location.subcategory = None

            # Update simple fields if present
            # Explicit mapping: API field name -> model field name
            api_to_model_fields = {
                F.TITLE: 'title',
                F.LATITUDE: 'latitude',
                F.LONGITUDE: 'longitude',
                F.ELEVATION_FT: 'elevation_ft',
                F.GMM_ID: 'gmm_id',
                F.RATING: 'rating',
                F.DESIRABILITY: 'desirability',
                F.ADVANCED_BOOKING: 'advanced_booking',
                F.OPEN_DAYS_TIMES: 'open_days_times',
            }
            for api_field, model_field in api_to_model_fields.items():
                if api_field in validated_data:
                    setattr( location, model_field, validated_data[api_field] )

            location.save()

            # Handle location_notes if present (replace all strategy)
            if F.LOCATION_NOTES in validated_data:
                cls._replace_location_notes( location, validated_data[F.LOCATION_NOTES] )

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
            text = ( note_data.get( F.TEXT ) or '' ).strip()
            if not text:
                continue

            note = LocationNote(
                location = location,
                text = text,
                source_label = note_data.get( F.SOURCE_LABEL ) or '',
                source_url = note_data.get( F.SOURCE_URL ) or '',
                sort_order = sort_order,
            )
            apply_note_heuristics( note )
            notes_to_create.append( note )
            sort_order += 1

        # Bulk create all notes
        if notes_to_create:
            LocationNote.objects.bulk_create( notes_to_create )

    @classmethod
    def _create_contact_info(
        cls,
        location: Location,
        contact_info_data: List[Dict[str, Any]],
    ) -> None:
        """
        Create ContactInfo records for a location using bulk operations.

        Filters out empty values. Contact type is validated by the serializer
        and stored as lowercase string matching ContactType enum values.

        Args:
            location: The Location to create contacts for.
            contact_info_data: List of contact dicts with contact_type, value, label, is_primary.
        """
        contacts_to_create = []
        for info in contact_info_data:
            value = ( info.get( F.VALUE ) or '' ).strip()
            if not value:
                continue

            contact = ContactInfo(
                content_object = location,
                contact_type = info.get( F.CONTACT_TYPE ),
                value = value,
                label = info.get( F.LABEL ) or '',
                is_primary = info.get( F.IS_PRIMARY, False ),
            )
            contacts_to_create.append( contact )

        if contacts_to_create:
            ContactInfo.objects.bulk_create( contacts_to_create )
