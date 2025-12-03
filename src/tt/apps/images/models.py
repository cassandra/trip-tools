import uuid

from django.conf import settings
from django.db import models

from . import managers


def trip_image_upload_path_helper( instance, filename, suffix = '' ):
    """
    Generate upload path for web-sized trip images: /trip/image/{YYYY-MM-DD}/{uuid}{suffix}.jpg
    If no datetime_utc, use: /trip/image/{uuid[:4]}/{uuid}{suffix}.jpg

    Note: This function is called when save() is invoked on the ImageField.
    """
    ext = filename.split('.')[-1] if '.' in filename else 'jpg'
    uuid_str = str(instance.uuid)

    if instance.datetime_utc:
        date_str = instance.datetime_utc.strftime('%Y-%m-%d')
        return f'trip/image/{date_str}/{uuid_str}{suffix}.{ext}'
    else:
        # Use first 4 characters of UUID as directory
        return f'trip/image/{uuid_str[:4]}/{uuid_str}{suffix}.{ext}'

    
def trip_web_image_upload_path( instance, filename ):
    return trip_image_upload_path_helper( instance, filename )


def trip_thumbnail_image_upload_path( instance, filename ):
    return trip_image_upload_path_helper( instance, filename, suffix = '_thumb' )


class TripImage(models.Model):
    """
    Storage for trip-related images with metadata.

    Images are NOT directly uploaded to these fields. Instead:
    1. Original image is uploaded and processed (EXIF extraction, resizing)
    2. Processed images are saved to web_image and thumbnail_image using ContentFile
    3. Original image is discarded

    Example usage in image processing code:
        from django.core.files.base import ContentFile

        trip_image = TripImage.objects.create(
            uploaded_by=user,
            datetime_utc=extracted_datetime,
            latitude=exif_lat,
            longitude=exif_lon,
            caption=exif_caption,
            tags=['vacation', 'beach', 'sunset'],  # List of tag strings
        )
        trip_image.web_image.save('image.jpg', ContentFile(web_bytes), save=False)
        trip_image.thumbnail_image.save('image.jpg', ContentFile(thumb_bytes), save=False)
        trip_image.save()
    """
    objects = managers.TripImageManager()

    # UUID for public URL access (non-guessable)
    uuid = models.UUIDField(
        default = uuid.uuid4,
        unique = True,
        editable = False,
    )

    # Processed image files (populated programmatically, not via direct upload)
    web_image = models.ImageField(
        upload_to = trip_web_image_upload_path,
        max_length = 255,
        help_text = 'Web-sized image (max 1600px), saved via ContentFile',
    )
    thumbnail_image = models.ImageField(
        upload_to = trip_thumbnail_image_upload_path,
        max_length = 255,
        blank = True,
        help_text = 'Thumbnail image (max 350px), saved via ContentFile',
    )
    # Metadata (extracted from image EXIF, user-editable)
    datetime_utc = models.DateTimeField(
        null = True,
        blank = True,
        db_index = True,  # Performance for date range queries
    )
    latitude = models.DecimalField(
        max_digits = 9,
        decimal_places = 6,
        null = True,
        blank = True,
    )
    longitude = models.DecimalField(
        max_digits = 9,
        decimal_places = 6,
        null = True,
        blank = True,
    )
    caption = models.TextField(blank = True)
    tags = models.JSONField(
        default = list,
        blank = True,
        help_text = 'List of tags extracted from EXIF or user-added',
    )
    has_exif = models.BooleanField(
        default = False,
        help_text = 'Whether EXIF metadata was successfully extracted from the uploaded image',
    )
    timezone = models.CharField(
        max_length = 63,
        null = True,
        blank = True,
        help_text = "IANA timezone name if detected from EXIF data (e.g., 'America/New_York')",
    )

    @property
    def timezone_unknown(self) -> bool:
        """Whether datetime_utc timezone is uncertain (no timezone information available)."""
        return self.timezone is None

    # Upload tracking
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete = models.SET_NULL,
        null = True,
        related_name = 'uploaded_images',
    )
    uploaded_datetime = models.DateTimeField(auto_now_add=True, db_index=True)
    upload_session_uuid = models.UUIDField(
        null=True,
        blank=True,
        help_text='Groups images from the same bulk upload batch for chronological ordering',
    )

    # Edit tracking
    modified_datetime = models.DateTimeField(
        auto_now = True,
        help_text = 'Last modification timestamp (auto-updated)',
    )
    modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete = models.SET_NULL,
        null = True,
        blank = True,
        related_name = 'modified_images',
        help_text = 'User who last modified this image metadata',
    )

    def __str__(self):
        if self.datetime_utc:
            return f"TripImage {self.uuid} ({self.datetime_utc.strftime('%Y-%m-%d')})"
        return f"TripImage {self.uuid}"
