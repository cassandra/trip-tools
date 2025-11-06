import io
import logging
import re
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404
from django.template.loader import render_to_string
from django.utils import timezone as django_timezone
from django.views.generic import View
from PIL import Image, ImageOps, ExifTags

from tt.apps.dashboard.context import DashboardPageContext
from tt.apps.dashboard.enums import DashboardPage
from tt.async_view import ModalView

from .models import TripImage

# Register HEIC support (optional dependency)
HEIF_SUPPORT_AVAILABLE = False
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
    HEIF_SUPPORT_AVAILABLE = True
except ImportError:
    pass  # HEIC support will be unavailable - will show warning on upload page

logger = logging.getLogger(__name__)

# File validation constants - conditionally include HEIC based on library availability
# MPO (Multi-Picture Object) is a JPEG variant used by some phone cameras
ALLOWED_FORMATS = {'JPEG', 'MPO', 'PNG'}
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png'}
if HEIF_SUPPORT_AVAILABLE:
    ALLOWED_FORMATS.add('HEIF')  # PIL reports HEIC files with format='HEIF'
    ALLOWED_EXTENSIONS.add('.heic')
MAX_FILE_SIZE_MB = 20
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# Image sizing constants
WEB_IMAGE_MAX_DIMENSION = 1600
THUMBNAIL_MAX_DIMENSION = 350


def validate_image_file( uploaded_file: UploadedFile ) -> tuple[bool, Optional[str]]:
    """
    Validate uploaded image file for format and size.

    Performs both extension and content validation to ensure file is a valid image.

    Args:
        uploaded_file: Django UploadedFile object to validate

    Returns:
        Tuple of (is_valid, error_message). If valid, error_message is None.
    """
    # Check file extension
    filename_lower = uploaded_file.name.lower()
    file_extension = None
    for ext in ALLOWED_EXTENSIONS:
        if filename_lower.endswith(ext):
            file_extension = ext
            break

    if not file_extension:
        allowed_list = ', '.join(sorted(ALLOWED_EXTENSIONS))
        return False, f'Invalid file format. Allowed: {allowed_list}'

    # Check file size
    if uploaded_file.size > MAX_FILE_SIZE_BYTES:
        return False, f'File too large. Maximum size: {MAX_FILE_SIZE_MB}MB'

    # Validate actual image content (security check - not just extension)
    try:
        uploaded_file.seek(0)
        image = Image.open(uploaded_file)

        # Verify the image data is valid
        image.verify()

        # Check that image format matches allowed formats
        if image.format not in ALLOWED_FORMATS:
            allowed_list = ', '.join(sorted(ALLOWED_FORMATS))
            return False, f'Invalid image format. Allowed: {allowed_list}'

        # Verify format matches extension expectation
        # Note: MPO (Multi-Picture Object) is accepted for .jpg files as it's a JPEG variant
        expected_formats = {
            '.jpg': ['JPEG', 'MPO'],
            '.jpeg': ['JPEG', 'MPO'],
            '.png': ['PNG'],
            '.heic': ['HEIF'],  # PIL reports HEIC files with format='HEIF'
        }
        expected_format_list = expected_formats.get(file_extension)
        if expected_format_list and image.format not in expected_format_list:
            return False, f'File content does not match extension (detected: {image.format})'

    except Exception as e:
        logger.warning(f'Image validation failed for {uploaded_file.name}: {e}')
        return False, 'Invalid or corrupted image file'
    finally:
        # Reset file pointer for subsequent processing
        uploaded_file.seek(0)

    return True, None


