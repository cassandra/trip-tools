import logging

from django.shortcuts import render

from tt.async_view import ModalView

from .context import TripPageContext
from .enums import TripPage
from .forms import TripForm
from .mixins import TripViewMixin
from .models import Trip

logger = logging.getLogger(__name__)


class TripCreateModalView(ModalView):

    def get_template_name(self) -> str:
        return 'trips/modals/trip-create.html'

    def get(self, request, *args, **kwargs):
        form = TripForm()
        context = {
            'form': form,
        }
        return self.modal_response(request, context=context)

    def post(self, request, *args, **kwargs):
        form = TripForm( request.POST )

        if form.is_valid():
            Trip.objects.create_with_owner(
                owner = request.user,
                **form.cleaned_data
            )

            return self.refresh_response( request )

        context = {
            'form': form,
        }
        return self.modal_response( request, context = context, status = 400 )


class TripHomeView( TripViewMixin, ModalView ):

    def get_template_name(self) -> str:
        return 'trips/pages/trip-home.html'

    def get(self, request, trip_id, *args, **kwargs):
        request_member = self.get_trip_member( request, trip_id = trip_id )
        self.assert_is_viewer( request_member )
        trip = request_member.trip

        request.view_parameters.trip_id = trip.pk
        request.view_parameters.to_session( request )

        trip_page_context = TripPageContext(
            active_page = TripPage.OVERVIEW,
            request_member = request_member,
        )

        context = {
            'trip_page': trip_page_context,
        }
        return render( request, 'trips/pages/trip-home.html', context )
