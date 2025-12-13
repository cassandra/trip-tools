"""
Tests for TripImageManager permission filtering and access control.

Tests focus on:
- Permission filtering by user (for_user)
- Trip-based access control (accessible_to_user_in_trip)
- Date range filtering for journal entries
- Multi-member permission scenarios
- Security boundaries (unauthenticated users, non-members)
- Edge cases (null datetimes, removed members)
"""
import logging

from datetime import datetime, timezone
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from tt.apps.images.models import TripImage
from tt.apps.trips.enums import TripPermissionLevel
from tt.apps.trips.tests.synthetic_data import TripSyntheticData

logging.disable(logging.CRITICAL)

User = get_user_model()


class TripImageManagerForUserTestCase(TestCase):
    """Test for_user filtering - images uploaded by user."""

    @classmethod
    def setUpTestData(cls):
        cls.user1 = User.objects.create_user(email='user1@test.com', password='pass')
        cls.user2 = User.objects.create_user(email='user2@test.com', password='pass')

    def test_for_user_returns_uploaded_images(self):
        """for_user should return images uploaded by the user."""
        # Create images uploaded by user1
        img1 = TripImage.objects.create(uploaded_by=self.user1, caption='Image 1')
        img2 = TripImage.objects.create(uploaded_by=self.user1, caption='Image 2')

        # Create image uploaded by user2
        TripImage.objects.create(uploaded_by=self.user2, caption='Image 3')

        # user1 should see only their images
        user1_images = TripImage.objects.for_user(self.user1)
        self.assertEqual(user1_images.count(), 2)
        self.assertIn(img1, user1_images)
        self.assertIn(img2, user1_images)

    def test_for_user_excludes_other_users_images(self):
        """for_user should not return images from other users."""
        # Create images for different users
        TripImage.objects.create(uploaded_by=self.user1, caption='User 1 Image')
        img2 = TripImage.objects.create(uploaded_by=self.user2, caption='User 2 Image')

        # user2 should only see their own image
        user2_images = TripImage.objects.for_user(self.user2)
        self.assertEqual(user2_images.count(), 1)
        self.assertIn(img2, user2_images)

    def test_for_user_empty_for_no_uploads(self):
        """for_user should return empty queryset for users with no uploads."""
        user3 = User.objects.create_user(email='user3@test.com', password='pass')

        # Create images for other users
        TripImage.objects.create(uploaded_by=self.user1, caption='Image')

        # user3 has no uploads
        user3_images = TripImage.objects.for_user(user3)
        self.assertEqual(user3_images.count(), 0)

    def test_for_user_multiple_images(self):
        """for_user should handle users with many images."""
        # Create many images for user1
        for i in range(50):
            TripImage.objects.create(uploaded_by=self.user1, caption=f'Image {i}')

        user1_images = TripImage.objects.for_user(self.user1)
        self.assertEqual(user1_images.count(), 50)