def extract_exif_metadata( image: Image.Image ) -> dict:
    """
    Extract EXIF metadata from PIL Image.

    Returns:
        Dict with keys: datetime_utc, latitude, longitude, caption, tags, timezone_unknown
    """
    metadata = {
        'datetime_utc': None,
        'latitude': None,
        'longitude': None,
        'caption': None,
        'tags': [],
        'timezone_unknown': False,
    }

    try:
        exif_data = image._getexif()
        if not exif_data:
            return metadata

        # Create reverse mapping of EXIF tag names to IDs
        exif_tag_names = {v: k for k, v in ExifTags.TAGS.items()}

        # Extract datetime and timezone offset
        datetime_tag = exif_tag_names.get('DateTimeOriginal') or exif_tag_names.get('DateTime')
        offset_tag = exif_tag_names.get('OffsetTimeOriginal') or exif_tag_names.get('OffsetTime')

        if datetime_tag and datetime_tag in exif_data:
            datetime_str = exif_data[datetime_tag]
            offset_str = exif_data.get(offset_tag) if offset_tag else None

            try:
                # EXIF datetime format: "YYYY:MM:DD HH:MM:SS" (local time)
                dt = datetime.strptime(datetime_str, '%Y:%m:%d %H:%M:%S')

                if offset_str:
                    # Parse timezone offset format: "±HH:MM" (e.g., "+02:00", "-05:00")
                    # Create timezone-aware datetime in local timezone, then convert to UTC
                    match = re.match(r'([+-])(\d{2}):(\d{2})', offset_str)
                    if match:
                        sign, hours, minutes = match.groups()
                        offset_minutes = int(hours) * 60 + int(minutes)
                        if sign == '-':
                            offset_minutes = -offset_minutes

                        local_tz = timezone(timedelta(minutes=offset_minutes))
                        dt_aware = dt.replace(tzinfo=local_tz)
                        # Convert to UTC
                        metadata['datetime_utc'] = dt_aware.astimezone(timezone.utc)
                        metadata['timezone_unknown'] = False
                    else:
                        logger.warning(f'Could not parse timezone offset: {offset_str}')
                        # Fallback: assume UTC
                        metadata['datetime_utc'] = django_timezone.make_aware(dt, timezone=timezone.utc)
                        metadata['timezone_unknown'] = True
                else:
                    # No timezone offset in EXIF - assume UTC and mark as unknown
                    metadata['datetime_utc'] = django_timezone.make_aware(dt, timezone=timezone.utc)
                    metadata['timezone_unknown'] = True

            except (ValueError, AttributeError) as e:
                logger.warning(f'Could not parse EXIF datetime: {datetime_str}, error: {e}')

        # Extract GPS coordinates
        gps_tag = exif_tag_names.get('GPSInfo')
        if gps_tag and gps_tag in exif_data:
            gps_info = exif_data[gps_tag]
            if gps_info:
                lat, lon = _extract_gps_coordinates(gps_info)
                if lat is not None and lon is not None:
                    metadata['latitude'] = lat
                    metadata['longitude'] = lon

        # Extract caption from ImageDescription or UserComment
        caption_tag = exif_tag_names.get('ImageDescription') or exif_tag_names.get('UserComment')
        if caption_tag and caption_tag in exif_data:
            caption = exif_data[caption_tag]
            if caption and isinstance(caption, str):
                metadata['caption'] = caption.strip()

        # Extract tags from Keywords or XPKeywords
        keywords_tag = exif_tag_names.get('XPKeywords')
        if keywords_tag and keywords_tag in exif_data:
            keywords = exif_data[keywords_tag]
            if keywords:
                # XPKeywords is typically semicolon-separated
                if isinstance(keywords, bytes):
                    keywords = keywords.decode('utf-16le', errors='ignore')
                if isinstance(keywords, str):
                    tags = [tag.strip() for tag in keywords.split(';') if tag.strip()]
                    metadata['tags'] = tags

    except Exception as e:
        logger.warning(f'Error extracting EXIF metadata: {e}')

    return metadata


def _extract_gps_coordinates( gps_info: dict ) -> tuple[Optional[Decimal], Optional[Decimal]]:
    """
    Extract GPS coordinates from EXIF GPS info dict.

    Returns:
        Tuple of (latitude, longitude) as Decimal, or (None, None) if not available.
    """
    try:
        # GPS tags we need
        gps_latitude = gps_info.get(2)  # GPSLatitude
        gps_latitude_ref = gps_info.get(1)  # GPSLatitudeRef (N/S)
        gps_longitude = gps_info.get(4)  # GPSLongitude
        gps_longitude_ref = gps_info.get(3)  # GPSLongitudeRef (E/W)

        if not all([gps_latitude, gps_latitude_ref, gps_longitude, gps_longitude_ref]):
            return None, None

        # Convert coordinates from degrees/minutes/seconds to decimal
        lat = _convert_to_degrees(gps_latitude)
        if gps_latitude_ref == 'S':
            lat = -lat

        lon = _convert_to_degrees(gps_longitude)
        if gps_longitude_ref == 'W':
            lon = -lon

        return Decimal(str(round(lat, 6))), Decimal(str(round(lon, 6)))

    except Exception as e:
        logger.warning(f'Error extracting GPS coordinates: {e}')
        return None, None


