"""
Tests for TripImageHelpers utility methods.

Tests focus on:
- Recent images for trip editors (fallback for image picker)
- Permission-based filtering (OWNER, ADMIN, EDITOR only)
- Ordering by uploaded_datetime DESC
"""
import logging

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
