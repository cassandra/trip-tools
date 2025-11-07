"""
Synthetic data factory for creating test images with configurable EXIF metadata.
"""
import io
from datetime import datetime
from decimal import Decimal
from typing import Optional

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image, ExifTags


def create_test_image_bytes(
    width: int = 800,
    height: int = 600,
    format: str = 'JPEG',
    color: tuple = (255, 0, 0),  # Red by default
) -> bytes:
    """
    Create synthetic image bytes.

    Args:
        width: Image width in pixels
        height: Image height in pixels
        format: Image format ('JPEG', 'PNG', etc.)
        color: RGB color tuple

    Returns:
        Image bytes
    """
    image = Image.new('RGB', (width, height), color)
    bytes_io = io.BytesIO()

    if format == 'JPEG':
        image.save(bytes_io, format='JPEG', quality=90)
    elif format == 'PNG':
        image.save(bytes_io, format='PNG')
    else:
        image.save(bytes_io, format=format)

    image.close()
    return bytes_io.getvalue()


def create_test_image_with_exif(
    width: int = 800,
    height: int = 600,
    datetime_utc: Optional[datetime] = None,
    datetime_offset: Optional[str] = None,
    latitude: Optional[Decimal] = None,
    longitude: Optional[Decimal] = None,
    description: Optional[str] = None,
    keywords: Optional[list] = None,
) -> bytes:
    """
    Create synthetic image with EXIF metadata.

    Args:
        width: Image width in pixels
        height: Image height in pixels
        datetime_utc: Photo datetime (will be converted to EXIF format)
        datetime_offset: Timezone offset in ±HH:MM format (e.g., '+02:00')
        latitude: GPS latitude in decimal degrees
        longitude: GPS longitude in decimal degrees
        description: Image description/caption
        keywords: List of keyword strings

    Returns:
        Image bytes with EXIF data
    """
    image = Image.new('RGB', (width, height), (0, 128, 255))

    # Build EXIF data dictionary
    exif_dict = {}

    # Add datetime if provided
    if datetime_utc:
        # EXIF datetime format: 'YYYY:MM:DD HH:MM:SS'
        datetime_str = datetime_utc.strftime('%Y:%m:%d %H:%M:%S')
        exif_dict[ExifTags.Base.DateTime.value] = datetime_str
        exif_dict[ExifTags.Base.DateTimeOriginal.value] = datetime_str

        # Add timezone offset if provided
        if datetime_offset:
            # Note: OffsetTimeOriginal requires PIL 9.1+ and may not work in all versions
            # We'll try to add it, but it's not critical for testing
            try:
                offset_tag = 36881  # OffsetTimeOriginal tag code
                exif_dict[offset_tag] = datetime_offset
            except Exception:
                pass

    # Add GPS coordinates if provided
    if latitude is not None and longitude is not None:
        gps_ifd = {}

        # Convert decimal to DMS (degrees, minutes, seconds) format
        lat_deg, lat_min, lat_sec, lat_ref = _decimal_to_dms(float(latitude), is_latitude=True)
        lon_deg, lon_min, lon_sec, lon_ref = _decimal_to_dms(float(longitude), is_latitude=False)

        # GPS tag codes
        gps_ifd[1] = lat_ref  # GPSLatitudeRef
        gps_ifd[2] = ((lat_deg, 1), (lat_min, 1), (int(lat_sec * 100), 100))  # GPSLatitude
        gps_ifd[3] = lon_ref  # GPSLongitudeRef
        gps_ifd[4] = ((lon_deg, 1), (lon_min, 1), (int(lon_sec * 100), 100))  # GPSLongitude

        exif_dict[ExifTags.Base.GPSInfo.value] = gps_ifd

    # Add description if provided
    if description:
        exif_dict[ExifTags.Base.ImageDescription.value] = description

    # Add keywords if provided
    if keywords:
        # XPKeywords should be UTF-16 encoded with null terminator
        keywords_str = ';'.join(keywords)
        keywords_bytes = keywords_str.encode('utf-16le') + b'\x00\x00'
        xp_keywords_tag = 0x9c9e  # XPKeywords tag code
        exif_dict[xp_keywords_tag] = keywords_bytes

    # Save image with EXIF data
    bytes_io = io.BytesIO()

    # Note: PIL's EXIF handling is limited - some tags may not persist
    # For testing, we'll do our best but accept limitations
    if exif_dict:
        try:
            exif = Image.Exif()
            for tag, value in exif_dict.items():
                exif[tag] = value
            image.save(bytes_io, format='JPEG', quality=90, exif=exif)
        except Exception:
            # If EXIF creation fails, just save without it
            image.save(bytes_io, format='JPEG', quality=90)
    else:
        image.save(bytes_io, format='JPEG', quality=90)

    image.close()
    return bytes_io.getvalue()


def _decimal_to_dms(decimal: float, is_latitude: bool) -> tuple:
    """
    Convert decimal degrees to DMS (degrees, minutes, seconds) format.

    Args:
        decimal: Decimal degrees
        is_latitude: True for latitude (N/S), False for longitude (E/W)

    Returns:
        Tuple of (degrees, minutes, seconds, reference)
    """
    # Determine reference (N/S/E/W)
    if is_latitude:
        ref = 'N' if decimal >= 0 else 'S'
    else:
        ref = 'E' if decimal >= 0 else 'W'

    # Work with absolute value
    decimal = abs(decimal)

    degrees = int(decimal)
    minutes_decimal = (decimal - degrees) * 60
    minutes = int(minutes_decimal)
    seconds = (minutes_decimal - minutes) * 60

    return degrees, minutes, seconds, ref


def create_uploaded_file(
    filename: str = 'test_image.jpg',
    content: Optional[bytes] = None,
    content_type: str = 'image/jpeg',
    **kwargs
) -> SimpleUploadedFile:
    """
    Create Django SimpleUploadedFile for testing uploads.

    Args:
        filename: Filename for the uploaded file
        content: File content bytes (if None, creates simple test image)
        content_type: MIME type
        **kwargs: Additional arguments passed to create_test_image_bytes if content is None

    Returns:
        SimpleUploadedFile instance
    """
    if content is None:
        content = create_test_image_bytes(**kwargs)

    return SimpleUploadedFile(
        name=filename,
        content=content,
        content_type=content_type,
    )
