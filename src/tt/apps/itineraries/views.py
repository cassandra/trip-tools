from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.generic import View

from tt.apps.trips.context import TripPageContext
from tt.apps.trips.enums import TripPage, TripPermissionLevel
from tt.apps.trips.mixins import TripPermissionMixin
from tt.apps.trips.models import Trip


class ItineraryHomeView( LoginRequiredMixin, TripPermissionMixin, View ):

    def get(self, request, trip_pk: int, *args, **kwargs) -> HttpResponse:
        trip = get_object_or_404( Trip, pk = trip_pk )

        if not self.has_trip_permission( request.user, trip, TripPermissionLevel.VIEWER ):
            raise Http404( 'Trip not found' )

        trip_page_context = TripPageContext(
            trip=trip,
            active_page=TripPage.ITINERARY
        )

        context = {
            'trip_page': trip_page_context,
        }

        return render(request, 'itineraries/pages/itinerary-home.html', context)
