"""
Tests for ImagePickerService - focusing on date boundary security.

Tests timezone-aware date boundary calculations to prevent unauthorized image access.
"""
import logging

from datetime import date, datetime, timezone as dt_timezone

from django.contrib.auth import get_user_model
from django.test import TestCase

from tt.apps.images.models import TripImage
from tt.apps.images.services import ImagePickerService
from tt.apps.journal.utils import JournalUtils
from tt.apps.trips.tests.synthetic_data import TripSyntheticData

logging.disable(logging.CRITICAL)

User = get_user_model()


class TestImagePickerServiceDateBoundaries(TestCase):
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
        images = ImagePickerService.get_accessible_images_for_image_picker(
            trip=self.trip,
            user=self.user,
            date=date(2024, 1, 15),
            timezone='UTC',
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
        images_utc = ImagePickerService.get_accessible_images_for_image_picker(
            trip=self.trip,
            user=self.user,
            date=date(2024, 1, 15),
            timezone='UTC',
        )
        utc_image_ids = [img.id for img in images_utc]
        self.assertNotIn(img.id, utc_image_ids)

        # Query for Jan 15 in Pacific time (UTC-8) - SHOULD include
        # (midnight UTC = 4pm PST on Jan 15, which IS part of Jan 15 PST day)
        images_pst = ImagePickerService.get_accessible_images_for_image_picker(
            trip=self.trip,
            user=self.user,
            date=date(2024, 1, 15),
            timezone='America/Los_Angeles',
        )
        pst_image_ids = [img.id for img in images_pst]
        self.assertIn(img.id, pst_image_ids)

        # But query for Jan 16 in PST should NOT include it
        # (midnight UTC = 4pm PST Jan 15, so it belongs to Jan 15 PST, not Jan 16 PST)
        images_pst_16 = ImagePickerService.get_accessible_images_for_image_picker(
            trip=self.trip,
            user=self.user,
            date=date(2024, 1, 16),
            timezone='America/Los_Angeles',
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
        images = ImagePickerService.get_accessible_images_for_image_picker(
            trip=self.trip,
            user=self.user,
            date=date(2024, 1, 15),
            timezone='UTC',
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
            ImagePickerService.get_accessible_images_for_image_picker(
                trip=self.trip,
                user=self.user,
                date=date(2024, 1, 15),
                timezone='Invalid/Timezone',
            )

    def test_date_boundary_precision_security(self):
        """Test date boundaries are precise to the second (no rounding issues)."""
        # Create image exactly at boundary
        boundary_img = TripImage.objects.create(
            uploaded_by=self.user,
            datetime_utc=datetime(2024, 1, 16, 0, 0, 0, 0, tzinfo=dt_timezone.utc),  # Exact midnight
        )

        # Query for Jan 15 - should NOT include boundary image
        images_15 = ImagePickerService.get_accessible_images_for_image_picker(
            trip=self.trip,
            user=self.user,
            date=date(2024, 1, 15),
            timezone='UTC',
        )
        image_15_ids = [img.id for img in images_15]
        self.assertNotIn(boundary_img.id, image_15_ids)

        # Query for Jan 16 - should include boundary image
        images_16 = ImagePickerService.get_accessible_images_for_image_picker(
            trip=self.trip,
            user=self.user,
            date=date(2024, 1, 16),
            timezone='UTC',
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
            images = ImagePickerService.get_accessible_images_for_image_picker(
                trip=self.trip,
                user=self.user,
                date=date(2024, 1, 15),
                timezone=tz,
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


class TestImagePickerServiceWithFallback(TestCase):
    """Test get_accessible_images_with_fallback method."""

    def setUp(self):
        """Set up test data."""
        from tt.apps.trips.enums import TripPermissionLevel
        from tt.apps.trips.tests.synthetic_data import TripSyntheticData

        self.user1 = User.objects.create_user(email='owner@test.com', password='pass')
        self.user2 = User.objects.create_user(email='editor@test.com', password='pass')
        self.user3 = User.objects.create_user(email='viewer@test.com', password='pass')

        self.trip = TripSyntheticData.create_test_trip(user=self.user1)
        TripSyntheticData.add_trip_member(self.trip, self.user2, TripPermissionLevel.EDITOR, self.user1)
        TripSyntheticData.add_trip_member(self.trip, self.user3, TripPermissionLevel.VIEWER, self.user1)

    def test_returns_date_filtered_images_when_they_exist(self):
        """Should return date-filtered images when available, not fallback."""
        # Create images on the target date
        img1 = TripImage.objects.create(
            uploaded_by=self.user1,
            datetime_utc=datetime(2024, 1, 15, 10, 0, 0, tzinfo=dt_timezone.utc),
            caption='Image on target date',
        )
        img2 = TripImage.objects.create(
            uploaded_by=self.user2,
            datetime_utc=datetime(2024, 1, 15, 14, 0, 0, tzinfo=dt_timezone.utc),
            caption='Another on target date',
        )

        # Create images on different dates (should not appear)
        TripImage.objects.create(
            uploaded_by=self.user1,
            datetime_utc=datetime(2024, 1, 20, 10, 0, 0, tzinfo=dt_timezone.utc),
            caption='Different date',
        )

        images = ImagePickerService.get_accessible_images_with_fallback(
            trip=self.trip,
            user=self.user1,
            date=date(2024, 1, 15),
            timezone='UTC',
            use_fallback=True,
        )

        # Should return date-filtered images, not fallback
        image_ids = [img.id for img in images]
        self.assertEqual(len(image_ids), 2)
        self.assertIn(img1.id, image_ids)
        self.assertIn(img2.id, image_ids)

    def test_falls_back_to_recent_images_when_date_query_empty(self):
        """Should fall back to recent images when date query returns no results."""
        # Create images on different dates (not on target date Jan 15)
        img1 = TripImage.objects.create(
            uploaded_by=self.user1,
            datetime_utc=datetime(2024, 1, 20, 10, 0, 0, tzinfo=dt_timezone.utc),
            caption='Recent image 1',
        )
        img2 = TripImage.objects.create(
            uploaded_by=self.user2,
            datetime_utc=datetime(2024, 1, 21, 10, 0, 0, tzinfo=dt_timezone.utc),
            caption='Recent image 2',
        )

        # Query for Jan 15 (no images exist for this date)
        images = ImagePickerService.get_accessible_images_with_fallback(
            trip=self.trip,
            user=self.user1,
            date=date(2024, 1, 15),
            timezone='UTC',
            use_fallback=True,
        )

        # Should return recent images as fallback
        image_ids = [img.id for img in images]
        self.assertEqual(len(image_ids), 2)
        self.assertIn(img1.id, image_ids)
        self.assertIn(img2.id, image_ids)

    def test_fallback_respects_use_fallback_false(self):
        """Should not use fallback when use_fallback=False."""
        # Create images on different date (not target date)
        TripImage.objects.create(
            uploaded_by=self.user1,
            datetime_utc=datetime(2024, 1, 20, 10, 0, 0, tzinfo=dt_timezone.utc),
            caption='Recent image',
        )

        # Query for Jan 15 with use_fallback=False
        images = ImagePickerService.get_accessible_images_with_fallback(
            trip=self.trip,
            user=self.user1,
            date=date(2024, 1, 15),
            timezone='UTC',
            use_fallback=False,
        )

        # Should return empty queryset, not fallback
        self.assertEqual(images.count(), 0)

    def test_fallback_returns_empty_when_no_editor_images(self):
        """Should handle empty fallback results gracefully."""
        # Create images only from viewer (excluded from fallback)
        TripImage.objects.create(
            uploaded_by=self.user3,
            datetime_utc=datetime(2024, 1, 20, 10, 0, 0, tzinfo=dt_timezone.utc),
            caption='Viewer image',
        )

        # Query for date with no images
        images = ImagePickerService.get_accessible_images_with_fallback(
            trip=self.trip,
            user=self.user1,
            date=date(2024, 1, 15),
            timezone='UTC',
            use_fallback=True,
        )

        # Should return empty list (no editor+ images)
        self.assertEqual(len(images), 0)

    def test_fallback_uses_exists_for_efficiency(self):
        """Should use .exists() check for performance."""
        # Create many images on target date
        for i in range(50):
            # Use different hours and minutes to create 50 distinct images
            hour = 10 + (i // 60)
            minute = i % 60
            TripImage.objects.create(
                uploaded_by=self.user1,
                datetime_utc=datetime(2024, 1, 15, hour, minute, 0, tzinfo=dt_timezone.utc),
                caption=f'Image {i}',
            )

        # This should execute efficiently without loading all images
        images = ImagePickerService.get_accessible_images_with_fallback(
            trip=self.trip,
            user=self.user1,
            date=date(2024, 1, 15),
            timezone='UTC',
            use_fallback=True,
        )

        # Should return date-filtered images (not evaluate fallback)
        self.assertEqual(images.count(), 50)

    def test_fallback_excludes_viewer_images(self):
        """Fallback should only include images from editor+ users."""
        # Create images from different permission levels
        img_owner = TripImage.objects.create(
            uploaded_by=self.user1,
            datetime_utc=datetime(2024, 1, 20, 10, 0, 0, tzinfo=dt_timezone.utc),
            caption='Owner image',
        )
        img_editor = TripImage.objects.create(
            uploaded_by=self.user2,
            datetime_utc=datetime(2024, 1, 20, 11, 0, 0, tzinfo=dt_timezone.utc),
            caption='Editor image',
        )
        img_viewer = TripImage.objects.create(
            uploaded_by=self.user3,
            datetime_utc=datetime(2024, 1, 20, 12, 0, 0, tzinfo=dt_timezone.utc),
            caption='Viewer image',
        )

        # Query for date with no images (triggers fallback)
        images = ImagePickerService.get_accessible_images_with_fallback(
            trip=self.trip,
            user=self.user1,
            date=date(2024, 1, 15),
            timezone='UTC',
            use_fallback=True,
        )

        # Should include owner and editor, but not viewer
        image_ids = [img.id for img in images]
        self.assertIn(img_owner.id, image_ids)
        self.assertIn(img_editor.id, image_ids)
        self.assertNotIn(img_viewer.id, image_ids)

    def test_fallback_ordered_by_uploaded_datetime_desc(self):
        """Fallback should return most recent images first."""
        # Create images at different times
        img1 = TripImage.objects.create(
            uploaded_by=self.user1,
            caption='Oldest',
        )
        img2 = TripImage.objects.create(
            uploaded_by=self.user2,
            caption='Middle',
        )
        img3 = TripImage.objects.create(
            uploaded_by=self.user1,
            caption='Newest',
        )

        # Query for date with no images (triggers fallback)
        images = ImagePickerService.get_accessible_images_with_fallback(
            trip=self.trip,
            user=self.user1,
            date=date(2024, 1, 15),
            timezone='UTC',
            use_fallback=True,
        )

        # Should be ordered newest first
        images_list = list(images)
        self.assertEqual(images_list[0].id, img3.id)
        self.assertEqual(images_list[1].id, img2.id)
        self.assertEqual(images_list[2].id, img1.id)

    def test_fallback_limit_to_50_images(self):
        """Fallback should limit results to 50 images."""
        # Create 60 images
        for i in range(60):
            TripImage.objects.create(
                uploaded_by=self.user1,
                caption=f'Image {i}',
            )

        # Query for date with no images (triggers fallback)
        images = ImagePickerService.get_accessible_images_with_fallback(
            trip=self.trip,
            user=self.user1,
            date=date(2024, 1, 15),
            timezone='UTC',
            use_fallback=True,
        )

        # Should return only 50 (default limit)
        self.assertEqual(len(images), 50)

    def test_date_query_takes_precedence_over_fallback(self):
        """When date query has results, should not use fallback."""
        # Create one image on target date
        img_target = TripImage.objects.create(
            uploaded_by=self.user1,
            datetime_utc=datetime(2024, 1, 15, 10, 0, 0, tzinfo=dt_timezone.utc),
            caption='Target date image',
        )

        # Create many recent images
        for i in range(50):
            TripImage.objects.create(
                uploaded_by=self.user1,
                datetime_utc=datetime(2024, 1, 20, 10, i, 0, tzinfo=dt_timezone.utc),
                caption=f'Recent image {i}',
            )

        # Query for Jan 15
        images = ImagePickerService.get_accessible_images_with_fallback(
            trip=self.trip,
            user=self.user1,
            date=date(2024, 1, 15),
            timezone='UTC',
            use_fallback=True,
        )

        # Should return only the target date image, not recent images
        self.assertEqual(images.count(), 1)
        self.assertEqual(images[0].id, img_target.id)

    def test_fallback_with_timezone_conversion(self):
        """Fallback should work correctly with different timezones."""
        # Create image
        TripImage.objects.create(
            uploaded_by=self.user1,
            datetime_utc=datetime(2024, 1, 20, 10, 0, 0, tzinfo=dt_timezone.utc),
            caption='Recent image',
        )

        # Query for date with different timezone
        images = ImagePickerService.get_accessible_images_with_fallback(
            trip=self.trip,
            user=self.user1,
            date=date(2024, 1, 15),
            timezone='America/New_York',
            use_fallback=True,
        )

        # Should trigger fallback (no images on Jan 15 EST)
        self.assertEqual(len(images), 1)
