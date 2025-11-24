"""
Tests for JournalImagePickerService - focusing on date boundary security.

Tests timezone-aware date boundary calculations to prevent unauthorized image access.
"""
import logging

from datetime import date, datetime, timezone as dt_timezone

from django.contrib.auth import get_user_model
from django.test import TestCase

from tt.apps.images.models import TripImage
from tt.apps.journal.enums import ImagePickerScope
from tt.apps.journal.services import JournalImagePickerService
from tt.apps.journal.utils import JournalUtils
from tt.apps.trips.tests.synthetic_data import TripSyntheticData

logging.disable(logging.CRITICAL)

User = get_user_model()


class TestJournalImagePickerDateBoundaries(TestCase):
    """Test timezone-aware date boundary calculations for image picker."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(email='test@test.com', password='pass')
        self.trip = TripSyntheticData.create_test_trip(user=self.user)

    def test_date_boundaries_timezone_edge_cases(self):
        """Test date boundaries across timezone offsets."""
        # Test UTC
        start, end = JournalUtils.get_entry_date_boundaries(
            date(2024, 1, 15),
            'UTC'
        )
        self.assertEqual(start.hour, 0)
        self.assertEqual(start.minute, 0)
        self.assertEqual(end.hour, 0)
        self.assertEqual(end.day, 16)

        # Test negative offset (Eastern Time)
        start, end = JournalUtils.get_entry_date_boundaries(
            date(2024, 1, 15),
            'America/New_York'
        )
        # Verify timezone aware (has tzinfo)
        self.assertIsNotNone(start.tzinfo)
        self.assertIsNotNone(end.tzinfo)

        # Test positive offset (Tokyo)
        start, end = JournalUtils.get_entry_date_boundaries(
            date(2024, 1, 15),
            'Asia/Tokyo'
        )
        self.assertIsNotNone(start.tzinfo)

    def test_date_boundaries_dst_transitions(self):
        """Test date boundaries during DST transitions cover the full local day."""
        # Spring forward: March 10, 2024 (DST begins in US)
        start, end = JournalUtils.get_entry_date_boundaries(
            date(2024, 3, 10),
            'America/New_York'
        )

        # Spring forward day is 23 hours (clock jumps from 2am to 3am)
        duration = end - start
        self.assertEqual(duration.total_seconds(), 82800)  # 23 hours

        # Fall back: November 3, 2024 (DST ends in US)
        start, end = JournalUtils.get_entry_date_boundaries(
            date(2024, 11, 3),
            'America/New_York'
        )

        # Fall back day is 25 hours (clock goes back from 2am to 1am)
        duration = end - start
        self.assertEqual(duration.total_seconds(), 90000)  # 25 hours

    def test_get_accessible_images_date_boundary_enforcement(self):
        """Test image picker only returns images within date boundaries."""
        # Create images at different times
        # Image at 23:59:59 on target date (should be included)
        img1 = TripImage.objects.create(
            uploaded_by=self.user,
            datetime_utc=datetime(2024, 1, 15, 23, 59, 59, tzinfo=dt_timezone.utc),
        )

        # Image at 00:00:01 next day (should NOT be included)
        img2 = TripImage.objects.create(
            uploaded_by=self.user,
            datetime_utc=datetime(2024, 1, 16, 0, 0, 1, tzinfo=dt_timezone.utc),
        )

        # Get images for Jan 15, 2024 in UTC
        images = JournalImagePickerService.get_accessible_images_for_image_picker(
            trip=self.trip,
            user=self.user,
            date=date(2024, 1, 15),
            timezone='UTC',
            scope=ImagePickerScope.DEFAULT
        )

        # Only img1 should be included
        image_ids = [img.id for img in images]
        self.assertIn(img1.id, image_ids)
        self.assertNotIn(img2.id, image_ids)

    def test_get_accessible_images_timezone_boundary_security(self):
        """Test timezone manipulation can't access unauthorized images."""
        # Create image at midnight UTC on Jan 16
        img = TripImage.objects.create(
            uploaded_by=self.user,
            datetime_utc=datetime(2024, 1, 16, 0, 0, 0, tzinfo=dt_timezone.utc),
        )

        # Query for Jan 15 in UTC - should NOT include midnight image
        images_utc = JournalImagePickerService.get_accessible_images_for_image_picker(
            trip=self.trip,
            user=self.user,
            date=date(2024, 1, 15),
            timezone='UTC',
            scope=ImagePickerScope.DEFAULT
        )
        utc_image_ids = [img.id for img in images_utc]
        self.assertNotIn(img.id, utc_image_ids)

        # Query for Jan 15 in Pacific time (UTC-8) - SHOULD include
        # (midnight UTC = 4pm PST on Jan 15, which IS part of Jan 15 PST day)
        images_pst = JournalImagePickerService.get_accessible_images_for_image_picker(
            trip=self.trip,
            user=self.user,
            date=date(2024, 1, 15),
            timezone='America/Los_Angeles',
            scope=ImagePickerScope.DEFAULT
        )
        pst_image_ids = [img.id for img in images_pst]
        self.assertIn(img.id, pst_image_ids)

        # But query for Jan 16 in PST should NOT include it
        # (midnight UTC = 4pm PST Jan 15, so it belongs to Jan 15 PST, not Jan 16 PST)
        images_pst_16 = JournalImagePickerService.get_accessible_images_for_image_picker(
            trip=self.trip,
            user=self.user,
            date=date(2024, 1, 16),
            timezone='America/Los_Angeles',
            scope=ImagePickerScope.DEFAULT
        )
        pst_16_image_ids = [img.id for img in images_pst_16]
        self.assertNotIn(img.id, pst_16_image_ids)

    def test_chronological_ordering_preserved(self):
        """Test images are returned in chronological order."""
        # Create images at different times on same date
        img_morning = TripImage.objects.create(
            uploaded_by=self.user,
            datetime_utc=datetime(2024, 1, 15, 8, 0, 0, tzinfo=dt_timezone.utc),
        )

        img_evening = TripImage.objects.create(
            uploaded_by=self.user,
            datetime_utc=datetime(2024, 1, 15, 20, 0, 0, tzinfo=dt_timezone.utc),
        )

        img_noon = TripImage.objects.create(
            uploaded_by=self.user,
            datetime_utc=datetime(2024, 1, 15, 12, 0, 0, tzinfo=dt_timezone.utc),
        )

        # Get images for the date
        images = JournalImagePickerService.get_accessible_images_for_image_picker(
            trip=self.trip,
            user=self.user,
            date=date(2024, 1, 15),
            timezone='UTC',
            scope=ImagePickerScope.DEFAULT
        )

        # Should be in chronological order
        image_list = list(images)
        self.assertEqual(len(image_list), 3)
        self.assertEqual(image_list[0].id, img_morning.id)
        self.assertEqual(image_list[1].id, img_noon.id)
        self.assertEqual(image_list[2].id, img_evening.id)

    def test_invalid_timezone_handling(self):
        """Test service handles invalid timezone gracefully."""
        # Invalid timezone should raise exception (not security bypass)
        with self.assertRaises(Exception):  # Could be pytz.UnknownTimeZoneError or similar
            JournalImagePickerService.get_accessible_images_for_image_picker(
                trip=self.trip,
                user=self.user,
                date=date(2024, 1, 15),
                timezone='Invalid/Timezone',
                scope=ImagePickerScope.DEFAULT
            )

    def test_date_boundary_precision_security(self):
        """Test date boundaries are precise to the second (no rounding issues)."""
        # Create image exactly at boundary
        boundary_img = TripImage.objects.create(
            uploaded_by=self.user,
            datetime_utc=datetime(2024, 1, 16, 0, 0, 0, 0, tzinfo=dt_timezone.utc),  # Exact midnight
        )

        # Query for Jan 15 - should NOT include boundary image
        images_15 = JournalImagePickerService.get_accessible_images_for_image_picker(
            trip=self.trip,
            user=self.user,
            date=date(2024, 1, 15),
            timezone='UTC',
            scope=ImagePickerScope.DEFAULT
        )
        image_15_ids = [img.id for img in images_15]
        self.assertNotIn(boundary_img.id, image_15_ids)

        # Query for Jan 16 - should include boundary image
        images_16 = JournalImagePickerService.get_accessible_images_for_image_picker(
            trip=self.trip,
            user=self.user,
            date=date(2024, 1, 16),
            timezone='UTC',
            scope=ImagePickerScope.DEFAULT
        )
        image_16_ids = [img.id for img in images_16]
        self.assertIn(boundary_img.id, image_16_ids)

    def test_timezone_abbreviation_vs_full_names(self):
        """Test different timezone name formats work consistently."""
        # Create test image
        TripImage.objects.create(
            uploaded_by=self.user,
            datetime_utc=datetime(2024, 1, 15, 12, 0, 0, tzinfo=dt_timezone.utc),
        )

        # Test various timezone name formats
        timezone_variants = [
            'America/New_York',
            'US/Eastern',
            # Note: We don't test abbreviations like 'EST' as they are ambiguous
        ]

        results = []
        for tz in timezone_variants:
            images = JournalImagePickerService.get_accessible_images_for_image_picker(
                trip=self.trip,
                user=self.user,
                date=date(2024, 1, 15),
                timezone=tz,
                scope=ImagePickerScope.DEFAULT
            )
            results.append(len(list(images)))

        # All valid timezone names should return same results
        self.assertEqual(len(set(results)), 1,
                         f"Different timezone names gave different results: {dict(zip(timezone_variants, results))}")

    def test_leap_year_date_boundaries(self):
        """Test date boundaries work correctly during leap year."""
        # Test Feb 29, 2024 (leap year)
        start, end = JournalUtils.get_entry_date_boundaries(
            date(2024, 2, 29),
            'UTC'
        )

        self.assertEqual(start.day, 29)
        self.assertEqual(start.month, 2)
        self.assertEqual(end.day, 1)
        self.assertEqual(end.month, 3)

        # Verify 24 hour duration
        duration = end - start
        self.assertEqual(duration.total_seconds(), 86400)

    def test_year_boundary_date_calculations(self):
        """Test date boundaries work correctly at year boundaries."""
        # Test Dec 31 to Jan 1 transition
        start, end = JournalUtils.get_entry_date_boundaries(
            date(2024, 12, 31),
            'UTC'
        )

        self.assertEqual(start.day, 31)
        self.assertEqual(start.month, 12)
        self.assertEqual(start.year, 2024)
        self.assertEqual(end.day, 1)
        self.assertEqual(end.month, 1)
        self.assertEqual(end.year, 2025)

        # Verify 24 hour duration
        duration = end - start
        self.assertEqual(duration.total_seconds(), 86400)
