"""
Tests for domain models and value objects.

Tests immutable value objects, validation, and business rule encapsulation.
"""
import logging
from datetime import datetime, timezone
from decimal import Decimal

from django.test import TestCase

from tt.apps.images.domain import (
    GpsCoordinate,
    ExifMetadata,
    ImageDimensions,
    ValidationResult,
    ImageProcessingConfig,
)

logging.disable(logging.CRITICAL)


class GpsCoordinateTestCase(TestCase):
    """Test GpsCoordinate value object."""

    def test_create_valid_coordinate(self):
        """Valid GPS coordinates should be accepted."""
        gps = GpsCoordinate(latitude=Decimal('48.208176'), longitude=Decimal('16.373819'))

        self.assertEqual(Decimal('48.208176'), gps.latitude)
        self.assertEqual(Decimal('16.373819'), gps.longitude)

    def test_latitude_validation_too_high(self):
        """Latitude > 90 should raise ValueError."""
        with self.assertRaises(ValueError) as cm:
            GpsCoordinate(latitude=Decimal('91.0'), longitude=Decimal('0.0'))

        self.assertIn('Latitude must be between -90 and 90', str(cm.exception))

    def test_latitude_validation_too_low(self):
        """Latitude < -90 should raise ValueError."""
        with self.assertRaises(ValueError) as cm:
            GpsCoordinate(latitude=Decimal('-91.0'), longitude=Decimal('0.0'))

        self.assertIn('Latitude must be between -90 and 90', str(cm.exception))

    def test_longitude_validation_too_high(self):
        """Longitude > 180 should raise ValueError."""
        with self.assertRaises(ValueError) as cm:
            GpsCoordinate(latitude=Decimal('0.0'), longitude=Decimal('181.0'))

        self.assertIn('Longitude must be between -180 and 180', str(cm.exception))

    def test_longitude_validation_too_low(self):
        """Longitude < -180 should raise ValueError."""
        with self.assertRaises(ValueError) as cm:
            GpsCoordinate(latitude=Decimal('0.0'), longitude=Decimal('-181.0'))

        self.assertIn('Longitude must be between -180 and 180', str(cm.exception))

    def test_from_dms_north_east(self):
        """DMS coordinates in NE quadrant should convert correctly."""
        # Vienna: 48° 12' 29.4336" N, 16° 22' 25.7484" E
        gps = GpsCoordinate.from_dms(
            lat_degrees=48, lat_minutes=12, lat_seconds=29.4336, lat_ref='N',
            lon_degrees=16, lon_minutes=22, lon_seconds=25.7484, lon_ref='E',
        )

        self.assertAlmostEqual(48.208176, float(gps.latitude), places=5)
        self.assertAlmostEqual(16.373819, float(gps.longitude), places=5)

    def test_from_dms_south_west(self):
        """DMS coordinates in SW quadrant should be negative."""
        # Buenos Aires: 34° 36' 12" S, 58° 22' 54" W
        gps = GpsCoordinate.from_dms(
            lat_degrees=34, lat_minutes=36, lat_seconds=12, lat_ref='S',
            lon_degrees=58, lon_minutes=22, lon_seconds=54, lon_ref='W',
        )

        self.assertAlmostEqual(-34.603333, float(gps.latitude), places=5)
        self.assertAlmostEqual(-58.381667, float(gps.longitude), places=5)

    def test_from_exif_gps_tuple(self):
        """EXIF GPS tuple format should convert correctly."""
        # EXIF stores as tuples of rationals: ((degrees_num, degrees_den), ...)
        gps_lat = ((48, 1), (12, 1), (2943336, 100000))  # 48° 12' 29.4336"
        gps_lon = ((16, 1), (22, 1), (2574840, 100000))  # 16° 22' 25.7484"

        gps = GpsCoordinate.from_exif_gps_tuple(gps_lat, 'N', gps_lon, 'E')

        self.assertAlmostEqual(48.208176, float(gps.latitude), places=5)
        self.assertAlmostEqual(16.373819, float(gps.longitude), places=5)

    def test_to_tuple(self):
        """to_tuple() should return (lat, lon) for database storage."""
        gps = GpsCoordinate(latitude=Decimal('48.208176'), longitude=Decimal('16.373819'))

        result = gps.to_tuple()

        self.assertEqual((Decimal('48.208176'), Decimal('16.373819')), result)

    def test_immutability(self):
        """GpsCoordinate should be immutable (frozen dataclass)."""
        gps = GpsCoordinate(latitude=Decimal('48.0'), longitude=Decimal('16.0'))

        with self.assertRaises(Exception):  # FrozenInstanceError or AttributeError
            gps.latitude = Decimal('50.0')


