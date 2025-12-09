from uuid import UUID

from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from tt.apps.api.views import TtApiView
from tt.apps.trips.mixins import TripViewMixin
from tt.apps.trips.models import Trip

from .serializers import TripSerializer


class TripCollectionView( TtApiView ):
    """
    List all trips for the authenticated user.

    GET /api/v1/trips/
    Returns all trips where user is a member (any permission level).
    """
    permission_classes = [ IsAuthenticated ]

    def get( self, request: Request ) -> Response:
        trips = Trip.objects.for_user( request.user ).order_by( '-created_datetime' )
        serializer = TripSerializer( trips, many = True )
        return Response( serializer.data )


class TripItemView( TripViewMixin, TtApiView ):
    """
    Get a single trip by UUID.

    GET /api/v1/trips/{uuid}/
    Returns trip details if user is a member.
    """
    permission_classes = [ IsAuthenticated ]

    def get( self, request: Request, trip_uuid: UUID ) -> Response:
        trip_member = self.get_trip_member( request, trip_uuid = trip_uuid )
        self.assert_is_viewer( trip_member )

        serializer = TripSerializer( trip_member.trip )
        return Response( serializer.data )