def _convert_to_degrees( value ) -> float:
    """
    Convert GPS coordinates from degrees/minutes/seconds to decimal degrees.

    Args:
        value: Tuple of (degrees, minutes, seconds)
    """
    d = float(value[0])
    m = float(value[1])
    s = float(value[2])
    return d + (m / 60.0) + (s / 3600.0)


def resize_image( image: Image.Image, max_dimension: int ) -> Image.Image:
    """
    Resize image to fit within max_dimension while preserving aspect ratio.
    Only resizes if image exceeds max_dimension.

    Args:
        image: PIL Image to resize
        max_dimension: Maximum width or height in pixels

    Returns:
        Resized PIL Image (or original if no resize needed)
    """
    width, height = image.size

    # Only resize if image exceeds limit
    if width <= max_dimension and height <= max_dimension:
        return image

    # Calculate new dimensions preserving aspect ratio
    if width > height:
        new_width = max_dimension
        new_height = int((height / width) * max_dimension)
    else:
        new_height = max_dimension
        new_width = int((width / height) * max_dimension)

    # Use LANCZOS for high-quality downsampling
    resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
    return resized_image


def process_uploaded_image( uploaded_file: UploadedFile, user: 'User', request=None ) -> dict:
    """
    Process a single uploaded image file: validate, extract EXIF, resize, save.

    Args:
        uploaded_file: Django UploadedFile object
        user: User who uploaded the file
        request: Optional HttpRequest object for rendering templates with context processors

    Returns:
        Dict with keys: status ('success' or 'error'), uuid (if success),
        error_message (if error), metadata (if success)
    """
    result = {
        'filename': uploaded_file.name,
        'status': 'error',
        'error_message': None,
        'uuid': None,
        'metadata': None,
    }

    # Validate file
    is_valid, error_message = validate_image_file(uploaded_file)
    if not is_valid:
        result['error_message'] = error_message
        return result

    # Image objects to close for memory management
    original_image = None
    web_image = None
    thumbnail_image = None

    try:
        # Load image with Pillow
        uploaded_file.seek(0)
        original_image = Image.open(uploaded_file)

        # Extract EXIF metadata (before any modifications)
        metadata = extract_exif_metadata(original_image)

        # Determine if any EXIF metadata was successfully extracted
        has_exif = any([
            metadata['datetime_utc'] is not None,
            metadata['latitude'] is not None,
            metadata['longitude'] is not None,
            metadata['caption'] is not None,
            len(metadata['tags']) > 0,
        ])

        # Apply EXIF orientation correction (handles smartphone rotation flags)
        original_image = ImageOps.exif_transpose(original_image)

        # Convert HEIC to RGB if needed (Pillow may need pillow-heif plugin)
        if original_image.format == 'HEIF':  # PIL reports HEIC files with format='HEIF'
            original_image = original_image.convert('RGB')

        # Ensure we have RGB mode for consistent processing
        if original_image.mode not in ('RGB', 'RGBA'):
            original_image = original_image.convert('RGB')

        # Resize web version
        web_image = resize_image(original_image, WEB_IMAGE_MAX_DIMENSION)

        # Convert RGBA to RGB if needed (JPEG doesn't support alpha channel)
        if web_image.mode == 'RGBA':
            # Create white background
            rgb_image = Image.new('RGB', web_image.size, (255, 255, 255))
            rgb_image.paste(web_image, mask=web_image.split()[3])  # Use alpha channel as mask
            web_image = rgb_image
        elif web_image.mode not in ('RGB', 'L'):
            # Convert any other modes to RGB
            web_image = web_image.convert('RGB')

        web_bytes_io = io.BytesIO()
        web_image.save(web_bytes_io, format='JPEG', quality=90, optimize=True)
        web_bytes = web_bytes_io.getvalue()

        # Create thumbnail from web version (more memory efficient than original)
        thumbnail_image = resize_image(web_image, THUMBNAIL_MAX_DIMENSION)
        thumb_bytes_io = io.BytesIO()
        thumbnail_image.save(thumb_bytes_io, format='JPEG', quality=85, optimize=True)
        thumb_bytes = thumb_bytes_io.getvalue()

        # Wrap database operations in transaction for atomicity
        with transaction.atomic():
            # Create TripImage instance
            # Use filename as caption if no EXIF caption available
            caption = metadata['caption'] if metadata['caption'] else uploaded_file.name

            trip_image = TripImage.objects.create(
                uploaded_by = user,
                datetime_utc = metadata['datetime_utc'],
                latitude = metadata['latitude'],
                longitude = metadata['longitude'],
                caption = caption,
                tags = metadata['tags'],
                has_exif = has_exif,
                timezone_unknown = metadata['timezone_unknown'],
            )

            # Save web image file
            trip_image.web_image.save(
                uploaded_file.name,
                ContentFile(web_bytes),
                save = False,
            )

            # Save thumbnail image file
            trip_image.thumbnail_image.save(
                uploaded_file.name,
                ContentFile(thumb_bytes),
                save = False,
            )

            # Save the TripImage instance with both image fields
            trip_image.save()

        # Render grid item HTML for client-side insertion
        # Pass request to trigger context processors (needed for USER_TIMEZONE)
        html = render_to_string('images/partials/image_grid_item.html', {'trip_image': trip_image}, request=request)

        # Build success response
        result['status'] = 'success'
        result['uuid'] = str(trip_image.uuid)
        result['html'] = html
        result['metadata'] = {
            'datetime_utc': metadata['datetime_utc'].isoformat() if metadata['datetime_utc'] else None,
            'latitude': float(metadata['latitude']) if metadata['latitude'] else None,
            'longitude': float(metadata['longitude']) if metadata['longitude'] else None,
            'caption': metadata['caption'],
            'tags': metadata['tags'],
        }

        logger.info(f'Successfully processed image upload: {uploaded_file.name} -> {trip_image.uuid}')

    except Exception as e:
        # Log detailed error for debugging, but return generic message to user
        logger.exception(f'Error processing image {uploaded_file.name}: {e}')
        result['error_message'] = 'Failed to process image. Please try again or contact support.'

    finally:
        # Clean up image objects to free memory
        if original_image:
            original_image.close()
        if web_image and web_image is not original_image:
            web_image.close()
        if thumbnail_image and thumbnail_image is not web_image:
            thumbnail_image.close()

    return result


