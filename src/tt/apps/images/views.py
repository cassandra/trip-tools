import logging
import pytz
from abc import ABC, abstractmethod
from datetime import date as date_class
from typing import Optional, Tuple

from uuid import UUID

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import BadRequest, PermissionDenied
from django.db import models
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.generic import View

from tt.apps.common.antinode import http_response
from tt.apps.dashboard.context import DashboardPageContext
from tt.apps.dashboard.enums import DashboardPage
from tt.apps.members.models import TripMember
from tt.apps.trips.context import TripPageContext
from tt.apps.trips.enums import TripPage
from tt.apps.trips.mixins import TripViewMixin
from tt.apps.trips.models import Trip
from tt.async_view import ModalView

from .context import ImagePageContext
from .enums import ImageAccessRole
from .forms import TripImageEditForm
from .helpers import TripImageHelpers
from .models import TripImage
from .services import ImagePickerService, ImageUploadService, HEIF_SUPPORT_AVAILABLE

logger = logging.getLogger(__name__)


class ImagesHomeView( LoginRequiredMixin, View ):
    """
    Home view for image management of images used for trips.
    """

    MAX_LATEST_IMAGES = 50
    
    def get(self, request, *args, **kwargs) -> HttpResponse:
        dashboard_page_context = DashboardPageContext(
            active_page=DashboardPage.IMAGES,
        )

        # Query uploaded images for the current user
        uploaded_images = TripImage.objects.for_user( request.user )[0:self.MAX_LATEST_IMAGES]

        context = {
            'dashboard_page': dashboard_page_context,
            'uploaded_images': uploaded_images,
            'heif_support_available': HEIF_SUPPORT_AVAILABLE,
        }
        return render(request, 'images/pages/trip_images_home.html', context)

    def post(self, request, *args, **kwargs) -> JsonResponse:
        """
        Handle multiple image uploads with EXIF extraction and resizing.

        Returns JSON with upload results for each file.
        """
        uploaded_files = request.FILES.getlist('files')

        if not uploaded_files:
            logger.debug(
                f"Upload rejected: User {request.user.email} (ID: {request.user.id}) "
                f"submitted request with no files"
            )
            return JsonResponse(
                {'error': 'No files provided'},
                status=400,
            )

        # Use ImageUploadService for processing
        service = ImageUploadService()
        results = []
        success_count = 0
        error_count = 0

        for uploaded_file in uploaded_files:
            result = service.process_uploaded_image(uploaded_file, request.user, request=request)
            results.append(result)

            # Import UploadStatus for comparison
            from tt.apps.images.enums import UploadStatus
            if result.status == UploadStatus.SUCCESS:
                success_count += 1
            else:
                error_count += 1

        # Log upload summary
        logger.debug(
            f"Upload batch completed: User {request.user.email} (ID: {request.user.id}) - "
            f"{success_count} succeeded, {error_count} failed out of {len(uploaded_files)} files"
        )

        # Convert dataclass results to dicts for JSON response
        results_dicts = [result.to_dict() for result in results]

        # Return 200 even if some files failed - client checks individual status
        return JsonResponse({'files': results_dicts})


class ImageInspectView( LoginRequiredMixin, TripViewMixin, ModalView ):
    """
    Modal view for inspecting/previewing a trip image with full metadata.

    Displays the web-sized image along with all available metadata including
    EXIF data, upload information, and GPS coordinates if available.

    Supports two access modes:
    1. With trip context (?trip_uuid=X): Check trip membership permission
    2. Without trip context: Only uploader has access
    """

    def get_template_name(self ) -> str:
        # We override this when editing is allowed
        return 'images/modals/trip_image_inspect_view.html'

    def get_effective_template_name(self, image_access_role : ImageAccessRole ) -> str:
        if image_access_role.can_edit:
            return 'images/modals/trip_image_inspect_edit.html'
        return self.get_template_name()

    def get(self, request, image_uuid: UUID, *args, **kwargs) -> HttpResponse:

        image_page_context = self.get_image_page_context( request, image_uuid, *args, **kwargs )

        if not image_page_context.image_access_role.can_access:
            raise PermissionDenied('You do not have permission to access this image.')

        trip_image_form = None
        if image_page_context.image_access_role.can_edit:
            trip_image_form = TripImageEditForm( instance = image_page_context.trip_image )

        context = {
            'image_page_context': image_page_context,
            'trip_image_form': trip_image_form,
        }
        template_name = self.get_effective_template_name(
            image_access_role = image_page_context.image_access_role,
        )
        return self.modal_response( request, context = context, template_name = template_name )

    def post(self, request, image_uuid: UUID, *args, **kwargs) -> HttpResponse:

        image_page_context = self.get_image_page_context( request, image_uuid, *args, **kwargs )
            
        if not image_page_context.image_access_role.can_edit:
            raise PermissionDenied('You do not have permission to access this image.')

        trip_image_form = TripImageEditForm( request.POST, instance = image_page_context.trip_image )

        if trip_image_form.is_valid():
            trip_image_form.save( user = request.user )
            return self.refresh_response( request )

        # Form has errors - re-render with errors
        context = {
            'image_page_context': image_page_context,
            'trip_image_form': trip_image_form,
        }
        template_name = self.get_effective_template_name(
            image_access_role = image_page_context.image_access_role,
        )
        return self.modal_response( request, context = context, template_name = template_name, status = 400 )

    def get_image_page_context( self, request, image_uuid: UUID, *args, **kwargs ) -> ImagePageContext:

        trip_image = get_object_or_404( TripImage, uuid = image_uuid )

        # Determine trip context (optional - image can be accessed outside trip context)
        trip_page_context = None
        try:
            trip_uuid_str = request.GET.get('trip_uuid')
            request_member = self.get_trip_member( request, trip_uuid = trip_uuid_str )
            trip_page_context = TripPageContext(
                active_page = TripPage.IMAGES,
                request_member = request_member,
            )
        except (TypeError, ValueError, BadRequest):
            pass
  
        image_access_role = TripImageHelpers.get_image_access_mode(
            user = request.user,
            trip_image = trip_image,
            trip_page_context = trip_page_context,
        )
        return ImagePageContext(
            user = request.user,
            trip_image = trip_image,
            image_access_role = image_access_role,
            trip_page_context = trip_page_context,
        )


