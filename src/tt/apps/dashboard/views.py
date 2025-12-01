import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import render
from django.views.generic import View

from tt.apps.members.models import TripMember
from tt.apps.trips.enums import TripStatus

from tt.context import FeaturePageContext
from tt.enums import FeaturePageType

logger = logging.getLogger(__name__)


class DashboardView(LoginRequiredMixin, View):
    """Dashboard categorizes trips by ownership and status."""

    def get(self, request, *args, **kwargs) -> HttpResponse:
        # Single query: get all memberships with trips prefetched
        memberships = list(
            TripMember.objects
            .filter( user = request.user )
            .select_related('trip')
            .order_by('-trip__created_datetime')
        )

        # In-memory categorization by ownership and status
        recent_trips = []

        for membership in memberships:
            trip = membership.trip
            if trip.trip_status in [ TripStatus.UPCOMING, TripStatus.CURRENT ]:
                recent_trips.append( trip )
            continue
        
        feature_page_context = FeaturePageContext(
            active_page = FeaturePageType.DASHBOARD,
        )

        context = {
            'feature_page': feature_page_context,
            'recent_trips': recent_trips[0:3],
        }
        return render(request, 'dashboard/pages/dashboard_home.html', context)
