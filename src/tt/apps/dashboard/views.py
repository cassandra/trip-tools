import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import render
from django.views.generic import View

from tt.apps.members.models import TripMember
from tt.apps.trips.enums import TripPermissionLevel, TripStatus

from .context import DashboardPageContext
from .enums import DashboardPage

logger = logging.getLogger(__name__)


class DashboardView(LoginRequiredMixin, View):
    """Dashboard categorizes trips by ownership and status."""

    def get(self, request, *args, **kwargs) -> HttpResponse:
        # Single query: get all memberships with trips prefetched
        memberships = list(
            TripMember.objects
            .filter(user=request.user)
            .select_related('trip')
            .order_by('-trip__created_datetime')
        )

        # In-memory categorization by ownership and status
        owned_upcoming_trips = []
        shared_trips = []
        owned_past_trips = []

        for membership in memberships:
            trip = membership.trip
            is_owner = membership.permission_level == TripPermissionLevel.OWNER

            if trip.trip_status in [TripStatus.UPCOMING, TripStatus.CURRENT]:
                if is_owner:
                    owned_upcoming_trips.append(trip)
                else:
                    shared_trips.append(trip)
            elif trip.trip_status == TripStatus.PAST and is_owner:
                owned_past_trips.append(trip)

        dashboard_page_context = DashboardPageContext(
            active_page = DashboardPage.TRIPS,
        )

        context = {
            'dashboard_page': dashboard_page_context,
            'owned_upcoming_trips': owned_upcoming_trips,
            'shared_trips': shared_trips,
            'owned_past_trips': owned_past_trips,
            'total_trips': len(memberships),
        }

        return render(request, 'dashboard/pages/dashboard.html', context)
