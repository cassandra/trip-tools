from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import render
from django.views.generic import View

from tt.apps.dashboard.context import DashboardPageContext
from tt.apps.dashboard.enums import DashboardPage


class TripImagesHomeView(LoginRequiredMixin, View):
    """
    Home view for image management of images used for trips.
    """

    def get(self, request, *args, **kwargs) -> HttpResponse:
        dashboard_page_context = DashboardPageContext(
            active_page = DashboardPage.IMAGES,
        )

        context = {
            'dashboard_page': dashboard_page_context,
        }
        return render(request, 'images/pages/trip_images_home.html', context)
