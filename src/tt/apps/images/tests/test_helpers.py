"""
Tests for TripImageHelpers utility methods.

Tests focus on:
- Recent images for trip editors (fallback for image picker)
- Permission-based filtering (OWNER, ADMIN, EDITOR only)
- Upload session grouping and chronological ordering within groups
"""
import logging
import uuid
from datetime import datetime, timezone

from django.contrib.auth import get_user_model
from django.test import TestCase

from tt.apps.images.helpers import TripImageHelpers
from tt.apps.images.models import TripImage
from tt.apps.trips.enums import TripPermissionLevel
from tt.apps.trips.tests.synthetic_data import TripSyntheticData

logging.disable(logging.CRITICAL)

User = get_user_model()


class TripImageHelpersRecentImagesTestCase(TestCase):
    """Test get_recent_images_for_trip_editors - fallback for image picker."""

    def setUp(self):
        self.user1 = User.objects.create_user(email='owner@test.com', password='pass')
        self.user2 = User.objects.create_user(email='editor@test.com', password='pass')
        self.user3 = User.objects.create_user(email='admin@test.com', password='pass')
        self.user4 = User.objects.create_user(email='viewer@test.com', password='pass')

        self.trip = TripSyntheticData.create_test_trip(user=self.user1, title='Test Trip')

    def test_recent_images_includes_owner_images(self):
        """Should include images from trip owner."""
        img1 = TripImage.objects.create(uploaded_by=self.user1, caption='Owner Image')

        recent = TripImageHelpers.get_recent_images_for_trip_editors(self.trip)

        self.assertEqual(len(recent), 1)
        self.assertIn(img1, recent)

    def test_recent_images_includes_editor_images(self):
        """Should include images from EDITOR members."""
        TripSyntheticData.add_trip_member(self.trip, self.user2, TripPermissionLevel.EDITOR, self.user1)

        img1 = TripImage.objects.create(uploaded_by=self.user1, caption='Owner Image')
        img2 = TripImage.objects.create(uploaded_by=self.user2, caption='Editor Image')

        recent = TripImageHelpers.get_recent_images_for_trip_editors(self.trip)

        self.assertEqual(len(recent), 2)
        self.assertIn(img1, recent)
        self.assertIn(img2, recent)

    def test_recent_images_includes_admin_images(self):
        """Should include images from ADMIN members."""
        TripSyntheticData.add_trip_member(self.trip, self.user3, TripPermissionLevel.ADMIN, self.user1)

        img1 = TripImage.objects.create(uploaded_by=self.user1, caption='Owner Image')
        img3 = TripImage.objects.create(uploaded_by=self.user3, caption='Admin Image')

        recent = TripImageHelpers.get_recent_images_for_trip_editors(self.trip)

        self.assertEqual(len(recent), 2)
        self.assertIn(img1, recent)
        self.assertIn(img3, recent)

    def test_recent_images_excludes_viewer_images(self):
        """Should exclude images from VIEWER members."""
        TripSyntheticData.add_trip_member(self.trip, self.user4, TripPermissionLevel.VIEWER, self.user1)

        img1 = TripImage.objects.create(uploaded_by=self.user1, caption='Owner Image')
        img4 = TripImage.objects.create(uploaded_by=self.user4, caption='Viewer Image')

        recent = TripImageHelpers.get_recent_images_for_trip_editors(self.trip)

        # Should only include owner image, not viewer image
        self.assertEqual(len(recent), 1)
        self.assertIn(img1, recent)
        self.assertNotIn(img4, recent)

    def test_recent_images_ordered_by_uploaded_datetime_desc(self):
        """Should order images by uploaded_datetime DESC (most recent first)."""
        TripSyntheticData.add_trip_member(self.trip, self.user2, TripPermissionLevel.EDITOR, self.user1)

        # Create images with different upload times
        # Note: uploaded_datetime is auto-set, so we create in chronological order
        img1 = TripImage.objects.create(uploaded_by=self.user1, caption='Oldest')
        img2 = TripImage.objects.create(uploaded_by=self.user2, caption='Middle')
        img3 = TripImage.objects.create(uploaded_by=self.user1, caption='Newest')

        recent = TripImageHelpers.get_recent_images_for_trip_editors(self.trip)

        # Should be in reverse chronological order
        self.assertEqual(len(recent), 3)
        self.assertEqual(recent[0].id, img3.id)  # Newest first
        self.assertEqual(recent[1].id, img2.id)
        self.assertEqual(recent[2].id, img1.id)  # Oldest last

    def test_recent_images_respects_limit_parameter(self):
        """Should respect limit parameter."""
        # Create more images than limit
        for i in range(10):
            TripImage.objects.create(uploaded_by=self.user1, caption=f'Image {i}')

        recent = TripImageHelpers.get_recent_images_for_trip_editors(self.trip, limit=5)

        self.assertEqual(len(recent), 5)

    def test_recent_images_default_limit_50(self):
        """Should use default limit of 50 when not specified."""
        # Create 60 images
        for i in range(60):
            TripImage.objects.create(uploaded_by=self.user1, caption=f'Image {i}')

        recent = TripImageHelpers.get_recent_images_for_trip_editors(self.trip)

        # Should return only 50 (default limit)
        self.assertEqual(len(recent), 50)

    def test_recent_images_empty_trip(self):
        """Should return empty list for trip with no editor images."""
        # Add only a viewer
        TripSyntheticData.add_trip_member(self.trip, self.user4, TripPermissionLevel.VIEWER, self.user1)

        # Create image from viewer
        TripImage.objects.create(uploaded_by=self.user4, caption='Viewer Image')

        recent = TripImageHelpers.get_recent_images_for_trip_editors(self.trip)

        # Should be empty since viewers are excluded
        self.assertEqual(len(recent), 0)

    def test_recent_images_trip_with_no_images(self):
        """Should return empty list when editors have no images."""
        TripSyntheticData.add_trip_member(self.trip, self.user2, TripPermissionLevel.EDITOR, self.user1)

        recent = TripImageHelpers.get_recent_images_for_trip_editors(self.trip)

        self.assertEqual(len(recent), 0)

    def test_recent_images_mixed_permission_levels(self):
        """Should only include images from editor+ levels."""
        # Add members with different permission levels
        TripSyntheticData.add_trip_member(self.trip, self.user2, TripPermissionLevel.EDITOR, self.user1)
        TripSyntheticData.add_trip_member(self.trip, self.user3, TripPermissionLevel.ADMIN, self.user1)
        TripSyntheticData.add_trip_member(self.trip, self.user4, TripPermissionLevel.VIEWER, self.user1)

        # Create images from all members
        img1 = TripImage.objects.create(uploaded_by=self.user1, caption='Owner')
        img2 = TripImage.objects.create(uploaded_by=self.user2, caption='Editor')
        img3 = TripImage.objects.create(uploaded_by=self.user3, caption='Admin')
        img4 = TripImage.objects.create(uploaded_by=self.user4, caption='Viewer')

        recent = TripImageHelpers.get_recent_images_for_trip_editors(self.trip)

        # Should include owner, editor, admin but NOT viewer
        self.assertEqual(len(recent), 3)
        self.assertIn(img1, recent)
        self.assertIn(img2, recent)
        self.assertIn(img3, recent)
        self.assertNotIn(img4, recent)

    def test_recent_images_excludes_non_members(self):
        """Should exclude images from users who are not trip members."""
        non_member = User.objects.create_user(email='nonmember@test.com', password='pass')

        img1 = TripImage.objects.create(uploaded_by=self.user1, caption='Member Image')
        img2 = TripImage.objects.create(uploaded_by=non_member, caption='Non-member Image')

        recent = TripImageHelpers.get_recent_images_for_trip_editors(self.trip)

        self.assertEqual(len(recent), 1)
        self.assertIn(img1, recent)
        self.assertNotIn(img2, recent)

    def test_bulk_upload_images_grouped_and_sorted_by_datetime_utc(self):
        """Images from same bulk upload should be grouped and sorted by datetime_utc."""
        session_uuid = uuid.uuid4()

        # Create 3 images with same upload_session_uuid but different photo times
        img1 = TripImage.objects.create(
            uploaded_by=self.user1,
            upload_session_uuid=session_uuid,
            datetime_utc=datetime(2024, 6, 15, 10, 0, tzinfo=timezone.utc),
            caption='Bulk 10am',
        )
        img2 = TripImage.objects.create(
            uploaded_by=self.user1,
            upload_session_uuid=session_uuid,
            datetime_utc=datetime(2024, 6, 15, 9, 0, tzinfo=timezone.utc),
            caption='Bulk 9am',
        )
        img3 = TripImage.objects.create(
            uploaded_by=self.user1,
            upload_session_uuid=session_uuid,
            datetime_utc=datetime(2024, 6, 15, 11, 0, tzinfo=timezone.utc),
            caption='Bulk 11am',
        )

        recent = TripImageHelpers.get_recent_images_for_trip_editors(self.trip)

        self.assertEqual(len(recent), 3)
        # Should be ordered by datetime_utc ASC within group
        self.assertEqual(recent[0].id, img2.id)  # 9:00 AM
        self.assertEqual(recent[1].id, img1.id)  # 10:00 AM
        self.assertEqual(recent[2].id, img3.id)  # 11:00 AM

    def test_multiple_bulk_uploads_ordered_by_most_recent_first(self):
        """Multiple bulk upload groups should be ordered by most recent upload first."""
        # Older bulk upload session
        old_session = uuid.uuid4()
        old_img1 = TripImage.objects.create(
            uploaded_by=self.user1,
            upload_session_uuid=old_session,
            datetime_utc=datetime(2024, 6, 10, 10, 0, tzinfo=timezone.utc),
            caption='Old bulk 10am',
        )
        old_img2 = TripImage.objects.create(
            uploaded_by=self.user1,
            upload_session_uuid=old_session,
            datetime_utc=datetime(2024, 6, 10, 9, 0, tzinfo=timezone.utc),
            caption='Old bulk 9am',
        )

        # Newer bulk upload session
        new_session = uuid.uuid4()
        new_img1 = TripImage.objects.create(
            uploaded_by=self.user1,
            upload_session_uuid=new_session,
            datetime_utc=datetime(2024, 6, 15, 10, 0, tzinfo=timezone.utc),
            caption='New bulk 10am',
        )
        new_img2 = TripImage.objects.create(
            uploaded_by=self.user1,
            upload_session_uuid=new_session,
            datetime_utc=datetime(2024, 6, 15, 9, 0, tzinfo=timezone.utc),
            caption='New bulk 9am',
        )

        recent = TripImageHelpers.get_recent_images_for_trip_editors(self.trip)

        self.assertEqual(len(recent), 4)
        # Newer group first, then older group
        self.assertEqual(recent[0].id, new_img2.id)  # New group, 9:00 AM
        self.assertEqual(recent[1].id, new_img1.id)  # New group, 10:00 AM
        self.assertEqual(recent[2].id, old_img2.id)  # Old group, 9:00 AM
        self.assertEqual(recent[3].id, old_img1.id)  # Old group, 10:00 AM

    def test_images_without_datetime_utc_sorted_last_in_group(self):
        """Images with NULL datetime_utc should be sorted last within their group."""
        session_uuid = uuid.uuid4()

        img_with_time = TripImage.objects.create(
            uploaded_by=self.user1,
            upload_session_uuid=session_uuid,
            datetime_utc=datetime(2024, 6, 15, 10, 0, tzinfo=timezone.utc),
            caption='With time',
        )
        img_no_time = TripImage.objects.create(
            uploaded_by=self.user1,
            upload_session_uuid=session_uuid,
            datetime_utc=None,
            caption='No time',
        )

        recent = TripImageHelpers.get_recent_images_for_trip_editors(self.trip)

        self.assertEqual(len(recent), 2)
        self.assertEqual(recent[0].id, img_with_time.id)
        self.assertEqual(recent[1].id, img_no_time.id)
