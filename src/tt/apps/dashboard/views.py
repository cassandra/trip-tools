import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import render
from django.views.generic import View

from tt.context import FeaturePageContext
from tt.enums import FeaturePageType

from .services import DashboardDisplayService

logger = logging.getLogger(__name__)


class DashboardHomeView(LoginRequiredMixin, View):

    def get(self, request, *args, **kwargs) -> HttpResponse:
        dashboard_trips = DashboardDisplayService.get_dashboard_trips_for_user(
            user = request.user,
        )

        feature_page_context = FeaturePageContext(
            active_page = FeaturePageType.DASHBOARD,
        )

        context = {
            'feature_page': feature_page_context,
            'dashboard_trips': dashboard_trips,
        }
        return render(request, 'dashboard/pages/dashboard_home.html', context)
