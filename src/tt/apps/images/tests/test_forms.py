"""
Tests for TripImage forms.

Tests form validation, data processing, and business logic.
"""
import logging
import tempfile
from datetime import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
import pytz

from tt.apps.images.models import TripImage
from tt.apps.images.forms import TripImageEditForm

User = get_user_model()
logging.disable(logging.CRITICAL)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class TripImageEditFormTestCase(TestCase):
    """Test TripImageEditForm validation and processing."""

    def setUp(self):
        self.user = User.objects.create_user(
            email='user@example.com',
            password='password',
        )
        self.trip_image = TripImage.objects.create(
            uploaded_by=self.user,
            caption='Original caption',
            datetime_utc=datetime(2025, 1, 15, 14, 30, tzinfo=pytz.UTC),
            latitude=Decimal('37.7749'),
            longitude=Decimal('-122.4194'),
            tags=['original', 'test'],
        )

    def test_form_initialization_with_instance(self):
        """Form should populate initial data from instance."""
        form = TripImageEditForm(instance=self.trip_image)

        self.assertEqual(form.initial['caption'], 'Original caption')
        self.assertEqual(form.initial['gps_coordinates'], '37.7749, -122.4194')
        self.assertEqual(form.initial['tags_input'], 'original, test')

    def test_valid_caption_update(self):
        """Valid caption update should save successfully."""
        form = TripImageEditForm(
            data={
                'caption': 'Updated caption',
                'datetime_utc': '2025-01-15T14:30',
                'gps_coordinates': '37.7749, -122.4194',
                'tags_input': 'original, test',
            },
            instance=self.trip_image,
        )

        self.assertTrue(form.is_valid(), form.errors)
        image = form.save(user=self.user)
        self.assertEqual(image.caption, 'Updated caption')

    def test_valid_datetime_update(self):
        """Valid datetime update should save correctly."""
        form = TripImageEditForm(
            data={
                'caption': 'Original caption',
                'datetime_utc': '2025-01-16T10:00',
                'gps_coordinates': '37.7749, -122.4194',
                'tags_input': 'original, test',
                'timezone': 'America/Los_Angeles',
            },
            instance=self.trip_image,
        )

        self.assertTrue(form.is_valid(), form.errors)
        image = form.save(user=self.user)

        # Verify datetime was updated
        self.assertEqual(image.datetime_utc.year, 2025)
        self.assertEqual(image.datetime_utc.month, 1)
        self.assertEqual(image.datetime_utc.day, 16)
        self.assertEqual(image.datetime_utc.hour, 10)
        self.assertEqual(image.datetime_utc.minute, 0)

        # Verify timezone was set
        self.assertEqual('America/Los_Angeles', image.timezone)
        self.assertFalse(image.timezone_unknown)  # Property returns False when timezone is set

    def test_gps_coordinates_decimal_degrees(self):
        """GPS coordinates in decimal degrees should parse correctly."""
        form = TripImageEditForm(
            data={
                'caption': 'Test',
                'datetime_utc': '2025-01-15T14:30',
                'gps_coordinates': '40.7128, -74.0060',
                'tags_input': '',
            },
            instance=self.trip_image,
        )

        self.assertTrue(form.is_valid(), form.errors)
        image = form.save(user=self.user)

        self.assertEqual(image.latitude, Decimal('40.7128'))
        self.assertEqual(image.longitude, Decimal('-74.0060'))

    def test_gps_coordinates_with_direction_letters(self):
        """GPS coordinates with direction letters should parse correctly."""
        form = TripImageEditForm(
            data={
                'caption': 'Test',
                'datetime_utc': '2025-01-15T14:30',
                'gps_coordinates': '40.7128N 74.0060W',  # No comma, space separator
                'tags_input': '',
            },
            instance=self.trip_image,
        )

        self.assertTrue(form.is_valid(), form.errors)
        image = form.save(user=self.user)

        self.assertAlmostEqual(float(image.latitude), 40.7128, places=4)
        self.assertAlmostEqual(float(image.longitude), -74.0060, places=4)

    def test_gps_coordinates_empty_clears_location(self):
        """Empty GPS coordinates should clear latitude and longitude."""
        form = TripImageEditForm(
            data={
                'caption': 'Test',
                'datetime_utc': '2025-01-15T14:30',
                'gps_coordinates': '',
                'tags_input': '',
            },
            instance=self.trip_image,
        )

        self.assertTrue(form.is_valid(), form.errors)
        image = form.save(user=self.user)

        self.assertIsNone(image.latitude)
        self.assertIsNone(image.longitude)

    def test_gps_coordinates_invalid_format(self):
        """Invalid GPS coordinates should fail validation."""
        form = TripImageEditForm(
            data={
                'caption': 'Test',
                'datetime_utc': '2025-01-15T14:30',
                'gps_coordinates': 'invalid coordinates',
                'tags_input': '',
            },
            instance=self.trip_image,
        )

        self.assertFalse(form.is_valid())
        self.assertIn('gps_coordinates', form.errors)

    def test_tags_comma_separated_parsing(self):
        """Tags should be parsed from comma-separated input."""
        form = TripImageEditForm(
            data={
                'caption': 'Test',
                'datetime_utc': '2025-01-15T14:30',
                'gps_coordinates': '37.7749, -122.4194',
                'tags_input': 'beach, sunset, vacation',
            },
            instance=self.trip_image,
        )

        self.assertTrue(form.is_valid(), form.errors)
        image = form.save(user=self.user)

        self.assertEqual(image.tags, ['beach', 'sunset', 'vacation'])

    def test_tags_whitespace_trimming(self):
        """Tags should have whitespace trimmed."""
        form = TripImageEditForm(
            data={
                'caption': 'Test',
                'datetime_utc': '2025-01-15T14:30',
                'gps_coordinates': '37.7749, -122.4194',
                'tags_input': '  beach  ,  sunset  ,  vacation  ',
            },
            instance=self.trip_image,
        )

        self.assertTrue(form.is_valid(), form.errors)
        image = form.save(user=self.user)

        self.assertEqual(image.tags, ['beach', 'sunset', 'vacation'])

    def test_tags_empty_clears_tags(self):
        """Empty tags input should clear tags list."""
        form = TripImageEditForm(
            data={
                'caption': 'Test',
                'datetime_utc': '2025-01-15T14:30',
                'gps_coordinates': '37.7749, -122.4194',
                'tags_input': '',
            },
            instance=self.trip_image,
        )

        self.assertTrue(form.is_valid(), form.errors)
        image = form.save(user=self.user)

        self.assertEqual(image.tags, [])

    def test_tag_max_length_validation(self):
        """Tags exceeding 50 characters should fail validation."""
        long_tag = 'a' * 51
        form = TripImageEditForm(
            data={
                'caption': 'Test',
                'datetime_utc': '2025-01-15T14:30',
                'gps_coordinates': '37.7749, -122.4194',
                'tags_input': f'{long_tag}, valid_tag',
            },
            instance=self.trip_image,
        )

        self.assertFalse(form.is_valid())
        self.assertIn('tags_input', form.errors)

    def test_modified_by_tracking(self):
        """Form save should track modified_by user."""
        form = TripImageEditForm(
            data={
                'caption': 'Updated caption',
                'datetime_utc': '2025-01-15T14:30',
                'gps_coordinates': '37.7749, -122.4194',
                'tags_input': 'test',
            },
            instance=self.trip_image,
        )

        self.assertTrue(form.is_valid(), form.errors)
        image = form.save(user=self.user)

        self.assertEqual(image.modified_by, self.user)

    def test_modified_datetime_auto_updates(self):
        """Form save should auto-update modified_datetime."""
        original_modified = self.trip_image.modified_datetime

        form = TripImageEditForm(
            data={
                'caption': 'Updated caption',
                'datetime_utc': '2025-01-15T14:30',
                'gps_coordinates': '37.7749, -122.4194',
                'tags_input': 'test',
            },
            instance=self.trip_image,
        )

        self.assertTrue(form.is_valid(), form.errors)
        image = form.save(user=self.user)

        # modified_datetime should be updated (will be different)
        self.assertNotEqual(image.modified_datetime, original_modified)

    def test_timezone_field_can_be_set_via_form(self):
        """Timezone field can be set via form and timezone_unknown property works correctly."""
        # Start with no timezone set
        self.trip_image.timezone = None
        self.trip_image.save()
        self.assertTrue(self.trip_image.timezone_unknown)  # Property should return True

        # Set timezone via form
        form = TripImageEditForm(
            data={
                'caption': 'Updated caption',
                'datetime_utc': '2025-01-16T10:00',
                'gps_coordinates': '37.7749, -122.4194',
                'tags_input': 'test',
                'timezone': 'America/New_York',
            },
            instance=self.trip_image,
        )

        self.assertTrue(form.is_valid(), form.errors)
        image = form.save(user=self.user)

        # timezone should be set and timezone_unknown property should return False
        self.assertEqual('America/New_York', image.timezone)
        self.assertFalse(image.timezone_unknown)  # Property returns False when timezone is set
