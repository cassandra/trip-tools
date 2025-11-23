import logging
from uuid import UUID

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import BadRequest, PermissionDenied
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.generic import View

from tt.apps.dashboard.context import DashboardPageContext
from tt.apps.dashboard.enums import DashboardPage
from tt.apps.trips.context import TripPageContext
from tt.apps.trips.enums import TripPage
from tt.apps.trips.mixins import TripViewMixin
from tt.async_view import ModalView

from .context import ImagePageContext
from .enums import ImageAccessRole
from .forms import TripImageEditForm
from .helpers import TripImageHelpers
from .models import TripImage
from .services import ImageUploadService, HEIF_SUPPORT_AVAILABLE

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
