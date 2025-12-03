import logging
from datetime import date as date_class
from typing import Tuple
from uuid import UUID

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.views.generic import View

from tt.apps.journal.models import Journal
from tt.apps.images.enums import UploadStatus
from tt.apps.images.services import ImageUploadService
from tt.apps.images.views import EntityImagePickerView, EntityImageUploadView
from tt.apps.members.models import TripMember

from tt.async_view import ModalView
from tt.context import FeaturePageContext
from tt.enums import FeaturePageType

from .context import TripPageContext
from .enums import TripPage
from .forms import TripForm
from .mixins import TripViewMixin
from .models import Trip
from .services import TripsHomeDisplayService, TripOverviewBuilder

logger = logging.getLogger(__name__)


class TripsHomeView(LoginRequiredMixin, View):

    def get(self, request, *args, **kwargs) -> HttpResponse:
        # Use service for business logic and categorization
        trip_data = TripsHomeDisplayService.get_categorized_trips_for_user(request.user)

        feature_page_context = FeaturePageContext(
            active_page = FeaturePageType.TRIPS,
        )
        context = {
            'feature_page': feature_page_context,
            'current_trips': trip_data.current_trips,
            'shared_trips': trip_data.shared_trips,
            'past_trips': trip_data.past_trips,
            'total_trips': trip_data.total_trips,
        }
        return render(request, 'trips/pages/trips_home.html', context)

    
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
            redirect_url = reverse( 'trips_trip_overview', kwargs = { 'trip_uuid': trip.uuid } )
            return self.redirect_response( request, redirect_url )

        context = {
            'form': form,
        }
        return self.modal_response( request, context = context, status = 400 )


class TripOverviewView( TripViewMixin, View ):

    def get(self, request, trip_uuid : UUID, *args, **kwargs):
        request_member = self.get_trip_member( request, trip_uuid = trip_uuid )
        self.assert_is_viewer( request_member )
        trip = request_member.trip

        request.view_parameters.trip_id = trip.pk
        request.view_parameters.to_session( request )

        journal = Journal.objects.get_primary_for_trip( trip )

        overview_data = TripOverviewBuilder.build(
            trip = trip,
            journal = journal,
            request_member = request_member,
        )
        trip_page_context = TripPageContext(
            active_page = TripPage.OVERVIEW,
            request_member = request_member,
        )
        context = {
            'trip_page': trip_page_context,
            'trip': trip,
            'overview_data': overview_data,
        }
        return render( request, 'trips/pages/trip_overview.html', context )


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


class TripImagePickerView( EntityImagePickerView ):

    def get_template_name(self) -> str:
        return 'trips/modals/trip_image_picker.html'

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
        return (date_class.today(), 'UTC')

    def get_trip_from_entity(self, entity: Trip) -> Trip:
        """Trip entity is already a Trip, return as-is."""
        return entity

    def get_picker_url(self, entity: Trip) -> str:
        return reverse('trips_trip_image_picker', kwargs={'trip_uuid': entity.uuid})

    def get_upload_url(self, entity: Trip) -> str:
        return reverse('trips_trip_image_upload', kwargs={'trip_uuid': entity.uuid})


class TripImageUploadView(EntityImageUploadView):
    """
    Single-image upload mode - automatically sets uploaded image as
    Trip's reference image and triggers page refresh on success.
    """

    def get_template_name(self) -> str:
        return 'trips/modals/trip_image_upload.html'

    def get_max_files(self) -> int:
        return 1

    def check_permission(self, request, *args, **kwargs) -> None:
        trip_uuid = kwargs.get('trip_uuid')
        request_member = self.get_trip_member(request, trip_uuid=trip_uuid)
        self.assert_is_editor(request_member)

    def get_upload_url(self, request, *args, **kwargs) -> str:
        trip_uuid = kwargs.get('trip_uuid')
        return reverse('trips_trip_image_upload', kwargs={'trip_uuid': trip_uuid})

    def post(self, request, *args, **kwargs):
        """
        Handle upload and automatically set as Trip's reference image.

        On successful upload, sets the image as the Trip's reference image.
        JavaScript handles page refresh via onComplete callback.
        """

        trip_uuid = kwargs.get('trip_uuid')
        request_member = self.get_trip_member(request, trip_uuid=trip_uuid)
        self.assert_is_editor(request_member)
        trip = request_member.trip

        uploaded_files = request.FILES.getlist('files')

        if not uploaded_files:
            return JsonResponse({'error': 'No file provided'}, status=400)

        if len(uploaded_files) > 1:
            return JsonResponse({'error': 'Only one image allowed'}, status=400)

        # Process the single file
        service = ImageUploadService()
        result = service.process_uploaded_image(
            uploaded_files[0],
            request.user,
            request=request,
        )

        if result.status == UploadStatus.SUCCESS:
            trip.reference_image = result.trip_image
            trip.save(update_fields=['reference_image'])

            # Return success - JS onComplete callback handles page refresh
            return JsonResponse({'files': [result.to_dict()]})

        return JsonResponse({
            'error': result.error_message or 'Upload failed'
        }, status=400)
