from django.contrib.auth import get_user_model
from django.test import TestCase

from tt.apps.trips.enums import TripPermissionLevel
from tt.apps.trips.mixins import TripPermissionMixin
from tt.apps.trips.models import TripMember
from tt.apps.trips.tests.synthetic_data import TripSyntheticData

User = get_user_model()


class TripPermissionMixinTests(TestCase):
    """Tests for TripPermissionMixin permission hierarchy logic."""

    def setUp(self):
        self.owner = User.objects.create_user(email='owner@test.com', password='pass')
        self.admin = User.objects.create_user(email='admin@test.com', password='pass')
        self.editor = User.objects.create_user(email='editor@test.com', password='pass')
        self.viewer = User.objects.create_user(email='viewer@test.com', password='pass')
        self.non_member = User.objects.create_user(email='outsider@test.com', password='pass')

        self.trip = TripSyntheticData.create_test_trip(user=self.owner, title='Test Trip')

        # Add other members with different permission levels
        TripMember.objects.create(
            trip=self.trip,
            user=self.admin,
            permission_level=TripPermissionLevel.ADMIN,
            added_by=self.owner
        )
        TripMember.objects.create(
            trip=self.trip,
            user=self.editor,
            permission_level=TripPermissionLevel.EDITOR,
            added_by=self.owner
        )
        TripMember.objects.create(
            trip=self.trip,
            user=self.viewer,
            permission_level=TripPermissionLevel.VIEWER,
            added_by=self.owner
        )

        # Create mixin instance for testing
        self.mixin = TripPermissionMixin()

    def test_owner_has_owner_permission(self):
        """Owner passes permission check for OWNER level."""
        self.assertTrue(
            self.mixin.has_trip_permission(
                self.owner,
                self.trip,
                TripPermissionLevel.OWNER
            )
        )

    def test_owner_has_admin_permission(self):
        """Owner passes permission check for ADMIN level (hierarchy)."""
        self.assertTrue(
            self.mixin.has_trip_permission(
                self.owner,
                self.trip,
                TripPermissionLevel.ADMIN
            )
        )

    def test_owner_has_editor_permission(self):
        """Owner passes permission check for EDITOR level (hierarchy)."""
        self.assertTrue(
            self.mixin.has_trip_permission(
                self.owner,
                self.trip,
                TripPermissionLevel.EDITOR
            )
        )

    def test_owner_has_viewer_permission(self):
        """Owner passes permission check for VIEWER level (hierarchy)."""
        self.assertTrue(
            self.mixin.has_trip_permission(
                self.owner,
                self.trip,
                TripPermissionLevel.VIEWER
            )
        )

    def test_admin_has_admin_permission(self):
        """Admin passes permission check for ADMIN level."""
        self.assertTrue(
            self.mixin.has_trip_permission(
                self.admin,
                self.trip,
                TripPermissionLevel.ADMIN
            )
        )

    def test_admin_has_editor_permission(self):
        """Admin passes permission check for EDITOR level (hierarchy)."""
        self.assertTrue(
            self.mixin.has_trip_permission(
                self.admin,
                self.trip,
                TripPermissionLevel.EDITOR
            )
        )

    def test_admin_has_viewer_permission(self):
        """Admin passes permission check for VIEWER level (hierarchy)."""
        self.assertTrue(
            self.mixin.has_trip_permission(
                self.admin,
                self.trip,
                TripPermissionLevel.VIEWER
            )
        )

    def test_admin_fails_owner_permission(self):
        """Admin fails permission check for OWNER level."""
        self.assertFalse(
            self.mixin.has_trip_permission(
                self.admin,
                self.trip,
                TripPermissionLevel.OWNER
            )
        )

    def test_editor_has_editor_permission(self):
        """Editor passes permission check for EDITOR level."""
        self.assertTrue(
            self.mixin.has_trip_permission(
                self.editor,
                self.trip,
                TripPermissionLevel.EDITOR
            )
        )

    def test_editor_has_viewer_permission(self):
        """Editor passes permission check for VIEWER level (hierarchy)."""
        self.assertTrue(
            self.mixin.has_trip_permission(
                self.editor,
                self.trip,
                TripPermissionLevel.VIEWER
            )
        )

    def test_editor_fails_admin_permission(self):
        """Editor fails permission check for ADMIN level."""
        self.assertFalse(
            self.mixin.has_trip_permission(
                self.editor,
                self.trip,
                TripPermissionLevel.ADMIN
            )
        )

    def test_editor_fails_owner_permission(self):
        """Editor fails permission check for OWNER level."""
        self.assertFalse(
            self.mixin.has_trip_permission(
                self.editor,
                self.trip,
                TripPermissionLevel.OWNER
            )
        )

    def test_viewer_has_viewer_permission(self):
        """Viewer passes permission check for VIEWER level."""
        self.assertTrue(
            self.mixin.has_trip_permission(
                self.viewer,
                self.trip,
                TripPermissionLevel.VIEWER
            )
        )

    def test_viewer_fails_editor_permission(self):
        """Viewer fails permission check for EDITOR level."""
        self.assertFalse(
            self.mixin.has_trip_permission(
                self.viewer,
                self.trip,
                TripPermissionLevel.EDITOR
            )
        )

    def test_viewer_fails_admin_permission(self):
        """Viewer fails permission check for ADMIN level."""
        self.assertFalse(
            self.mixin.has_trip_permission(
                self.viewer,
                self.trip,
                TripPermissionLevel.ADMIN
            )
        )

    def test_viewer_fails_owner_permission(self):
        """Viewer fails permission check for OWNER level."""
        self.assertFalse(
            self.mixin.has_trip_permission(
                self.viewer,
                self.trip,
                TripPermissionLevel.OWNER
            )
        )

    def test_non_member_fails_all_permissions(self):
        """Non-member fails all permission checks (default deny)."""
        for level in [
            TripPermissionLevel.VIEWER,
            TripPermissionLevel.EDITOR,
            TripPermissionLevel.ADMIN,
            TripPermissionLevel.OWNER
        ]:
            with self.subTest(level=level):
                self.assertFalse(
                    self.mixin.has_trip_permission(
                        self.non_member,
                        self.trip,
                        level
                    )
                )

    def test_permission_hierarchy_values(self):
        """PERMISSION_HIERARCHY has correct numeric ordering."""
        hierarchy = TripPermissionMixin.PERMISSION_HIERARCHY

        self.assertEqual(hierarchy[TripPermissionLevel.OWNER], 4)
        self.assertEqual(hierarchy[TripPermissionLevel.ADMIN], 3)
        self.assertEqual(hierarchy[TripPermissionLevel.EDITOR], 2)
        self.assertEqual(hierarchy[TripPermissionLevel.VIEWER], 1)

        # Verify ordering
        self.assertGreater(
            hierarchy[TripPermissionLevel.OWNER],
            hierarchy[TripPermissionLevel.ADMIN]
        )
        self.assertGreater(
            hierarchy[TripPermissionLevel.ADMIN],
            hierarchy[TripPermissionLevel.EDITOR]
        )
        self.assertGreater(
            hierarchy[TripPermissionLevel.EDITOR],
            hierarchy[TripPermissionLevel.VIEWER]
        )