class EntityImagePickerView(LoginRequiredMixin, TripViewMixin, ModalView, ABC):
    """
    Abstract base view for selecting reference images for any entity type.

    This view provides a generic image picker modal that can be configured
    for different entity types (Trip, Journal, etc.).
    """

    @abstractmethod
    def get_entity_model(self) -> type[models.Model]:
        pass

    @abstractmethod
    def get_entity_uuid_param_name(self) -> str:
        pass

    @abstractmethod
    def check_permission(self, request, entity) -> None:
        """
        Should raise PermissionDenied if user lacks permission.
        """
        pass

    @abstractmethod
    def get_default_date_and_timezone(self, entity) -> Tuple[date_class, str]:
        pass

    @abstractmethod
    def get_template_name(self) -> str:
        """Return the template path for the image picker modal."""
        pass

    @abstractmethod
    def get_picker_url(self, entity) -> str:
        """Return the URL for the image picker form action."""
        pass

    def get_trip_from_entity(self, entity) -> Trip:
        """
        Extract the Trip from the entity.

        Default implementation assumes entity has a 'trip' attribute.
        Override if needed for other entity types.

        Raises:
            ValueError: If the result is not a Trip instance.
        """
        if hasattr(entity, 'trip'):
            result = entity.trip
        else:
            result = entity

        if not isinstance(result, Trip):
            raise ValueError(
                f"get_trip_from_entity must return a Trip instance, "
                f"got {type(result).__name__}. Override this method in your subclass."
            )
        return result

    def get( self, request, *args, **kwargs ) -> HttpResponse:

        entity_uuid_param = self.get_entity_uuid_param_name()
        entity_uuid = kwargs.get(entity_uuid_param)

        entity = get_object_or_404(
            self.get_entity_model(),
            uuid = entity_uuid,
        )
        self.check_permission( request, entity )

        trip = self.get_trip_from_entity( entity )

        selected_date, selected_timezone = self._get_accessible_images_date_and_timezone(
            entity = entity,
            request_date_str = request.GET.get('date'),
        )
        accessible_images = ImagePickerService.get_accessible_images_for_image_picker(
            trip = trip,
            user = request.user,
            date = selected_date,
            timezone = selected_timezone,
        )
        context = {
            'entity': entity,
            'accessible_images': accessible_images,
            'trip': trip,
            'selected_date': selected_date,
            'picker_url': self.get_picker_url(entity),
        }
        return self.modal_response(request, context)

    def post(self, request, *args, **kwargs) -> HttpResponse:

        entity_uuid_param = self.get_entity_uuid_param_name()
        entity_uuid = kwargs.get(entity_uuid_param)

        entity = get_object_or_404(
            self.get_entity_model(),
            uuid=entity_uuid,
        )
        self.check_permission(request, entity)

        trip = self.get_trip_from_entity(entity)

        image_uuid_str = request.POST.get('image_uuid')
        if not image_uuid_str:
            return http_response( {'error': 'Image UUID required'}, status = 400 )

        try:
            image_uuid = UUID(image_uuid_str)
        except ValueError:
            return http_response( {'error': 'Invalid UUID format'}, status = 400 )

        trip_image = get_object_or_404( TripImage, uuid = image_uuid )

        member_user_ids = TripMember.objects.filter(
            trip = trip
        ).values_list( 'user_id', flat = True )

        if trip_image.uploaded_by_id not in member_user_ids:
            return http_response( {'error': 'Image not accessible'}, status = 403 )

        entity.reference_image = trip_image
        entity.save( update_fields = ['reference_image'] )

        return self.refresh_response(request)

    def _get_accessible_images_date_and_timezone(
        self,
        entity,
        request_date_str: Optional[str]
    ) -> Tuple[date_class, str]:
        """
        Determine the date and timezone to use for image filtering.

        Priority:
        1. Date from request parameter (if valid)
        2. Date from entity's current reference image (if set)
        3. Default date from subclass implementation
        """
        # Priority 1: Use date from request if provided
        if request_date_str:
            try:
                selected_date = date_class.fromisoformat(request_date_str)
                _, default_timezone = self.get_default_date_and_timezone(entity)
                return (selected_date, default_timezone)
            except (TypeError, ValueError):
                raise BadRequest('Invalid date format')

        # Priority 2: Use date from current reference image if available
        if entity.reference_image and entity.reference_image.datetime_utc:
            ref_img = entity.reference_image
            # Use image's timezone if available, otherwise fall back to entity timezone
            _, default_timezone = self.get_default_date_and_timezone(entity)
            selected_timezone = ref_img.timezone if ref_img.timezone else default_timezone
            # Convert UTC datetime to the selected timezone to get the correct date
            tz = pytz.timezone(selected_timezone)
            selected_date = ref_img.datetime_utc.astimezone(tz).date()
            return (selected_date, selected_timezone)

        # Priority 3: Use default from subclass
        return self.get_default_date_and_timezone(entity)