class TripImagesHomeView(LoginRequiredMixin, View):
    """
    Home view for image management of images used for trips.
    """

    def get(self, request, *args, **kwargs) -> HttpResponse:
        dashboard_page_context = DashboardPageContext(
            active_page = DashboardPage.IMAGES,
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
            return JsonResponse(
                {'error': 'No files provided'},
                status = 400,
            )

        results = []
        for uploaded_file in uploaded_files:
            result = process_uploaded_image(uploaded_file, request.user, request=request)
            results.append(result)

        # Return 200 even if some files failed - client checks individual status
        return JsonResponse({'files': results})


class TripImageInspectView(LoginRequiredMixin, ModalView):
    """
    Modal view for inspecting/previewing a trip image with full metadata.

    Displays the web-sized image along with all available metadata including
    EXIF data, upload information, and GPS coordinates if available.
    """

    def get_template_name(self) -> str:
        return 'images/modals/trip_image_inspect.html'

    def get(self, request, image_uuid: str, *args, **kwargs) -> HttpResponse:
        # Fetch image by UUID
        trip_image = get_object_or_404(TripImage, uuid=image_uuid)

        # TODO: Add permission check - ensure user has access to this image
        # For now, any logged-in user can view any image

        context = {
            'image': trip_image,
        }
        return self.modal_response(request, context=context)