class ExifMetadataTestCase(TestCase):
    """Test ExifMetadata value object."""

    def test_create_empty_metadata(self):
        """Empty metadata should have all None/empty values."""
        metadata = ExifMetadata.empty()

        self.assertIsNone(metadata.datetime_utc)
        self.assertIsNone(metadata.gps)
        self.assertIsNone(metadata.caption)
        self.assertEqual((), metadata.tags)
        self.assertFalse(metadata.has_exif)
        self.assertFalse(metadata.timezone_unknown)

    def test_create_metadata_with_datetime(self):
        """Metadata with only datetime should have has_exif=True."""
        dt = datetime(2024, 6, 15, 10, 0, 0, tzinfo=timezone.utc)
        metadata = ExifMetadata(datetime_utc=dt)

        self.assertEqual(dt, metadata.datetime_utc)
        self.assertTrue(metadata.has_exif)

    def test_create_metadata_with_gps(self):
        """Metadata with only GPS should have has_exif=True."""
        gps = GpsCoordinate(latitude=Decimal('48.0'), longitude=Decimal('16.0'))
        metadata = ExifMetadata(gps=gps)

        self.assertEqual(gps, metadata.gps)
        self.assertTrue(metadata.has_exif)

    def test_create_metadata_with_caption(self):
        """Metadata with only caption should have has_exif=True."""
        metadata = ExifMetadata(caption="Beautiful sunset")

        self.assertEqual("Beautiful sunset", metadata.caption)
        self.assertTrue(metadata.has_exif)

    def test_create_metadata_with_tags(self):
        """Metadata with only tags should have has_exif=True."""
        metadata = ExifMetadata(tags=('vacation', 'beach'))

        self.assertEqual(('vacation', 'beach'), metadata.tags)
        self.assertTrue(metadata.has_exif)

    def test_has_exif_calculated_property(self):
        """has_exif should be automatically calculated from data presence."""
        # No data
        metadata1 = ExifMetadata()
        self.assertFalse(metadata1.has_exif)

        # With datetime
        metadata2 = ExifMetadata(datetime_utc=datetime.now(timezone.utc))
        self.assertTrue(metadata2.has_exif)

        # With GPS
        gps = GpsCoordinate(latitude=Decimal('0'), longitude=Decimal('0'))
        metadata3 = ExifMetadata(gps=gps)
        self.assertTrue(metadata3.has_exif)

    def test_to_dict_conversion(self):
        """to_dict() should convert to database-compatible format."""
        gps = GpsCoordinate(latitude=Decimal('48.208176'), longitude=Decimal('16.373819'))
        dt = datetime(2024, 6, 15, 8, 38, 0, tzinfo=timezone.utc)
        metadata = ExifMetadata(
            datetime_utc=dt,
            gps=gps,
            caption="Vienna",
            tags=('travel', 'austria'),
            timezone_unknown=False,
        )

        result = metadata.to_dict()

        self.assertEqual(dt, result['datetime_utc'])
        self.assertEqual(Decimal('48.208176'), result['latitude'])
        self.assertEqual(Decimal('16.373819'), result['longitude'])
        self.assertEqual("Vienna", result['caption'])
        self.assertEqual(['travel', 'austria'], result['tags'])  # Converted to list
        self.assertTrue(result['has_exif'])
        self.assertFalse(result['timezone_unknown'])

    def test_to_dict_with_no_gps(self):
        """to_dict() with no GPS should have None lat/lon."""
        metadata = ExifMetadata(caption="No GPS data")

        result = metadata.to_dict()

        self.assertIsNone(result['latitude'])
        self.assertIsNone(result['longitude'])

    def test_tags_immutable(self):
        """Tags should be stored as immutable tuple."""
        metadata = ExifMetadata(tags=('a', 'b', 'c'))

        self.assertIsInstance(metadata.tags, tuple)
        with self.assertRaises(Exception):  # Tuple is immutable
            metadata.tags[0] = 'x'

    def test_immutability(self):
        """ExifMetadata should be immutable (frozen dataclass)."""
        metadata = ExifMetadata(caption="Test")

        with self.assertRaises(Exception):  # FrozenInstanceError or AttributeError
            metadata.caption = "Modified"


