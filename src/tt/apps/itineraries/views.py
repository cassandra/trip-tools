from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.generic import View

from tt.apps.trips.context import TripPageContext
from tt.apps.trips.enums import TripPage
from tt.apps.trips.models import Trip


class ItineraryHomeView(LoginRequiredMixin, View):

    def get(self, request, trip_pk: int, *args, **kwargs) -> HttpResponse:
        trip = get_object_or_404(Trip, pk=trip_pk, user=request.user)

        trip_page_context = TripPageContext(
            trip=trip,
            active_page=TripPage.ITINERARY
        )

        context = {
            'trip_page': trip_page_context,
        }

        return render(request, 'itineraries/pages/itinerary-home.html', context)
