"""
Reusable validators for image processing.

Following Django patterns for validator classes that can be used
in forms, models, or service layer validation.
"""
from typing import List

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile

from .domain import ImageProcessingConfig


class ImageFileValidator:
    """
    Validator for uploaded image files.

    Checks file extension, size, and format validity.
    Can be used in forms or directly in service layer.

    Example usage:
        validator = ImageFileValidator()
        try:
            validator(uploaded_file)
        except ValidationError as e:
            # Handle validation error
    """

    def __init__(
        self,
        allowed_extensions: List[str] = None,
        max_size_bytes: int = None,
    ):
        """
        Initialize validator with optional custom limits.

        Args:
            allowed_extensions: List of allowed file extensions (with dots)
            max_size_bytes: Maximum file size in bytes
        """
        self.allowed_extensions = allowed_extensions or list(ImageProcessingConfig.ALLOWED_EXTENSIONS)
        self.max_size_bytes = max_size_bytes or ImageProcessingConfig.MAX_FILE_SIZE_BYTES

    def __call__(self, uploaded_file: UploadedFile):
        """
        Validate the uploaded file.

        Args:
            uploaded_file: Django UploadedFile to validate

        Raises:
            ValidationError: If file fails validation
        """
        self.validate_extension(uploaded_file)
        self.validate_size(uploaded_file)

    def validate_extension(self, uploaded_file: UploadedFile):
        """
        Validate file extension.

        Args:
            uploaded_file: Django UploadedFile to validate

        Raises:
            ValidationError: If extension is not allowed
        """
        filename_lower = uploaded_file.name.lower()
        has_valid_extension = any(
            filename_lower.endswith(ext) for ext in self.allowed_extensions
        )

        if not has_valid_extension:
            allowed_list = ', '.join(sorted(self.allowed_extensions))
            raise ValidationError(
                f'Invalid file format. Allowed extensions: {allowed_list}',
                code='invalid_extension',
            )

    def validate_size(self, uploaded_file: UploadedFile):
        """
        Validate file size.

        Args:
            uploaded_file: Django UploadedFile to validate

        Raises:
            ValidationError: If file is too large
        """
        if uploaded_file.size > self.max_size_bytes:
            max_mb = self.max_size_bytes // (1024 * 1024)
            raise ValidationError(
                f'File too large. Maximum size: {max_mb}MB',
                code='file_too_large',
            )


class ImagePermissionValidator:
    """
    Validator for image access permissions.

    Checks if user has permission to access a specific image,
    with optional trip context support.
    """

    def __init__(self, trip=None):
        """
        Initialize validator with optional trip context.

        Args:
            trip: Optional Trip instance for trip-context permission check
        """
        self.trip = trip

    def __call__(self, trip_image, user):
        """
        Validate user has permission to access image.

        Args:
            trip_image: TripImage instance
            user: User to check permission for

        Raises:
            ValidationError: If user does not have permission
        """
        if not trip_image.user_can_access(user, trip=self.trip):
            raise ValidationError(
                'You do not have permission to access this image.',
                code='permission_denied',
            )
