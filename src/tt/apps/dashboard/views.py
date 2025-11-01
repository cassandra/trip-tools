import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import render
from django.views.generic import View

from tt.apps.trips.enums import TripStatus
from tt.apps.trips.models import Trip

logger = logging.getLogger(__name__)


class DashboardView(LoginRequiredMixin, View):
    """Dashboard combines UPCOMING and CURRENT trips in main section per business requirement."""

    def get(self, request, *args, **kwargs) -> HttpResponse:
        # Single query with evaluation to avoid N+1 queries
        all_trips = list(Trip.objects.for_user(request.user).order_by('-created_datetime'))

        # In-memory filtering (no additional queries)
        upcoming_trips = [
            trip for trip in all_trips
            if trip.trip_status in [TripStatus.UPCOMING, TripStatus.CURRENT]
        ]
        past_trips = [
            trip for trip in all_trips
            if trip.trip_status == TripStatus.PAST
        ]        
        context = {
            'upcoming_trips': upcoming_trips,
            'past_trips': past_trips,
            'total_trips': len(all_trips),
        }

        return render(request, 'dashboard/pages/dashboard.html', context)