class TripImageManagerAccessibleToUserInTripTestCase(TestCase):
    """Test accessible_to_user_in_trip - trip member-based access."""

    @classmethod
    def setUpTestData(cls):
        cls.user1 = User.objects.create_user(email='user1@test.com', password='pass')
        cls.user2 = User.objects.create_user(email='user2@test.com', password='pass')
        cls.user3 = User.objects.create_user(email='user3@test.com', password='pass')

        cls.trip = TripSyntheticData.create_test_trip(user=cls.user1, title='Test Trip')

    def test_accessible_to_owner_includes_all_member_images(self):
        """Trip owner should see images from all trip members."""
        # Add user2 as member
        TripSyntheticData.add_trip_member(self.trip, self.user2, TripPermissionLevel.EDITOR, self.user1)

        # Create images from both users
        img1 = TripImage.objects.create(uploaded_by=self.user1, caption='Owner Image')
        img2 = TripImage.objects.create(uploaded_by=self.user2, caption='Member Image')

        # Owner should see both
        accessible = TripImage.objects.accessible_to_user_in_trip(self.user1, self.trip)
        self.assertEqual(accessible.count(), 2)
        self.assertIn(img1, accessible)
        self.assertIn(img2, accessible)

    def test_accessible_to_member_includes_all_member_images(self):
        """Trip member should see images from all other trip members."""
        # Add user2 and user3 as members
        TripSyntheticData.add_trip_member(self.trip, self.user2, TripPermissionLevel.EDITOR, self.user1)
        TripSyntheticData.add_trip_member(self.trip, self.user3, TripPermissionLevel.VIEWER, self.user1)

        # Create images from all members
        img1 = TripImage.objects.create(uploaded_by=self.user1, caption='Owner Image')
        img2 = TripImage.objects.create(uploaded_by=self.user2, caption='Editor Image')
        img3 = TripImage.objects.create(uploaded_by=self.user3, caption='Viewer Image')

        # user2 (EDITOR) should see all member images
        accessible = TripImage.objects.accessible_to_user_in_trip(self.user2, self.trip)
        self.assertEqual(accessible.count(), 3)
        self.assertIn(img1, accessible)
        self.assertIn(img2, accessible)
        self.assertIn(img3, accessible)

    def test_accessible_excludes_non_member_images(self):
        """Trip members should not see images from non-members."""
        # user3 is NOT a member
        non_member_img = TripImage.objects.create(uploaded_by=self.user3, caption='Non-member Image')
        member_img = TripImage.objects.create(uploaded_by=self.user1, caption='Member Image')

        # user1 (member) should not see user3's images
        accessible = TripImage.objects.accessible_to_user_in_trip(self.user1, self.trip)
        self.assertEqual(accessible.count(), 1)
        self.assertIn(member_img, accessible)
        self.assertNotIn(non_member_img, accessible)

    def test_accessible_unauthenticated_user_returns_none(self):
        """Unauthenticated user should see no images."""
        TripImage.objects.create(uploaded_by=self.user1, caption='Image')

        # Create mock unauthenticated user
        class MockAnonymousUser:
            is_authenticated = False

        anonymous = MockAnonymousUser()

        accessible = TripImage.objects.accessible_to_user_in_trip(anonymous, self.trip)
        self.assertEqual(accessible.count(), 0)

    def test_accessible_none_user_returns_none(self):
        """None user should return empty queryset."""
        TripImage.objects.create(uploaded_by=self.user1, caption='Image')

        accessible = TripImage.objects.accessible_to_user_in_trip(None, self.trip)
        self.assertEqual(accessible.count(), 0)

    def test_accessible_non_member_sees_member_images(self):
        """Non-member can see trip member images (current implementation - no permission check on requesting user)."""
        # Note: Current implementation doesn't check if requesting user is a trip member
        # It returns images from trip members to ANY authenticated user
        # This may be intentional for future sharing features

        TripImage.objects.create(uploaded_by=self.user1, caption='Trip Image')

        # user2 is not a member, but can still query trip member images
        accessible = TripImage.objects.accessible_to_user_in_trip(self.user2, self.trip)
        self.assertEqual(accessible.count(), 1)  # Current behavior: returns member images

    def test_accessible_all_permission_levels(self):
        """All permission levels should have same access to member images."""
        # Create trip with multiple permission levels
        trip2 = TripSyntheticData.create_test_trip(user=self.user1, title='Multi-Level Trip')
        TripSyntheticData.add_trip_member(trip2, self.user2, TripPermissionLevel.ADMIN, self.user1)
        TripSyntheticData.add_trip_member(trip2, self.user3, TripPermissionLevel.VIEWER, self.user1)

        # Create images
        img1 = TripImage.objects.create(uploaded_by=self.user1, caption='Owner Image')
        img2 = TripImage.objects.create(uploaded_by=self.user2, caption='Admin Image')
        img3 = TripImage.objects.create(uploaded_by=self.user3, caption='Viewer Image')

        # All members should see all images
        for user in [self.user1, self.user2, self.user3]:
            with self.subTest(user=user.email):
                accessible = TripImage.objects.accessible_to_user_in_trip(user, trip2)
                self.assertEqual(accessible.count(), 3)
                self.assertIn(img1, accessible)
                self.assertIn(img2, accessible)
                self.assertIn(img3, accessible)


