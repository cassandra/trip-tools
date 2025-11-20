"""
Domain models and value objects for trip image processing.

Following Domain-Driven Design principles:
- Value objects are immutable (frozen dataclasses)
- Business rules encapsulated in domain entities
- No external dependencies (pure Python + standard library)
"""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional, Tuple


# Configuration constants - centralized business rules
class ImageProcessingConfig:
    """Central configuration for image processing parameters."""

    # File validation
    MAX_FILE_SIZE_MB = 20
    MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

    # Image sizing
    WEB_IMAGE_MAX_DIMENSION = 1600
    THUMBNAIL_MAX_DIMENSION = 350

    # JPEG quality settings
    WEB_IMAGE_QUALITY = 90
    THUMBNAIL_QUALITY = 85

    # Supported formats (base set, HEIF added conditionally)
    ALLOWED_FORMATS = {'JPEG', 'MPO', 'PNG'}
    ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png'}


@dataclass(frozen=True)
class GpsCoordinate:
    """
    Immutable GPS coordinate value object.

    Represents a geographic location with latitude and longitude.
    Encapsulates validation and conversion from DMS (degrees/minutes/seconds) format.
    """
    latitude: Decimal
    longitude: Decimal

    def __post_init__(self):
        """Validate GPS coordinates are within valid ranges."""
        if not (-90 <= float(self.latitude) <= 90):
            raise ValueError(f"Latitude must be between -90 and 90, got {self.latitude}")
        if not (-180 <= float(self.longitude) <= 180):
            raise ValueError(f"Longitude must be between -180 and 180, got {self.longitude}")

    @classmethod
    def from_dms(
        cls,
        lat_degrees: float,
        lat_minutes: float,
        lat_seconds: float,
        lat_ref: str,
        lon_degrees: float,
        lon_minutes: float,
        lon_seconds: float,
        lon_ref: str,
    ) -> 'GpsCoordinate':
        """
        Create GPS coordinate from DMS (degrees, minutes, seconds) format.

        Args:
            lat_degrees: Latitude degrees
            lat_minutes: Latitude minutes
            lat_seconds: Latitude seconds
            lat_ref: Latitude reference ('N' or 'S')
            lon_degrees: Longitude degrees
            lon_minutes: Longitude minutes
            lon_seconds: Longitude seconds
            lon_ref: Longitude reference ('E' or 'W')

        Returns:
            GpsCoordinate instance
        """
        # Convert DMS to decimal
        lat_decimal = lat_degrees + (lat_minutes / 60.0) + (lat_seconds / 3600.0)
        lon_decimal = lon_degrees + (lon_minutes / 60.0) + (lon_seconds / 3600.0)

        # Apply hemisphere reference
        if lat_ref == 'S':
            lat_decimal = -lat_decimal
        if lon_ref == 'W':
            lon_decimal = -lon_decimal

        return cls(
            latitude=Decimal(str(round(lat_decimal, 6))),
            longitude=Decimal(str(round(lon_decimal, 6))),
        )

    @classmethod
    def from_exif_gps_tuple(
        cls,
        gps_latitude: tuple,
        gps_latitude_ref: str,
        gps_longitude: tuple,
        gps_longitude_ref: str,
    ) -> 'GpsCoordinate':
        """
        Create GPS coordinate from EXIF GPS tuple format.

        EXIF GPS data can be in multiple formats:
        - Tuples of rationals: ((degrees_num, degrees_den), ...)
        - IFDRational objects with numerator/denominator properties

        Args:
            gps_latitude: Tuple of (degrees, minutes, seconds) as rationals or IFDRational
            gps_latitude_ref: 'N' or 'S'
            gps_longitude: Tuple of (degrees, minutes, seconds) as rationals or IFDRational
            gps_longitude_ref: 'E' or 'W'

        Returns:
            GpsCoordinate instance
        """
        def _convert_to_float(component):
            """Convert EXIF GPS component to float (handles tuple or IFDRational)."""
            # Check if it's an IFDRational object (has numerator/denominator)
            if hasattr(component, 'numerator') and hasattr(component, 'denominator'):
                return float(component.numerator) / float(component.denominator) if component.denominator != 0 else float(component.numerator)
            # Otherwise assume it's a tuple (numerator, denominator)
            elif isinstance(component, (tuple, list)) and len(component) == 2:
                return float(component[0]) / float(component[1]) if component[1] != 0 else float(component[0])
            # Fallback: try to convert directly to float
            else:
                return float(component)

        # Convert EXIF rational tuples/objects to floats
        lat_deg = _convert_to_float(gps_latitude[0])
        lat_min = _convert_to_float(gps_latitude[1])
        lat_sec = _convert_to_float(gps_latitude[2])

        lon_deg = _convert_to_float(gps_longitude[0])
        lon_min = _convert_to_float(gps_longitude[1])
        lon_sec = _convert_to_float(gps_longitude[2])

        return cls.from_dms(
            lat_deg, lat_min, lat_sec, gps_latitude_ref,
            lon_deg, lon_min, lon_sec, gps_longitude_ref,
        )

    def to_tuple(self) -> Tuple[Decimal, Decimal]:
        """Return as (latitude, longitude) tuple for database storage."""
        return (self.latitude, self.longitude)


