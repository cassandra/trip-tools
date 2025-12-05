from uuid import UUID

from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from tt.apps.locations.models import Location
from tt.apps.trips.mixins import TripViewMixin
from .serializers import LocationSerializer


class LocationListView(TripViewMixin, APIView):
    """
    List locations for a trip.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request: Request, trip_uuid: UUID) -> Response:

        request_member = self.get_trip_member( request, trip_uuid = trip_uuid )
        self.assert_is_viewer( request_member )

        locations = Location.objects.filter(
            trip = request_member.trip
        ).select_related('subcategory', 'trip')

        serializer = LocationSerializer( locations, many = True )
        return Response( serializer.data )