class ImageDimensionsTestCase(TestCase):
    """Test ImageDimensions value object."""

    def test_create_valid_dimensions(self):
        """Valid dimensions should be accepted."""
        dims = ImageDimensions(width=1920, height=1080)

        self.assertEqual(1920, dims.width)
        self.assertEqual(1080, dims.height)

    def test_width_validation(self):
        """Width must be positive."""
        with self.assertRaises(ValueError) as cm:
            ImageDimensions(width=0, height=100)

        self.assertIn('Width must be positive', str(cm.exception))

    def test_height_validation(self):
        """Height must be positive."""
        with self.assertRaises(ValueError) as cm:
            ImageDimensions(width=100, height=-5)

        self.assertIn('Height must be positive', str(cm.exception))

    def test_aspect_ratio_landscape(self):
        """Aspect ratio should be width / height."""
        dims = ImageDimensions(width=1920, height=1080)

        self.assertAlmostEqual(1.777778, dims.aspect_ratio, places=5)

    def test_aspect_ratio_portrait(self):
        """Portrait aspect ratio should be < 1."""
        dims = ImageDimensions(width=1080, height=1920)

        self.assertAlmostEqual(0.5625, dims.aspect_ratio, places=5)

    def test_is_landscape(self):
        """Landscape images should return True for is_landscape."""
        landscape = ImageDimensions(width=1920, height=1080)
        portrait = ImageDimensions(width=1080, height=1920)
        square = ImageDimensions(width=1000, height=1000)

        self.assertTrue(landscape.is_landscape)
        self.assertFalse(portrait.is_landscape)
        self.assertFalse(square.is_landscape)

    def test_is_portrait(self):
        """Portrait images should return True for is_portrait."""
        landscape = ImageDimensions(width=1920, height=1080)
        portrait = ImageDimensions(width=1080, height=1920)
        square = ImageDimensions(width=1000, height=1000)

        self.assertFalse(landscape.is_portrait)
        self.assertTrue(portrait.is_portrait)
        self.assertFalse(square.is_portrait)

    def test_is_square(self):
        """Square images should return True for is_square."""
        landscape = ImageDimensions(width=1920, height=1080)
        portrait = ImageDimensions(width=1080, height=1920)
        square = ImageDimensions(width=1000, height=1000)

        self.assertFalse(landscape.is_square)
        self.assertFalse(portrait.is_square)
        self.assertTrue(square.is_square)

    def test_max_dimension(self):
        """max_dimension should return the larger of width or height."""
        landscape = ImageDimensions(width=1920, height=1080)
        portrait = ImageDimensions(width=1080, height=1920)

        self.assertEqual(1920, landscape.max_dimension)
        self.assertEqual(1920, portrait.max_dimension)

    def test_needs_resize_exceeds_limit(self):
        """Images exceeding limit should need resize."""
        dims = ImageDimensions(width=2000, height=1500)

        self.assertTrue(dims.needs_resize(1600))

    def test_needs_resize_within_limit(self):
        """Images within limit should not need resize."""
        dims = ImageDimensions(width=1200, height=800)

        self.assertFalse(dims.needs_resize(1600))

    def test_calculate_resized_dimensions_landscape(self):
        """Landscape image resize should maintain aspect ratio."""
        dims = ImageDimensions(width=2000, height=1000)

        resized = dims.calculate_resized_dimensions(1600)

        self.assertEqual(1600, resized.width)
        self.assertEqual(800, resized.height)
        # Aspect ratio preserved
        self.assertAlmostEqual(dims.aspect_ratio, resized.aspect_ratio, places=5)

    def test_calculate_resized_dimensions_portrait(self):
        """Portrait image resize should maintain aspect ratio."""
        dims = ImageDimensions(width=1000, height=2000)

        resized = dims.calculate_resized_dimensions(1600)

        self.assertEqual(800, resized.width)
        self.assertEqual(1600, resized.height)
        # Aspect ratio preserved
        self.assertAlmostEqual(dims.aspect_ratio, resized.aspect_ratio, places=5)

    def test_calculate_resized_dimensions_no_resize_needed(self):
        """If no resize needed, should return self."""
        dims = ImageDimensions(width=800, height=600)

        resized = dims.calculate_resized_dimensions(1600)

        self.assertEqual(dims, resized)
        self.assertIs(dims, resized)  # Same object

    def test_calculate_thumbnail_size(self):
        """Thumbnail should use configured max dimension."""
        dims = ImageDimensions(width=2000, height=1500)

        thumbnail = dims.calculate_thumbnail_size()

        self.assertEqual(ImageProcessingConfig.THUMBNAIL_MAX_DIMENSION, thumbnail.max_dimension)

    def test_to_tuple(self):
        """to_tuple() should return (width, height) for PIL."""
        dims = ImageDimensions(width=1920, height=1080)

        result = dims.to_tuple()

        self.assertEqual((1920, 1080), result)

    def test_immutability(self):
        """ImageDimensions should be immutable (frozen dataclass)."""
        dims = ImageDimensions(width=100, height=100)

        with self.assertRaises(Exception):  # FrozenInstanceError or AttributeError
            dims.width = 200


