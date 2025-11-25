import logging

from django.contrib.auth import get_user_model
from django.test import TestCase

from tt.apps.members.models import TripMember
from tt.apps.trips.enums import TripPermissionLevel
from tt.apps.trips.tests.synthetic_data import TripSyntheticData

logging.disable(logging.CRITICAL)

User = get_user_model()


class TripMemberModelTests(TestCase):
    """Tests for TripMember model constraints and behavior."""

    def test_cascade_delete_trip_removes_members(self):
        """Deleting trip deletes all TripMembers."""
        user = User.objects.create_user(email='test@test.com', password='pass')
        trip = TripSyntheticData.create_test_trip(user=user, title='Test Trip')

        trip_id = trip.pk
        self.assertEqual(TripMember.objects.filter(trip_id=trip_id).count(), 1)

        trip.delete()

        self.assertEqual(TripMember.objects.filter(trip_id=trip_id).count(), 0)

    def test_cascade_delete_user_removes_memberships(self):
        """Deleting user deletes all TripMembers for that user."""
        user = User.objects.create_user(email='test@test.com', password='pass')
        TripSyntheticData.create_test_trip(user=user, title='Test Trip')

        user_id = user.pk
        self.assertEqual(TripMember.objects.filter(user_id=user_id).count(), 1)

        user.delete()

        self.assertEqual(TripMember.objects.filter(user_id=user_id).count(), 0)


