"""
Tests for TripImage model.

Tests business logic, permissions, and model methods.
"""
from datetime import datetime
import logging
import pytz
import tempfile

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from tt.apps.images.models import TripImage
from tt.apps.members.models import TripMember
from tt.apps.trips.models import Trip
from tt.apps.trips.enums import TripPermissionLevel, TripStatus

User = get_user_model()
logging.disable(logging.CRITICAL)


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


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class TripImageTripPermissionTestCase(TestCase):
    """Test TripImage trip-context permissions."""

    def setUp(self):

        # Create users
        self.alice = User.objects.create_user(
            email='alice@example.com',
            password='password',
        )
        self.bob = User.objects.create_user(
            email='bob@example.com',
            password='password',
        )
        self.charlie = User.objects.create_user(
            email='charlie@example.com',
            password='password',
        )

        # Create trip with Alice and Bob as members
        self.trip = Trip.objects.create(
            title='Test Trip',
            trip_status=TripStatus.CURRENT,
        )
        TripMember.objects.create(
            trip=self.trip,
            user=self.alice,
            permission_level=TripPermissionLevel.OWNER,
        )
        TripMember.objects.create(
            trip=self.trip,
            user=self.bob,
            permission_level=TripPermissionLevel.EDITOR,
        )

        # Create image uploaded by Alice
        self.alice_image = TripImage.objects.create(
            uploaded_by=self.alice,
            caption='Alice image',
        )

        # Create image uploaded by Charlie (not a trip member)
        self.charlie_image = TripImage.objects.create(
            uploaded_by=self.charlie,
            caption='Charlie image',
        )


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class TripImageManagerTripContextTestCase(TestCase):
    """Test TripImageManager trip-context methods."""

    def setUp(self):

        # Create users
        self.alice = User.objects.create_user(
            email='alice@example.com',
            password='password',
        )
        self.bob = User.objects.create_user(
            email='bob@example.com',
            password='password',
        )
        self.charlie = User.objects.create_user(
            email='charlie@example.com',
            password='password',
        )

        # Create trip with Alice and Bob
        self.trip = Trip.objects.create(
            title='Test Trip',
            trip_status=TripStatus.CURRENT,
        )
        TripMember.objects.create(
            trip=self.trip,
            user=self.alice,
            permission_level=TripPermissionLevel.OWNER,
        )
        TripMember.objects.create(
            trip=self.trip,
            user=self.bob,
            permission_level=TripPermissionLevel.EDITOR,
        )

        # Create images with dates
        self.alice_jan15 = TripImage.objects.create(
            uploaded_by=self.alice,
            datetime_utc=datetime(2025, 1, 15, 14, 0, tzinfo=pytz.UTC),
            caption='Alice Jan 15',
        )
        self.bob_jan15 = TripImage.objects.create(
            uploaded_by=self.bob,
            datetime_utc=datetime(2025, 1, 15, 16, 0, tzinfo=pytz.UTC),
            caption='Bob Jan 15',
        )
        self.alice_jan16 = TripImage.objects.create(
            uploaded_by=self.alice,
            datetime_utc=datetime(2025, 1, 16, 10, 0, tzinfo=pytz.UTC),
            caption='Alice Jan 16',
        )
        self.charlie_jan15 = TripImage.objects.create(
            uploaded_by=self.charlie,
            datetime_utc=datetime(2025, 1, 15, 12, 0, tzinfo=pytz.UTC),
            caption='Charlie Jan 15 (not in trip)',
        )

    def test_accessible_to_user_in_trip(self):
        """Returns images from all current trip members."""
        images = TripImage.objects.accessible_to_user_in_trip(
            self.alice, self.trip
        )

        # Should include Alice and Bob's images
        self.assertEqual(3, images.count())
        self.assertIn(self.alice_jan15, images)
        self.assertIn(self.bob_jan15, images)
        self.assertIn(self.alice_jan16, images)

        # Should not include Charlie's image
        self.assertNotIn(self.charlie_jan15, images)

    def test_accessible_to_user_in_trip_for_date_range(self):
        """Filters images by date range boundaries."""
        from datetime import datetime
        import pytz

        # Jan 15 boundaries in UTC
        start = datetime(2025, 1, 15, 0, 0, tzinfo=pytz.UTC)
        end = datetime(2025, 1, 16, 0, 0, tzinfo=pytz.UTC)

        images = TripImage.objects.accessible_to_user_in_trip_for_date_range(
            user=self.alice,
            trip=self.trip,
            start_datetime=start,
            end_datetime=end
        )

        # Should include Jan 15 images from Alice and Bob
        self.assertEqual(2, images.count())
        self.assertIn(self.alice_jan15, images)
        self.assertIn(self.bob_jan15, images)

        # Should not include Jan 16 or non-member images
        self.assertNotIn(self.alice_jan16, images)
        self.assertNotIn(self.charlie_jan15, images)

    def test_for_trip_pattern(self):
        """for_trip() follows codebase pattern."""
        images = TripImage.objects.for_trip(self.trip)

        # Should include all trip member images
        self.assertEqual(3, images.count())
        self.assertIn(self.alice_jan15, images)
        self.assertIn(self.bob_jan15, images)
        self.assertIn(self.alice_jan16, images)