class TripImageManagerDateRangeFilteringTestCase(TestCase):
    """Test accessible_to_user_in_trip_for_date_range - date filtering for journal entries."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(email='user@test.com', password='pass')
        cls.trip = TripSyntheticData.create_test_trip(user=cls.user, title='Test Trip')

    def test_date_range_includes_images_within_range(self):
        """Should return images within the date range."""
        # Create images with different timestamps
        start = datetime(2025, 1, 15, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 1, 16, 0, 0, 0, tzinfo=timezone.utc)

        # Images within range
        img1 = TripImage.objects.create(
            uploaded_by=self.user,
            datetime_utc=datetime(2025, 1, 15, 8, 0, 0, tzinfo=timezone.utc),
            caption='Morning',
        )
        img2 = TripImage.objects.create(
            uploaded_by=self.user,
            datetime_utc=datetime(2025, 1, 15, 20, 0, 0, tzinfo=timezone.utc),
            caption='Evening',
        )

        # Image outside range
        TripImage.objects.create(
            uploaded_by=self.user,
            datetime_utc=datetime(2025, 1, 17, 8, 0, 0, tzinfo=timezone.utc),
            caption='Next Day',
        )

        accessible = TripImage.objects.accessible_to_user_in_trip_for_date_range(
            self.user, self.trip, start, end
        )

        self.assertEqual(accessible.count(), 2)
        self.assertIn(img1, accessible)
        self.assertIn(img2, accessible)

    def test_date_range_excludes_before_start(self):
        """Should exclude images before start datetime."""
        start = datetime(2025, 1, 15, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 1, 16, 0, 0, 0, tzinfo=timezone.utc)

        # Image before start
        TripImage.objects.create(
            uploaded_by=self.user,
            datetime_utc=datetime(2025, 1, 14, 23, 59, 59, tzinfo=timezone.utc),
            caption='Before',
        )

        # Image after start
        img = TripImage.objects.create(
            uploaded_by=self.user,
            datetime_utc=datetime(2025, 1, 15, 0, 0, 0, tzinfo=timezone.utc),
            caption='At Start',
        )

        accessible = TripImage.objects.accessible_to_user_in_trip_for_date_range(
            self.user, self.trip, start, end
        )

        self.assertEqual(accessible.count(), 1)
        self.assertIn(img, accessible)

    def test_date_range_excludes_at_end_boundary(self):
        """Should exclude images at end boundary (range is [start, end))."""
        start = datetime(2025, 1, 15, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 1, 16, 0, 0, 0, tzinfo=timezone.utc)

        # Image exactly at end boundary
        TripImage.objects.create(
            uploaded_by=self.user,
            datetime_utc=datetime(2025, 1, 16, 0, 0, 0, tzinfo=timezone.utc),
            caption='At End',
        )

        # Image just before end
        img = TripImage.objects.create(
            uploaded_by=self.user,
            datetime_utc=datetime(2025, 1, 15, 23, 59, 59, tzinfo=timezone.utc),
            caption='Before End',
        )

        accessible = TripImage.objects.accessible_to_user_in_trip_for_date_range(
            self.user, self.trip, start, end
        )

        self.assertEqual(accessible.count(), 1)
        self.assertIn(img, accessible)

    def test_date_range_excludes_null_datetime(self):
        """Should exclude images with null datetime_utc."""
        start = datetime(2025, 1, 15, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 1, 16, 0, 0, 0, tzinfo=timezone.utc)

        # Image with null datetime
        TripImage.objects.create(
            uploaded_by=self.user,
            datetime_utc=None,
            caption='No DateTime',
        )

        # Image with valid datetime
        img = TripImage.objects.create(
            uploaded_by=self.user,
            datetime_utc=datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
            caption='With DateTime',
        )

        accessible = TripImage.objects.accessible_to_user_in_trip_for_date_range(
            self.user, self.trip, start, end
        )

        self.assertEqual(accessible.count(), 1)
        self.assertIn(img, accessible)

    def test_date_range_multi_member_filtering(self):
        """Date range filtering should work with multiple trip members."""
        user2 = User.objects.create_user(email='user2@test.com', password='pass')
        TripSyntheticData.add_trip_member(self.trip, user2, TripPermissionLevel.EDITOR, self.user)

        start = datetime(2025, 1, 15, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 1, 16, 0, 0, 0, tzinfo=timezone.utc)

        # Images from both members within range
        img1 = TripImage.objects.create(
            uploaded_by=self.user,
            datetime_utc=datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
            caption='User1 Image',
        )
        img2 = TripImage.objects.create(
            uploaded_by=user2,
            datetime_utc=datetime(2025, 1, 15, 14, 0, 0, tzinfo=timezone.utc),
            caption='User2 Image',
        )

        # Both members should see both images
        accessible_user1 = TripImage.objects.accessible_to_user_in_trip_for_date_range(
            self.user, self.trip, start, end
        )
        accessible_user2 = TripImage.objects.accessible_to_user_in_trip_for_date_range(
            user2, self.trip, start, end
        )

        self.assertEqual(accessible_user1.count(), 2)
        self.assertEqual(accessible_user2.count(), 2)
        self.assertIn(img1, accessible_user1)
        self.assertIn(img2, accessible_user1)

    def test_date_range_select_related_optimization(self):
        """Date range query should use select_related for uploaded_by."""
        start = datetime(2025, 1, 15, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 1, 16, 0, 0, 0, tzinfo=timezone.utc)

        TripImage.objects.create(
            uploaded_by=self.user,
            datetime_utc=datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
            caption='Image',
        )

        accessible = TripImage.objects.accessible_to_user_in_trip_for_date_range(
            self.user, self.trip, start, end
        )

        # Evaluate the queryset first to fetch all data
        images_list = list(accessible)

        # Now access uploaded_by without triggering additional query
        # (select_related should have prefetched it during evaluation)
        with self.assertNumQueries(0):
            for img in images_list:
                _ = img.uploaded_by.email  # Should not trigger query

    def test_date_range_timezone_aware_boundaries(self):
        """Date range filtering should work with timezone-aware datetimes."""
        # New York timezone boundaries (EST = UTC-5)
        start = datetime(2025, 1, 15, 5, 0, 0, tzinfo=timezone.utc)  # Midnight EST
        end = datetime(2025, 1, 16, 5, 0, 0, tzinfo=timezone.utc)  # Next midnight EST

        # Image at midnight EST (05:00 UTC)
        img1 = TripImage.objects.create(
            uploaded_by=self.user,
            datetime_utc=start,
            caption='Midnight EST',
        )

        # Image at 11:59 PM EST (04:59 UTC next day)
        img2 = TripImage.objects.create(
            uploaded_by=self.user,
            datetime_utc=datetime(2025, 1, 16, 4, 59, 0, tzinfo=timezone.utc),
            caption='11:59 PM EST',
        )

        # Image at midnight next day (should be excluded)
        TripImage.objects.create(
            uploaded_by=self.user,
            datetime_utc=end,
            caption='Next Day',
        )

        accessible = TripImage.objects.accessible_to_user_in_trip_for_date_range(
            self.user, self.trip, start, end
        )

        self.assertEqual(accessible.count(), 2)
        self.assertIn(img1, accessible)
        self.assertIn(img2, accessible)


class TripImageManagerForTripTestCase(TestCase):
    """Test for_trip filtering - all images from trip members."""

    @classmethod
    def setUpTestData(cls):
        cls.user1 = User.objects.create_user(email='user1@test.com', password='pass')
        cls.user2 = User.objects.create_user(email='user2@test.com', password='pass')
        cls.user3 = User.objects.create_user(email='user3@test.com', password='pass')

        cls.trip = TripSyntheticData.create_test_trip(user=cls.user1, title='Test Trip')

    def test_for_trip_returns_all_member_images(self):
        """for_trip should return images from all trip members."""
        # Add user2 as member
        TripSyntheticData.add_trip_member(self.trip, self.user2, TripPermissionLevel.EDITOR, self.user1)

        # Create images from members
        img1 = TripImage.objects.create(uploaded_by=self.user1, caption='Owner Image')
        img2 = TripImage.objects.create(uploaded_by=self.user2, caption='Member Image')

        # Create image from non-member
        TripImage.objects.create(uploaded_by=self.user3, caption='Non-member Image')

        trip_images = TripImage.objects.for_trip(self.trip)

        self.assertEqual(trip_images.count(), 2)
        self.assertIn(img1, trip_images)
        self.assertIn(img2, trip_images)

    def test_for_trip_excludes_non_members(self):
        """for_trip should exclude images from non-members."""
        # Only user1 is a member (trip owner)
        member_img = TripImage.objects.create(uploaded_by=self.user1, caption='Member Image')
        non_member_img = TripImage.objects.create(uploaded_by=self.user2, caption='Non-member Image')

        trip_images = TripImage.objects.for_trip(self.trip)

        self.assertEqual(trip_images.count(), 1)
        self.assertIn(member_img, trip_images)
        self.assertNotIn(non_member_img, trip_images)

    def test_for_trip_no_permission_check(self):
        """for_trip doesn't check permissions, just returns member images."""
        # This is a documentation test - for_trip returns images without permission filtering
        # For permission-aware queries, use accessible_to_user_in_trip()

        TripSyntheticData.add_trip_member(self.trip, self.user2, TripPermissionLevel.VIEWER, self.user1)

        img = TripImage.objects.create(uploaded_by=self.user2, caption='Viewer Image')

        trip_images = TripImage.objects.for_trip(self.trip)

        # Image is returned regardless of permission level
        self.assertIn(img, trip_images)


