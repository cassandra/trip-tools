from uuid import UUID

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from tt.apps.api.constants import APIFields as F
from tt.apps.api.views import TtApiView
from tt.apps.locations.models import Location
from tt.apps.locations.services import LocationService
from tt.apps.trips.mixins import TripViewMixin

from .serializers import LocationSerializer


class LocationCollectionView( TripViewMixin, TtApiView ):
    """
    List or create locations.

    GET /api/v1/locations/?trip={uuid}
    Returns all locations for specified trip.

    POST /api/v1/locations/
    Creates new location. Requires trip_uuid in body.
    """
    permission_classes = [ IsAuthenticated ]

    def get( self, request: Request ) -> Response:
        """List locations for a trip."""
        trip_uuid_str = request.query_params.get( 'trip' )
        if not trip_uuid_str:
            return Response(
                { F.ERROR: 'trip query parameter is required' },
                status = status.HTTP_400_BAD_REQUEST,
            )

        try:
            trip_uuid = UUID( trip_uuid_str )
        except ValueError:
            return Response(
                { F.ERROR: 'Invalid trip UUID format' },
                status = status.HTTP_400_BAD_REQUEST,
            )

        trip_member = self.get_trip_member( request, trip_uuid = trip_uuid )
        self.assert_is_viewer( trip_member )

        locations = Location.objects.filter(
            trip = trip_member.trip
        ).select_related( 'subcategory', 'trip' ).prefetch_related(
            'location_notes'
        ).order_by( 'title' )

        serializer = LocationSerializer( locations, many = True )
        return Response( serializer.data )

    def post( self, request: Request ) -> Response:
        """Create a new location."""
        trip_uuid_str = request.data.get( F.TRIP_UUID )
        if not trip_uuid_str:
            return Response(
                { F.ERROR: 'trip_uuid is required' },
                status = status.HTTP_400_BAD_REQUEST,
            )

        try:
            trip_uuid = UUID( str( trip_uuid_str ) )
        except ValueError:
            return Response(
                { F.ERROR: 'Invalid trip_uuid format' },
                status = status.HTTP_400_BAD_REQUEST,
            )

        trip_member = self.get_trip_member( request, trip_uuid = trip_uuid )
        self.assert_is_editor( trip_member )

        serializer = LocationSerializer( data = request.data )
        serializer.is_valid( raise_exception = True )

        location = LocationService.create(
            trip = trip_member.trip,
            validated_data = serializer.validated_data,
        )

        # Re-serialize with related data
        output_serializer = LocationSerializer( location )
        return Response( output_serializer.data, status = status.HTTP_201_CREATED )


class LocationItemView( TripViewMixin, TtApiView ):
    """
    Get, update, or delete a single location.

    GET /api/v1/locations/{uuid}/
    PATCH /api/v1/locations/{uuid}/
    DELETE /api/v1/locations/{uuid}/
    """
    permission_classes = [ IsAuthenticated ]

    def _get_location_and_member( self, request: Request, location_uuid: UUID ):
        """
        Get location and verify access.
        Returns (location, trip_member) tuple.
        Returns (None, None) if location not found.
        """
        try:
            location = Location.objects.select_related(
                'trip', 'subcategory'
            ).prefetch_related(
                'location_notes'
            ).get( uuid = location_uuid )
        except Location.DoesNotExist:
            return None, None

        trip_member = self.get_trip_member( request, trip_uuid = location.trip.uuid )
        return location, trip_member

    def get( self, request: Request, location_uuid: UUID ) -> Response:
        """Get single location."""
        location, trip_member = self._get_location_and_member( request, location_uuid )
        if not location:
            return Response( status = status.HTTP_404_NOT_FOUND )

        self.assert_is_viewer( trip_member )

        serializer = LocationSerializer( location )
        return Response( serializer.data )

    def patch( self, request: Request, location_uuid: UUID ) -> Response:
        """Update location."""
        location, trip_member = self._get_location_and_member( request, location_uuid )
        if not location:
            return Response( status = status.HTTP_404_NOT_FOUND )

        self.assert_is_editor( trip_member )

        serializer = LocationSerializer( location, data = request.data, partial = True )
        serializer.is_valid( raise_exception = True )

        location = LocationService.update(
            location = location,
            validated_data = serializer.validated_data,
        )

        # Re-serialize with updated data
        output_serializer = LocationSerializer( location )
        return Response( output_serializer.data )

    def delete( self, request: Request, location_uuid: UUID ) -> Response:
        """Delete location."""
        location, trip_member = self._get_location_and_member( request, location_uuid )
        if not location:
            return Response( status = status.HTTP_404_NOT_FOUND )

        self.assert_is_editor( trip_member )

        location.delete()
        return Response( status = status.HTTP_204_NO_CONTENT )
