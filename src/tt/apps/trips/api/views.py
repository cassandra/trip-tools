from uuid import UUID

from django.db import IntegrityError
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from tt.apps.api.views import TtApiView
from tt.apps.members.models import TripMember
from tt.apps.trips.mixins import TripViewMixin
from tt.apps.trips.models import Trip
from tt.apps.trips.services import TripService

from .serializers import TripSerializer


class TripCollectionView( TtApiView ):
    """
    List or create trips for the authenticated user.

    GET /api/v1/trips/
    Returns all trips where user is a member (any permission level).

    POST /api/v1/trips/
    Creates a new trip. User becomes OWNER.
    """
    permission_classes = [ IsAuthenticated ]

    def get( self, request: Request ) -> Response:
        trips = Trip.objects.for_user( request.user ).order_by( '-created_datetime' )
        serializer = TripSerializer( trips, many = True )
        return Response( serializer.data )

    def post( self, request: Request ) -> Response:
        serializer = TripSerializer( data = request.data )
        serializer.is_valid( raise_exception = True )

        try:
            trip = Trip.objects.create_with_owner(
                owner = request.user,
                **serializer.validated_data,
            )
        except IntegrityError:
            return Response(
                { 'error': 'A trip with this GMM map ID already exists' },
                status = status.HTTP_409_CONFLICT
            )

        output_serializer = TripSerializer( trip )
        return Response( output_serializer.data, status = status.HTTP_201_CREATED )


class TripItemView( TripViewMixin, TtApiView ):
    """
    Get or update a single trip by UUID.

    GET /api/v1/trips/{uuid}/
    Returns trip details if user is a member.

    PATCH /api/v1/trips/{uuid}/
    Updates trip fields. Requires EDITOR permission.
    """
    permission_classes = [ IsAuthenticated ]

    def get( self, request: Request, trip_uuid: UUID ) -> Response:
        trip_member = self.get_trip_member( request, trip_uuid = trip_uuid )
        self.assert_is_viewer( trip_member )

        serializer = TripSerializer( trip_member.trip )
        return Response( serializer.data )

    def patch( self, request: Request, trip_uuid: UUID ) -> Response:
        trip_member = self.get_trip_member( request, trip_uuid = trip_uuid )
        self.assert_is_editor( trip_member )

        serializer = TripSerializer( trip_member.trip, data = request.data, partial = True )
        serializer.is_valid( raise_exception = True )

        trip = TripService.update(
            trip = trip_member.trip,
            validated_data = serializer.validated_data,
        )

        # Re-serialize with updated data
        output_serializer = TripSerializer( trip )
        return Response( output_serializer.data )


class TripByGmmMapView( TtApiView ):
    """
    Get a trip by its GMM map ID.

    GET /api/v1/trips/by-gmm-map/{gmm_map_id}/
    Returns trip if found and user is a member, 404 otherwise.
    """
    permission_classes = [ IsAuthenticated ]

    def get( self, request: Request, gmm_map_id: str ) -> Response:
        trip = Trip.objects.filter( gmm_map_id = gmm_map_id ).first()

        if not trip:
            raise NotFound( 'No trip found with this GMM map ID' )

        # Check user has access to this trip
        # Returns 404 (not 403) to avoid leaking existence of trips
        trip_member = TripMember.objects.filter(
            trip = trip,
            user = request.user
        ).first()

        if not trip_member:
            raise NotFound( 'No trip found with this GMM map ID' )

        serializer = TripSerializer( trip )
        return Response( serializer.data )
