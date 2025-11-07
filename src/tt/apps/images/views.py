import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.generic import View

from tt.apps.dashboard.context import DashboardPageContext
from tt.apps.dashboard.enums import DashboardPage
from tt.async_view import ModalView

from .models import TripImage
from .services import ImageUploadService, HEIF_SUPPORT_AVAILABLE

logger = logging.getLogger(__name__)


class TripImagesHomeView(LoginRequiredMixin, View):
    """
    Home view for image management of images used for trips.
    """

    def get(self, request, *args, **kwargs) -> HttpResponse:
        dashboard_page_context = DashboardPageContext(
            active_page=DashboardPage.IMAGES,
        )

        # Query uploaded images for the current user
        uploaded_images = TripImage.objects.for_user(request.user)

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
            logger.info(
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

            if result['status'] == 'success':
                success_count += 1
            else:
                error_count += 1

        # Log upload summary
        logger.info(
            f"Upload batch completed: User {request.user.email} (ID: {request.user.id}) - "
            f"{success_count} succeeded, {error_count} failed out of {len(uploaded_files)} files"
        )

        # Return 200 even if some files failed - client checks individual status
        return JsonResponse({'files': results})


class TripImageInspectView(LoginRequiredMixin, ModalView):
    """
    Modal view for inspecting/previewing a trip image with full metadata.

    Displays the web-sized image along with all available metadata including
    EXIF data, upload information, and GPS coordinates if available.

    Supports two access modes:
    1. With trip context (?trip_id=X): Check trip membership permission
    2. Without trip context: Only uploader has access
    """

    def get_template_name(self) -> str:
        return 'images/modals/trip_image_inspect.html'

    def get(self, request, image_uuid: str, *args, **kwargs) -> HttpResponse:
        # Fetch image by UUID
        trip_image = get_object_or_404(TripImage, uuid=image_uuid)

        # Determine trip context (optional)
        trip = None
        trip_id = request.GET.get('trip_id')
        if trip_id:
            try:
                from tt.apps.trips.models import Trip
                trip = Trip.objects.get(pk=int(trip_id))
            except (ValueError, Trip.DoesNotExist):
                pass  # Invalid trip_id, fall back to non-trip context

        # Permission check with optional trip context
        if not trip_image.user_can_access(request.user, trip=trip):
            logger.warning(
                f"Access denied: User {request.user.email} (ID: {request.user.id}) "
                f"attempted to access TripImage {image_uuid} "
                f"(trip_id: {trip_id if trip_id else 'none'}) "
                f"owned by {trip_image.uploaded_by.email if trip_image.uploaded_by else 'unknown'}"
            )
            return JsonResponse(
                {'error': 'You do not have permission to access this image.'},
                status=403,
            )

        # Determine if user can edit metadata (only uploader)
        can_edit_metadata = (trip_image.uploaded_by == request.user)

        context = {
            'image': trip_image,
            'can_edit_metadata': can_edit_metadata,
            'trip': trip,  # May be None
        }
        return self.modal_response(request, context=context)