class ValidationResultTestCase(TestCase):
    """Test ValidationResult value object."""

    def test_success_factory(self):
        """success() should create successful result."""
        result = ValidationResult.success()

        self.assertTrue(result.is_valid)
        self.assertIsNone(result.error_message)

    def test_failure_factory(self):
        """failure() should create failed result with error message."""
        result = ValidationResult.failure("Invalid file format")

        self.assertFalse(result.is_valid)
        self.assertEqual("Invalid file format", result.error_message)

    def test_to_tuple(self):
        """to_tuple() should provide backward compatibility."""
        success = ValidationResult.success()
        failure = ValidationResult.failure("Error")

        self.assertEqual((True, None), success.to_tuple())
        self.assertEqual((False, "Error"), failure.to_tuple())

    def test_immutability(self):
        """ValidationResult should be immutable (frozen dataclass)."""
        result = ValidationResult.success()

        with self.assertRaises(Exception):  # FrozenInstanceError or AttributeError
            result.is_valid = False


class ImageProcessingConfigTestCase(TestCase):
    """Test ImageProcessingConfig constants."""

    def test_file_size_constants(self):
        """File size configuration should be defined."""
        self.assertEqual(20, ImageProcessingConfig.MAX_FILE_SIZE_MB)
        self.assertEqual(20 * 1024 * 1024, ImageProcessingConfig.MAX_FILE_SIZE_BYTES)

    def test_image_dimension_constants(self):
        """Image dimension configuration should be defined."""
        self.assertEqual(1600, ImageProcessingConfig.WEB_IMAGE_MAX_DIMENSION)
        self.assertEqual(350, ImageProcessingConfig.THUMBNAIL_MAX_DIMENSION)

    def test_quality_constants(self):
        """JPEG quality configuration should be defined."""
        self.assertEqual(90, ImageProcessingConfig.WEB_IMAGE_QUALITY)
        self.assertEqual(85, ImageProcessingConfig.THUMBNAIL_QUALITY)

    def test_format_constants(self):
        """Allowed formats should be defined."""
        self.assertIn('JPEG', ImageProcessingConfig.ALLOWED_FORMATS)
        self.assertIn('PNG', ImageProcessingConfig.ALLOWED_FORMATS)
        self.assertIn('MPO', ImageProcessingConfig.ALLOWED_FORMATS)

    def test_extension_constants(self):
        """Allowed extensions should be defined."""
        self.assertIn('.jpg', ImageProcessingConfig.ALLOWED_EXTENSIONS)
        self.assertIn('.jpeg', ImageProcessingConfig.ALLOWED_EXTENSIONS)
        self.assertIn('.png', ImageProcessingConfig.ALLOWED_EXTENSIONS)
