import io
import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple, Dict, Any

from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.http import HttpRequest
from django.template.loader import render_to_string
from django.utils import timezone as django_timezone
from PIL import Image, ImageOps, ExifTags

from tt.apps.common import datetimeproxy
from tt.apps.common.singleton import Singleton

from .domain import (
    GpsCoordinate,
    ExifMetadata,
    ImageDimensions,
    ImageUploadResult,
    ValidationResult,
    ImageProcessingConfig,
)
from .models import TripImage

logger = logging.getLogger(__name__)

# Check for HEIF support and update configuration
HEIF_SUPPORT_AVAILABLE = False
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
    HEIF_SUPPORT_AVAILABLE = True
    # Add HEIF support to configuration
    ImageProcessingConfig.ALLOWED_FORMATS.add('HEIF')
    ImageProcessingConfig.ALLOWED_EXTENSIONS.add('.heic')
except ImportError:
    pass  # HEIC support will be unavailable


class ImageUploadService(Singleton):
    """
    Service for handling trip image upload, processing, and metadata extraction.

    Responsibilities:
    - Image file validation (format, size, content)
    - EXIF metadata extraction (datetime, GPS, tags)
    - Image processing (resize, format conversion, orientation correction)
    - TripImage database record creation
    - Grid item HTML rendering for AJAX responses
    """

    def __init_singleton__(self):
        """Initialize service singleton."""
        logger.debug("ImageUploadService initialized")
        return

    def validate_image_file(self, uploaded_file: UploadedFile) -> ValidationResult:
        """
        Validate uploaded image file for format and size.

        Performs both extension and content validation to ensure file is a valid image.

        Args:
            uploaded_file: Django UploadedFile object to validate

        Returns:
            ValidationResult with is_valid and optional error_message
        """
        # Check file extension
        filename_lower = uploaded_file.name.lower()
        file_extension = None
        for ext in ImageProcessingConfig.ALLOWED_EXTENSIONS:
            if filename_lower.endswith(ext):
                file_extension = ext
                break

        if not file_extension:
            allowed_list = ', '.join(sorted(ImageProcessingConfig.ALLOWED_EXTENSIONS))
            return ValidationResult.failure(
                f'Invalid file format for "{uploaded_file.name}". '
                f'Allowed extensions: {allowed_list}'
            )

        # Check file size
        if uploaded_file.size > ImageProcessingConfig.MAX_FILE_SIZE_BYTES:
            file_size_mb = uploaded_file.size / (1024 * 1024)
            return ValidationResult.failure(
                f'File "{uploaded_file.name}" is too large ({file_size_mb:.1f}MB). '
                f'Maximum size: {ImageProcessingConfig.MAX_FILE_SIZE_MB}MB'
            )

        # Validate actual image content (security check - not just extension)
        try:
            uploaded_file.seek(0)
            image = Image.open(uploaded_file)

            # Verify the image data is valid
            image.verify()

            # Check that image format matches allowed formats
            if image.format not in ImageProcessingConfig.ALLOWED_FORMATS:
                allowed_list = ', '.join(sorted(ImageProcessingConfig.ALLOWED_FORMATS))
                return ValidationResult.failure(
                    f'Invalid image format "{image.format}" in file "{uploaded_file.name}". '
                    f'Allowed formats: {allowed_list}'
                )

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
                return ValidationResult.failure(
                    f'File "{uploaded_file.name}": extension {file_extension} does not match '
                    f'actual image format {image.format}. This may indicate file corruption or '
                    f'incorrect file extension.'
                )

            # Reset file pointer for subsequent operations
            uploaded_file.seek(0)
            return ValidationResult.success()

        except Exception as e:
            logger.warning(f"Image validation failed for {uploaded_file.name}: {e}")
            return ValidationResult.failure(
                f'File "{uploaded_file.name}" appears to be invalid or corrupted. '
                f'Please ensure it is a valid image file.'
            )

    def extract_exif_metadata(self, image: Image.Image) -> ExifMetadata:
        """
        Extract EXIF metadata from PIL Image.

        Extracts:
        - datetime_utc: Photo capture datetime in UTC (with timezone offset parsing)
        - gps: GPS coordinates as GpsCoordinate value object
        - caption: Image description from EXIF
        - tags: Keyword tags from EXIF (as immutable tuple)
        - timezone: IANA timezone name if detected from EXIF offset
        - has_exif: Whether any EXIF data was successfully extracted

        Args:
            image: PIL Image object (must be called BEFORE exif_transpose)

        Returns:
            ExifMetadata value object
        """
        datetime_utc = None
        gps = None
        caption = None
        tags = []
        detected_timezone = None

        try:
            exif_data = image._getexif()
            if not exif_data:
                return ExifMetadata.empty()

            # Create reverse mapping of EXIF tag codes to names
            exif_tag_names = {ExifTags.TAGS[k]: v for k, v in exif_data.items() if k in ExifTags.TAGS}

            # Extract datetime with timezone offset parsing
            datetime_str = exif_tag_names.get('DateTimeOriginal') or exif_tag_names.get('DateTime')
            offset_str = exif_tag_names.get('OffsetTimeOriginal') or exif_tag_names.get('OffsetTime')

            if datetime_str:
                # datetime_str is already the value from exif_tag_names, not a tag key

                try:
                    dt = datetime.strptime(datetime_str, '%Y:%m:%d %H:%M:%S')

                    if offset_str:
                        # Parse timezone offset format: "±HH:MM"
                        match = re.match(r'([+-])(\d{2}):(\d{2})', offset_str)
                        if match:
                            sign, hours, minutes = match.groups()
                            offset_minutes = int(hours) * 60 + int(minutes)
                            if sign == '-':
                                offset_minutes = -offset_minutes

                            # Convert local time to UTC
                            local_tz = timezone(timedelta(minutes=offset_minutes))
                            dt_aware = dt.replace(tzinfo=local_tz)
                            datetime_utc = dt_aware.astimezone(timezone.utc)

                            # Convert offset to IANA timezone name using the actual datetime
                            # (important for DST consideration)
                            detected_timezone = datetimeproxy.offset_to_timezone(offset_minutes, datetime_utc)
                        else:
                            # Fallback: assume UTC and no timezone
                            datetime_utc = django_timezone.make_aware(dt, timezone=timezone.utc)
                            detected_timezone = None
                    else:
                        # No timezone offset - assume UTC and no timezone
                        datetime_utc = django_timezone.make_aware(dt, timezone=timezone.utc)
                        detected_timezone = None

                except (ValueError, AttributeError) as e:
                    logger.warning(f"Failed to parse EXIF datetime: {e}")

            # Extract GPS coordinates using GpsCoordinate value object
            gps_info = exif_tag_names.get('GPSInfo')
            if gps_info:
                try:
                    # GPS tags use numeric keys
                    gps_latitude = gps_info.get(2)  # GPSLatitude
                    gps_latitude_ref = gps_info.get(1)  # GPSLatitudeRef (N/S)
                    gps_longitude = gps_info.get(4)  # GPSLongitude
                    gps_longitude_ref = gps_info.get(3)  # GPSLongitudeRef (E/W)

                    if gps_latitude and gps_longitude and gps_latitude_ref and gps_longitude_ref:
                        gps = GpsCoordinate.from_exif_gps_tuple(
                            gps_latitude, gps_latitude_ref,
                            gps_longitude, gps_longitude_ref,
                        )

                except (KeyError, ValueError, AttributeError) as e:
                    logger.warning(f"Failed to parse GPS coordinates: {e}")

            # Extract caption/description
            image_description = exif_tag_names.get('ImageDescription')
            if image_description:
                caption = str(image_description).strip()

            # Extract keywords/tags
            # XPKeywords is a Windows-specific tag that stores keywords
            xp_keywords = exif_tag_names.get('XPKeywords')
            if xp_keywords:
                try:
                    # XPKeywords is UTF-16 encoded
                    if isinstance(xp_keywords, bytes):
                        keywords_str = xp_keywords.decode('utf-16le', errors='ignore').rstrip('\x00')
                    else:
                        keywords_str = str(xp_keywords)

                    # Split on semicolons and clean
                    tags = [tag.strip() for tag in keywords_str.split(';') if tag.strip()]
                except (UnicodeDecodeError, AttributeError) as e:
                    logger.warning(f"Failed to parse EXIF keywords: {e}")

        except (AttributeError, KeyError) as e:
            logger.info(f"No EXIF data available: {e}")

        # Return immutable ExifMetadata value object
        return ExifMetadata(
            datetime_utc=datetime_utc,
            gps=gps,
            caption=caption,
            tags=tuple(tags),  # Convert to immutable tuple
            timezone=detected_timezone,
        )

    def resize_image(self, image: Image.Image, max_dimension: int) -> Image.Image:
        """
        Resize image to fit within max_dimension while preserving aspect ratio.
        Only resizes if image exceeds max_dimension.

        Uses ImageDimensions value object for aspect ratio calculations.

        Args:
            image: PIL Image to resize
            max_dimension: Maximum width or height in pixels

        Returns:
            Resized PIL Image (or original if no resize needed)
        """
        current_dims = ImageDimensions(width=image.size[0], height=image.size[1])

        # Check if resize is needed
        if not current_dims.needs_resize(max_dimension):
            return image

        # Calculate new dimensions preserving aspect ratio
        new_dims = current_dims.calculate_resized_dimensions(max_dimension)

        # Use LANCZOS for high-quality downsampling
        resized_image = image.resize(new_dims.to_tuple(), Image.Resampling.LANCZOS)
        return resized_image

    def process_and_resize_images(self, original_image: Image.Image) -> Tuple[bytes, bytes]:
        """
        Process original image: resize web version, create thumbnail, convert to JPEG.

        Uses ImageProcessingConfig for sizing and quality settings.

        Args:
            original_image: PIL Image after EXIF orientation correction

        Returns:
            Tuple of (web_image_bytes, thumbnail_image_bytes)
        """
        # Resize web version
        web_image = self.resize_image(original_image, ImageProcessingConfig.WEB_IMAGE_MAX_DIMENSION)

        # Convert RGBA to RGB if needed (JPEG doesn't support alpha channel)
        if web_image.mode == 'RGBA':
            # Create white background
            rgb_image = Image.new('RGB', web_image.size, (255, 255, 255))
            rgb_image.paste(web_image, mask=web_image.split()[3])  # Use alpha channel as mask
            web_image = rgb_image
        elif web_image.mode not in ('RGB', 'L'):
            # Convert any other modes to RGB
            web_image = web_image.convert('RGB')

        # Save web image to bytes
        web_bytes_io = io.BytesIO()
        web_image.save(web_bytes_io, format='JPEG', quality=ImageProcessingConfig.WEB_IMAGE_QUALITY, optimize=True)
        web_bytes = web_bytes_io.getvalue()

        # Create thumbnail from web version (more memory efficient than original)
        thumbnail_image = self.resize_image(web_image, ImageProcessingConfig.THUMBNAIL_MAX_DIMENSION)
        thumb_bytes_io = io.BytesIO()
        thumbnail_image.save(thumb_bytes_io, format='JPEG', quality=ImageProcessingConfig.THUMBNAIL_QUALITY, optimize=True)
        thumb_bytes = thumb_bytes_io.getvalue()

        # Clean up intermediate images
        if web_image is not original_image:
            web_image.close()
        if thumbnail_image is not web_image:
            thumbnail_image.close()

        return web_bytes, thumb_bytes

    def create_trip_image(
        self,
        user: Any,
        uploaded_file: UploadedFile,
        metadata: ExifMetadata,
        web_bytes: bytes,
        thumb_bytes: bytes,
    ) -> TripImage:
        """
        Create TripImage database record with processed image files.

        Args:
            user: User who uploaded the image
            uploaded_file: Original uploaded file (for filename)
            metadata: Extracted EXIF metadata as ExifMetadata value object
            web_bytes: Processed web-sized image bytes
            thumb_bytes: Processed thumbnail image bytes

        Returns:
            Created TripImage instance
        """
        # Use filename as caption if no EXIF caption available
        caption = metadata.caption if metadata.caption else uploaded_file.name

        with transaction.atomic():
            # Create TripImage instance using dataclass fields directly
            trip_image = TripImage.objects.create(
                uploaded_by=user,
                datetime_utc=metadata.datetime_utc,
                latitude=metadata.gps.latitude if metadata.gps else None,
                longitude=metadata.gps.longitude if metadata.gps else None,
                caption=caption,
                tags=list(metadata.tags),
                has_exif=metadata.has_exif,
                timezone=metadata.timezone,
            )

            # Save web image file
            trip_image.web_image.save(
                uploaded_file.name,
                ContentFile(web_bytes),
                save=False,
            )

            # Save thumbnail image file
            trip_image.thumbnail_image.save(
                uploaded_file.name,
                ContentFile(thumb_bytes),
                save=False,
            )

            # Save the TripImage instance with both image fields
            trip_image.save()

        logger.info(f'Created TripImage {trip_image.uuid} from {uploaded_file.name}')
        return trip_image

    def render_grid_item_html(self, trip_image: TripImage, request: Optional[HttpRequest] = None) -> str:
        """
        Render HTML partial for image grid item (used in AJAX responses).

        Args:
            trip_image: TripImage instance to render
            request: HttpRequest for context processors (needed for USER_TIMEZONE)

        Returns:
            Rendered HTML string
        """
        return render_to_string(
            'images/partials/image_grid_item.html',
            {'trip_image': trip_image},
            request=request,
        )

    def process_uploaded_image(self, uploaded_file: UploadedFile, user: Any, request: Optional[HttpRequest] = None) -> ImageUploadResult:
        """
        Main orchestration method: validate, extract EXIF, process, and save uploaded image.

        Args:
            uploaded_file: Django UploadedFile object
            user: User who uploaded the file
            request: Optional HttpRequest object for rendering templates with context processors

        Returns:
            ImageUploadResult with success or error status
        """
        # Step 1: Validate file
        validation = self.validate_image_file(uploaded_file)
        if not validation.is_valid:
            return ImageUploadResult.failure(
                filename=uploaded_file.name,
                error_message=validation.error_message,
            )

        # Image objects to close for memory management
        original_image = None

        try:
            # Step 2: Load image with Pillow
            uploaded_file.seek(0)
            original_image = Image.open(uploaded_file)

            # Step 3: Extract EXIF metadata (BEFORE any modifications)
            metadata = self.extract_exif_metadata(original_image)

            # Step 4: Apply EXIF orientation correction
            transposed = ImageOps.exif_transpose(original_image)
            if transposed is not None:
                original_image = transposed

            # Step 5: Convert HEIF to RGB if needed
            if original_image.format == 'HEIF':
                original_image = original_image.convert('RGB')

            # Step 6: Ensure RGB mode for consistent processing
            if original_image.mode not in ('RGB', 'RGBA'):
                original_image = original_image.convert('RGB')

            # Step 7: Process and resize images
            web_bytes, thumb_bytes = self.process_and_resize_images(original_image)

            # Step 8: Create database record
            trip_image = self.create_trip_image(user, uploaded_file, metadata, web_bytes, thumb_bytes)

            # Step 9: Render grid item HTML (only if request provided)
            html = None
            if request is not None:
                html = self.render_grid_item_html(trip_image, request)

            # Step 10: Build success response
            logger.info(f'Successfully processed image upload: {uploaded_file.name} -> {trip_image.uuid}')

            return ImageUploadResult.success(
                filename=uploaded_file.name,
                uuid=str(trip_image.uuid),
                metadata=metadata,
                html=html,
            )

        except Exception as e:
            # Log detailed error for debugging
            logger.exception(
                f'Unexpected error processing image {uploaded_file.name} for user {user.email}: {e}'
            )
            return ImageUploadResult.failure(
                filename=uploaded_file.name,
                error_message=(
                    f'Failed to process "{uploaded_file.name}". '
                    f'Please verify the file is not corrupted and try again. '
                    f'If the problem persists, contact support.'
                ),
            )

        finally:
            # Clean up image objects to free memory
            if original_image:
                original_image.close()
