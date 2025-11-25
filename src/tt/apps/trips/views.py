import logging
from datetime import date as date_class
from typing import Tuple
from uuid import UUID

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.urls import reverse

from tt.apps.images.views import EntityImagePickerView
from tt.apps.members.models import TripMember
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
            trip = Trip.objects.create_with_owner(
                owner = request.user,
                **form.cleaned_data
            )
            redirect_url = reverse( 'trips_home', kwargs = { 'trip_uuid': trip.uuid } )
            return self.redirect_response( request, redirect_url )

        context = {
            'form': form,
        }
        return self.modal_response( request, context = context, status = 400 )


class TripHomeView( TripViewMixin, ModalView ):

    def get_template_name(self) -> str:
        return 'trips/pages/trip-home.html'

    def get(self, request, trip_uuid : UUID, *args, **kwargs):
        request_member = self.get_trip_member( request, trip_uuid = trip_uuid )
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


class TripEditModalView( LoginRequiredMixin, TripViewMixin, ModalView ):

    def get_template_name(self) -> str:
        return 'trips/modals/trip_edit.html'

    def get(self, request, trip_uuid: UUID, *args, **kwargs) -> HttpResponse:
        request_member = self.get_trip_member( request, trip_uuid = trip_uuid )
        self.assert_is_editor( request_member )
        trip = request_member.trip

        form = TripForm( instance = trip )

        context = {
            'form': form,
            'trip': trip,
        }
        return self.modal_response( request, context = context )

    def post(self, request, trip_uuid: UUID, *args, **kwargs) -> HttpResponse:
        request_member = self.get_trip_member( request, trip_uuid = trip_uuid )
        self.assert_is_editor( request_member )
        trip = request_member.trip

        form = TripForm( request.POST, instance = trip )

        if form.is_valid():
            form.save()
            return self.refresh_response( request )

        context = {
            'form': form,
            'trip': trip,
        }
        return self.modal_response( request, context = context, status = 400 )


class TripReferenceImagePickerView(EntityImagePickerView):
    """
    Modal view for selecting a reference image for a Trip.

    Extends EntityImagePickerView with Trip-specific configuration.
    """

    def get_template_name(self) -> str:
        return 'trips/modals/trip_reference_image_picker.html'

    def get_entity_model(self):
        return Trip

    def get_entity_uuid_param_name(self) -> str:
        return 'trip_uuid'

    def check_permission(self, request, entity: Trip) -> None:
        """Verify user has editor permission for the trip."""
        request_member = get_object_or_404(
            TripMember,
            trip=entity,
            user=request.user,
        )
        self.assert_is_editor(request_member)

    def get_default_date_and_timezone(self, entity: Trip) -> Tuple[date_class, str]:
        """
        Determine default date and timezone for Trip image picker.

        Uses today's date and UTC timezone as default.
        """
        return (date_class.today(), 'UTC')

    def get_trip_from_entity(self, entity: Trip) -> Trip:
        """Trip entity is already a Trip, return as-is."""
        return entity

    def get_picker_url(self, entity: Trip) -> str:
        """Return the URL for the Trip reference image picker."""
        return reverse('trip_reference_image_picker', kwargs={'trip_uuid': entity.uuid})