class TripMemberPermissionMethodTests(TestCase):
    """Tests for TripMember permission checking methods - core business logic."""

    @classmethod
    def setUpTestData(cls):
        """Set up test users and trip with various permission levels."""
        cls.owner_user = User.objects.create_user(email='owner@test.com', password='pass')
        cls.admin_user = User.objects.create_user(email='admin@test.com', password='pass')
        cls.editor_user = User.objects.create_user(email='editor@test.com', password='pass')
        cls.viewer_user = User.objects.create_user(email='viewer@test.com', password='pass')

        # Create trip with owner
        cls.trip = TripSyntheticData.create_test_trip(user=cls.owner_user, title='Test Trip')

        # Add members at different permission levels
        cls.owner_member = TripMember.objects.get(trip=cls.trip, user=cls.owner_user)
        cls.admin_member = TripSyntheticData.add_trip_member(
            trip=cls.trip,
            user=cls.admin_user,
            permission_level=TripPermissionLevel.ADMIN,
            added_by=cls.owner_user
        )
        cls.editor_member = TripSyntheticData.add_trip_member(
            trip=cls.trip,
            user=cls.editor_user,
            permission_level=TripPermissionLevel.EDITOR,
            added_by=cls.owner_user
        )
        cls.viewer_member = TripSyntheticData.add_trip_member(
            trip=cls.trip,
            user=cls.viewer_user,
            permission_level=TripPermissionLevel.VIEWER,
            added_by=cls.owner_user
        )

    def test_has_trip_permission_owner_access(self):
        """Owner has permission for all levels - permission hierarchy logic."""
        self.assertTrue(self.owner_member.has_trip_permission(TripPermissionLevel.VIEWER))
        self.assertTrue(self.owner_member.has_trip_permission(TripPermissionLevel.EDITOR))
        self.assertTrue(self.owner_member.has_trip_permission(TripPermissionLevel.ADMIN))
        self.assertTrue(self.owner_member.has_trip_permission(TripPermissionLevel.OWNER))

    def test_has_trip_permission_admin_access(self):
        """Admin has permission for admin/editor/viewer but not owner - permission boundary."""
        self.assertTrue(self.admin_member.has_trip_permission(TripPermissionLevel.VIEWER))
        self.assertTrue(self.admin_member.has_trip_permission(TripPermissionLevel.EDITOR))
        self.assertTrue(self.admin_member.has_trip_permission(TripPermissionLevel.ADMIN))
        self.assertFalse(self.admin_member.has_trip_permission(TripPermissionLevel.OWNER))

    def test_has_trip_permission_editor_access(self):
        """Editor has permission for editor/viewer but not admin - permission boundary."""
        self.assertTrue(self.editor_member.has_trip_permission(TripPermissionLevel.VIEWER))
        self.assertTrue(self.editor_member.has_trip_permission(TripPermissionLevel.EDITOR))
        self.assertFalse(self.editor_member.has_trip_permission(TripPermissionLevel.ADMIN))
        self.assertFalse(self.editor_member.has_trip_permission(TripPermissionLevel.OWNER))

    def test_has_trip_permission_viewer_access(self):
        """Viewer only has permission for viewer level - minimum permissions."""
        self.assertTrue(self.viewer_member.has_trip_permission(TripPermissionLevel.VIEWER))
        self.assertFalse(self.viewer_member.has_trip_permission(TripPermissionLevel.EDITOR))
        self.assertFalse(self.viewer_member.has_trip_permission(TripPermissionLevel.ADMIN))
        self.assertFalse(self.viewer_member.has_trip_permission(TripPermissionLevel.OWNER))

    def test_can_manage_members_owner_and_admin_only(self):
        """Only owner and admin can manage members - critical business rule."""
        self.assertTrue(self.owner_member.can_manage_members)
        self.assertTrue(self.admin_member.can_manage_members)
        self.assertFalse(self.editor_member.can_manage_members)
        self.assertFalse(self.viewer_member.can_manage_members)

    def test_can_edit_trip_editor_and_above(self):
        """Owner, admin, and editor can edit trip content - business rule."""
        self.assertTrue(self.owner_member.can_edit_trip)
        self.assertTrue(self.admin_member.can_edit_trip)
        self.assertTrue(self.editor_member.can_edit_trip)
        self.assertFalse(self.viewer_member.can_edit_trip)

    def test_can_manage_versions_owner_and_admin_only(self):
        """Only owner and admin can manage versions - critical business rule."""
        self.assertTrue(self.owner_member.can_manage_versions)
        self.assertTrue(self.admin_member.can_manage_versions)
        self.assertFalse(self.editor_member.can_manage_versions)
        self.assertFalse(self.viewer_member.can_manage_versions)

    def test_can_modify_member_owner_can_modify_all(self):
        """Owner can modify all members including other owners - highest privilege."""
        # Owner can modify everyone
        self.assertTrue(self.owner_member.can_modify_member(self.owner_member))
        self.assertTrue(self.owner_member.can_modify_member(self.admin_member))
        self.assertTrue(self.owner_member.can_modify_member(self.editor_member))
        self.assertTrue(self.owner_member.can_modify_member(self.viewer_member))

    def test_can_modify_member_admin_cannot_modify_owner(self):
        """Admin can modify admin/editor/viewer but not owner - permission boundary."""
        # Admin cannot modify owner
        self.assertFalse(self.admin_member.can_modify_member(self.owner_member))
        # Admin can modify equal or lower levels
        self.assertTrue(self.admin_member.can_modify_member(self.admin_member))
        self.assertTrue(self.admin_member.can_modify_member(self.editor_member))
        self.assertTrue(self.admin_member.can_modify_member(self.viewer_member))

    def test_can_modify_member_editor_cannot_modify_anyone(self):
        """Editor cannot modify any members - requires admin permission."""
        self.assertFalse(self.editor_member.can_modify_member(self.owner_member))
        self.assertFalse(self.editor_member.can_modify_member(self.admin_member))
        self.assertFalse(self.editor_member.can_modify_member(self.editor_member))
        self.assertFalse(self.editor_member.can_modify_member(self.viewer_member))

    def test_can_modify_member_viewer_cannot_modify_anyone(self):
        """Viewer cannot modify any members - no management permissions."""
        self.assertFalse(self.viewer_member.can_modify_member(self.owner_member))
        self.assertFalse(self.viewer_member.can_modify_member(self.admin_member))
        self.assertFalse(self.viewer_member.can_modify_member(self.editor_member))
        self.assertFalse(self.viewer_member.can_modify_member(self.viewer_member))

    def test_can_modify_member_requires_can_manage_members(self):
        """can_modify_member requires can_manage_members to be True - method dependency."""
        # Editor cannot manage members, so cannot modify even viewers
        self.assertFalse(self.editor_member.can_manage_members)
        self.assertFalse(self.editor_member.can_modify_member(self.viewer_member))

        # Admin can manage members, so can modify viewers
        self.assertTrue(self.admin_member.can_manage_members)
        self.assertTrue(self.admin_member.can_modify_member(self.viewer_member))

    def test_can_modify_member_permission_level_comparison(self):
        """can_modify_member requires modifier's level >= target's level - hierarchy enforcement."""
        # Create second admin to test same-level modification
        admin2_user = User.objects.create_user(email='admin2@test.com', password='pass')
        admin2_member = TripSyntheticData.add_trip_member(
            trip=self.trip,
            user=admin2_user,
            permission_level=TripPermissionLevel.ADMIN,
            added_by=self.owner_user
        )

        # Admin can modify another admin (equal level)
        self.assertTrue(self.admin_member.can_modify_member(admin2_member))

        # Admin can modify editor (lower level)
        self.assertTrue(self.admin_member.can_modify_member(self.editor_member))

        # Admin cannot modify owner (higher level)
        self.assertFalse(self.admin_member.can_modify_member(self.owner_member))
