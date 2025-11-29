import logging
from uuid import UUID

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import render
from django.views.generic import View

from tt.apps.trips.context import TripPageContext
from tt.apps.trips.enums import TripPage
from tt.apps.trips.mixins import TripViewMixin

logger = logging.getLogger(__name__)


class ReviewsHomeView( LoginRequiredMixin, TripViewMixin, View ):

    def get(self, request,trip_uuid: UUID, *args, **kwargs) -> HttpResponse:
        request_member = self.get_trip_member( request, trip_uuid = trip_uuid )
        self.assert_is_viewer( request_member )

        trip_page_context = TripPageContext(
            active_page = TripPage.REVIEWS,
            request_member = request_member,
        )
        context = {
            'trip_page': trip_page_context,
        }
        return render(request, 'reviews/pages/reviews_home.html', context)
