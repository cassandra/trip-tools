import logging

from django.db import transaction
from django.http import Http404
from django.shortcuts import render

from tt.async_view import ModalView

from .forms import TripForm
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
        form = TripForm(request.POST)

        if form.is_valid():
            with transaction.atomic():
                trip = form.save(commit=False)
                trip.user = request.user
                trip.save()

            return self.refresh_response(request)

        context = {
            'form': form,
        }
        return self.modal_response(request, context=context, status=400)


class TripHomeView(ModalView):

    def get_template_name(self) -> str:
        return 'trips/pages/trip-home.html'

    def get(self, request, trip_id, *args, **kwargs):
        try:
            trip = Trip.objects.get(pk=trip_id, user=request.user)
        except Trip.DoesNotExist:
            raise Http404('Trip not found')

        # Set the trip in session using ViewParameters
        request.view_parameters.trip_id = trip.pk
        request.view_parameters.to_session(request)

        context = {
            'trip': trip,
        }
        return render(request, 'trips/pages/trip-home.html', context)
