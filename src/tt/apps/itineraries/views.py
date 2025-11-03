from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import render
from django.views.generic import View

from tt.apps.trips.context import TripPageContext
from tt.apps.trips.enums import TripPage
from tt.apps.trips.mixins import TripViewMixin


class ItineraryHomeView( LoginRequiredMixin, TripViewMixin, View ):

    def get(self, request, trip_id: int, *args, **kwargs) -> HttpResponse:
        trip_member = self.get_trip_member( request, trip_id = trip_id )
        self.assert_is_viewer( trip_member )

        trip_page_context = TripPageContext(
            trip = trip_member.trip,
            active_page = TripPage.ITINERARY
        )
        context = {
            'trip_page': trip_page_context,
        }
        return render(request, 'itineraries/pages/itinerary-home.html', context)
