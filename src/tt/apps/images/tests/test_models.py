"""
Tests for TripImage model.

Tests business logic, permissions, and model methods.
"""
import logging
import tempfile

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from tt.apps.images.models import TripImage

User = get_user_model()
logging.disable(logging.CRITICAL)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class TripImagePermissionTestCase(TestCase):
    """Test TripImage permission methods."""

    def setUp(self):
        self.owner = User.objects.create_user(
            email='owner@example.com',
            password='password',
        )
        self.other_user = User.objects.create_user(
            email='other@example.com',
            password='password',
        )
        self.trip_image = TripImage.objects.create(
            uploaded_by=self.owner,
            caption='Test image',
        )

    def test_owner_can_access(self):
        """Image owner should have access."""
        self.assertTrue(self.trip_image.user_can_access(self.owner))

    def test_other_user_cannot_access(self):
        """Non-owner user should not have access."""
        self.assertFalse(self.trip_image.user_can_access(self.other_user))

    def test_unauthenticated_user_cannot_access(self):
        """Unauthenticated user should not have access."""
        from django.contrib.auth.models import AnonymousUser
        anonymous = AnonymousUser()
        self.assertFalse(self.trip_image.user_can_access(anonymous))

    def test_none_user_cannot_access(self):
        """None user should not have access."""
        self.assertFalse(self.trip_image.user_can_access(None))


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class TripImageManagerTestCase(TestCase):
    """Test TripImage manager methods."""

    def setUp(self):
        self.user1 = User.objects.create_user(
            email='user1@example.com',
            password='password',
        )
        self.user2 = User.objects.create_user(
            email='user2@example.com',
            password='password',
        )

        # Create images for each user
        self.image1 = TripImage.objects.create(
            uploaded_by=self.user1,
            caption='User 1 image',
        )
        self.image2 = TripImage.objects.create(
            uploaded_by=self.user2,
            caption='User 2 image',
        )

    def test_for_user_returns_only_user_images(self):
        """for_user() should return only images uploaded by that user."""
        user1_images = TripImage.objects.for_user(self.user1)

        self.assertEqual(1, user1_images.count())
        self.assertEqual(self.image1, user1_images.first())

    def test_for_user_excludes_other_users(self):
        """for_user() should not return images from other users."""
        user1_images = TripImage.objects.for_user(self.user1)

        self.assertNotIn(self.image2, user1_images)