class TripImageManagerEdgeCasesTestCase(TestCase):
    """Test edge cases and boundary conditions."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(email='user@test.com', password='pass')
        cls.trip = TripSyntheticData.create_test_trip(user=cls.user, title='Test Trip')

    def test_accessible_empty_trip(self):
        """accessible_to_user_in_trip should work with trip that has no images."""
        accessible = TripImage.objects.accessible_to_user_in_trip(self.user, self.trip)
        self.assertEqual(accessible.count(), 0)

    def test_date_range_empty_results(self):
        """Date range filtering should return empty queryset when no images match."""
        # Create image outside range
        TripImage.objects.create(
            uploaded_by=self.user,
            datetime_utc=datetime(2025, 1, 20, 12, 0, 0, tzinfo=timezone.utc),
            caption='Outside Range',
        )

        start = datetime(2025, 1, 15, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 1, 16, 0, 0, 0, tzinfo=timezone.utc)

        accessible = TripImage.objects.accessible_to_user_in_trip_for_date_range(
            self.user, self.trip, start, end
        )

        self.assertEqual(accessible.count(), 0)

    def test_date_range_with_gps_coordinates(self):
        """Date range filtering should work with images that have GPS coordinates."""
        start = datetime(2025, 1, 15, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 1, 16, 0, 0, 0, tzinfo=timezone.utc)

        img = TripImage.objects.create(
            uploaded_by=self.user,
            datetime_utc=datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
            latitude=Decimal('48.208176'),
            longitude=Decimal('16.373819'),
            caption='Vienna',
        )

        accessible = TripImage.objects.accessible_to_user_in_trip_for_date_range(
            self.user, self.trip, start, end
        )

        self.assertEqual(accessible.count(), 1)
        self.assertIn(img, accessible)

    def test_accessible_multiple_trips_isolation(self):
        """accessible_to_user_in_trip should isolate images by trip."""
        user2 = User.objects.create_user(email='user2@test.com', password='pass')
        trip2 = TripSyntheticData.create_test_trip(user=user2, title='Other Trip')

        # Add user to both trips
        TripSyntheticData.add_trip_member(trip2, self.user, TripPermissionLevel.EDITOR, user2)

        # Create images for different trips
        img_trip1 = TripImage.objects.create(uploaded_by=self.user, caption='Trip 1 Image')
        img_trip2 = TripImage.objects.create(uploaded_by=user2, caption='Trip 2 Image')

        # User should see different images for different trips
        accessible_trip1 = TripImage.objects.accessible_to_user_in_trip(self.user, self.trip)
        accessible_trip2 = TripImage.objects.accessible_to_user_in_trip(self.user, trip2)

        # Trip 1: only img_trip1 (uploaded by user who is member)
        self.assertIn(img_trip1, accessible_trip1)
        self.assertNotIn(img_trip2, accessible_trip1)

        # Trip 2: both images (both uploaders are members)
        self.assertIn(img_trip1, accessible_trip2)
        self.assertIn(img_trip2, accessible_trip2)
