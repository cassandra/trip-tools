import logging

from django.db import transaction
from django.http import Http404
from django.shortcuts import render

from tt.async_view import ModalView

from .context import TripPageContext
from .enums import TripPage, TripPermissionLevel
from .forms import TripForm
from .mixins import TripPermissionMixin
from .models import Trip, TripMember

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
            with transaction.atomic():
                trip = form.save( commit = False )
                trip.save()

                TripMember.objects.create(
                    trip = trip,
                    user = request.user,
                    permission_level = TripPermissionLevel.OWNER,
                    added_by = request.user,
                )

            return self.refresh_response( request )

        context = {
            'form': form,
        }
        return self.modal_response( request, context = context, status = 400 )


class TripHomeView( TripPermissionMixin, ModalView ):

    def get_template_name(self) -> str:
        return 'trips/pages/trip-home.html'

    def get(self, request, trip_id, *args, **kwargs):
        try:
            trip = Trip.objects.get( pk = trip_id )
        except Trip.DoesNotExist:
            raise Http404( 'Trip not found' )

        if not self.has_trip_permission( request.user, trip, TripPermissionLevel.VIEWER ):
            raise Http404( 'Trip not found' )

        request.view_parameters.trip_id = trip.pk
        request.view_parameters.to_session( request )

        trip_page_context = TripPageContext(
            trip = trip,
            active_page = TripPage.OVERVIEW,
        )

        context = {
            'trip_page': trip_page_context,
        }
        return render( request, 'trips/pages/trip-home.html', context )