@dataclass(frozen=True)
class ExifMetadata:
    """
    Immutable EXIF metadata value object.

    Represents extracted metadata from an image's EXIF tags.
    All fields are optional as EXIF data may be absent.
    """
    datetime_utc: Optional[datetime] = None
    gps: Optional[GpsCoordinate] = None
    caption: Optional[str] = None
    tags: Tuple[str, ...] = ()  # Immutable tuple instead of list
    timezone: Optional[str] = None  # IANA timezone name if detected from EXIF

    @property
    def timezone_unknown(self) -> bool:
        """Whether timezone is uncertain (no timezone information available)."""
        return self.timezone is None

    @classmethod
    def empty(cls) -> 'ExifMetadata':
        """Create empty metadata (no EXIF data found)."""
        return cls()

    @property
    def has_exif(self) -> bool:
        """Check if any EXIF data was successfully extracted (calculated property)."""
        return any([
            self.datetime_utc is not None,
            self.gps is not None,
            self.caption is not None,
            len(self.tags) > 0,
        ])

    def has_any_data(self) -> bool:
        """Alias for has_exif property (kept for compatibility)."""
        return self.has_exif

    def to_dict(self) -> dict:
        """
        Convert to dictionary format for database storage.

        Returns:
            Dictionary with fields compatible with TripImage model
        """
        return {
            'datetime_utc': self.datetime_utc,
            'latitude': self.gps.latitude if self.gps else None,
            'longitude': self.gps.longitude if self.gps else None,
            'caption': self.caption,
            'tags': list(self.tags),  # Convert tuple back to list for JSON field
            'has_exif': self.has_any_data(),  # Use has_any_data() for determination
            'timezone': self.timezone,
        }


@dataclass(frozen=True)
class ImageDimensions:
    """
    Immutable image dimensions value object.

    Encapsulates image size and aspect ratio calculations.
    """
    width: int
    height: int

    def __post_init__(self):
        """Validate dimensions are positive."""
        if self.width <= 0:
            raise ValueError(f"Width must be positive, got {self.width}")
        if self.height <= 0:
            raise ValueError(f"Height must be positive, got {self.height}")

    @property
    def aspect_ratio(self) -> float:
        """Calculate aspect ratio (width / height)."""
        return self.width / self.height

    @property
    def is_landscape(self) -> bool:
        """Check if image is landscape orientation."""
        return self.width > self.height

    @property
    def is_portrait(self) -> bool:
        """Check if image is portrait orientation."""
        return self.height > self.width

    @property
    def is_square(self) -> bool:
        """Check if image is square."""
        return self.width == self.height

    @property
    def max_dimension(self) -> int:
        """Get the larger of width or height."""
        return max(self.width, self.height)

    def needs_resize(self, max_dimension: int) -> bool:
        """
        Check if image needs resizing to fit within max_dimension.

        Args:
            max_dimension: Maximum allowed width or height

        Returns:
            True if image exceeds max_dimension
        """
        return self.width > max_dimension or self.height > max_dimension

    def calculate_resized_dimensions(self, max_dimension: int) -> 'ImageDimensions':
        """
        Calculate new dimensions to fit within max_dimension while preserving aspect ratio.

        Args:
            max_dimension: Maximum allowed width or height

        Returns:
            New ImageDimensions with resized dimensions, or self if no resize needed
        """
        if not self.needs_resize(max_dimension):
            return self

        if self.is_landscape or self.is_square:
            # Width is limiting factor
            new_width = max_dimension
            new_height = int((self.height / self.width) * max_dimension)
        else:
            # Height is limiting factor
            new_height = max_dimension
            new_width = int((self.width / self.height) * max_dimension)

        return ImageDimensions(width=new_width, height=new_height)

    def calculate_thumbnail_size(self) -> 'ImageDimensions':
        """
        Calculate thumbnail dimensions using configured max dimension.

        Returns:
            ImageDimensions for thumbnail
        """
        return self.calculate_resized_dimensions(ImageProcessingConfig.THUMBNAIL_MAX_DIMENSION)

    def to_tuple(self) -> Tuple[int, int]:
        """Return as (width, height) tuple for PIL operations."""
        return (self.width, self.height)


@dataclass(frozen=True)
class ValidationResult:
    """
    Immutable validation result value object.

    Represents the outcome of file validation.
    """
    is_valid: bool
    error_message: Optional[str] = None

    @classmethod
    def success(cls) -> 'ValidationResult':
        """Create successful validation result."""
        return cls(is_valid=True, error_message=None)

    @classmethod
    def failure(cls, error_message: str) -> 'ValidationResult':
        """Create failed validation result with error message."""
        return cls(is_valid=False, error_message=error_message)

    def to_tuple(self) -> Tuple[bool, Optional[str]]:
        """Return as (is_valid, error_message) tuple for backward compatibility."""
        return (self.is_valid, self.error_message)
