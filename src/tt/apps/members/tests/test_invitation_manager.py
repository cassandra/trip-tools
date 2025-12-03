import logging
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.http import HttpRequest
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from tt.apps.members.invitation_manager import MemberInvitationManager
from tt.apps.members.models import TripMember
from tt.apps.trips.enums import TripPermissionLevel
from tt.apps.trips.tests.synthetic_data import TripSyntheticData
from tt.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)

User = get_user_model()


class TestMemberInvitationTokenSecurity(TestCase):
    """Test token validation security patterns."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(email='test@test.com', password='pass')
        cls.trip = TripSyntheticData.create_test_trip(user=cls.user, title='Test Trip')

    def setUp(self):
        self.manager = MemberInvitationManager()

    def test_verify_token_one_time_use_enforcement(self):
        """Test token becomes invalid after invitation is accepted (one-time use)."""
        # Create a second user to invite
        invited_user = User.objects.create_user(email='invited@test.com', password='pass')

        # Generate token for invited user
        token = self.manager._token_generator.make_token(invited_user)

        # Create trip member but DON'T accept yet
        member = TripMember.objects.create(
            trip=self.trip,
            user=invited_user,
            permission_level=TripPermissionLevel.VIEWER,
            added_by=self.user,
            invitation_accepted_datetime=None  # Not accepted
        )

        # Token should be valid before acceptance
        self.assertTrue(
            self.manager.verify_invitation_token(invited_user, token, self.trip)
        )

        # Accept the invitation
        member.invitation_accepted_datetime = timezone.now()
        member.save()

        # Token should now be INVALID (one-time use enforced)
        self.assertFalse(
            self.manager.verify_invitation_token(invited_user, token, self.trip)
        )

    def test_verify_token_invalid_token_rejected(self):
        """Test invalid tokens are rejected."""
        # Test various invalid tokens
        self.assertFalse(self.manager.verify_invitation_token(self.user, 'invalid_token'))
        self.assertFalse(self.manager.verify_invitation_token(self.user, ''))
        self.assertFalse(self.manager.verify_invitation_token(self.user, 'a' * 1000))
        self.assertFalse(self.manager.verify_invitation_token(self.user, None))

    def test_verify_token_wrong_user_rejected(self):
        """Test token for different user is rejected."""
        user1 = User.objects.create_user(email='user1@test.com', password='pass')
        user2 = User.objects.create_user(email='user2@test.com', password='pass')

        token = self.manager._token_generator.make_token(user1)

        # Token valid for user1
        self.assertTrue(self.manager.verify_invitation_token(user1, token))

        # Token INVALID for user2 (security boundary)
        self.assertFalse(self.manager.verify_invitation_token(user2, token))

    def test_verify_token_without_trip_parameter(self):
        """Test token validation without trip (doesn't check one-time use)."""
        token = self.manager._token_generator.make_token(self.user)

        # Without trip parameter, only validates token itself
        self.assertTrue(self.manager.verify_invitation_token(self.user, token))

        # Token remains valid even if used elsewhere
        # (one-time check requires trip parameter)
        self.assertTrue(self.manager.verify_invitation_token(self.user, token))

    def test_verify_token_nonexistent_member(self):
        """Test token validation for user not yet a member."""
        invited_user = User.objects.create_user(email='invited@test.com', password='pass')
        token = self.manager._token_generator.make_token(invited_user)

        # User not a member yet - token should be valid
        self.assertTrue(
            self.manager.verify_invitation_token(invited_user, token, self.trip)
        )

    def test_token_uniqueness_per_user(self):
        """Test tokens generated for different users are different."""
        user1 = User.objects.create_user(email='user1@test.com', password='pass')
        user2 = User.objects.create_user(email='user2@test.com', password='pass')

        token1 = self.manager._token_generator.make_token(user1)
        token2 = self.manager._token_generator.make_token(user2)

        # Tokens should be different for different users
        self.assertNotEqual(token1, token2)


class TestMemberInvitationEmailIntegration(TransactionTestCase):
    """Test email integration and transaction patterns."""

    def setUp(self):
        self.user = User.objects.create_user(email='owner@test.com', password='pass')
        self.trip = TripSyntheticData.create_test_trip(user=self.user, title='Test Trip')
        self.manager = MemberInvitationManager()

        # Create mock request
        self.mock_request = Mock(spec=HttpRequest)
        self.mock_request.build_absolute_uri = Mock(return_value='http://test.com/accept')

    def test_invite_member_existing_user_flow(self):
        """Test invitation flow for existing user (security: no user creation)."""
        existing_user = User.objects.create_user(
            email='existing@test.com',
            password='pass',
            email_verified=True
        )

        with patch('tt.apps.members.invitation_manager.EmailSender') as mock_sender:
            result = self.manager.invite_member(
                request = self.mock_request,
                trip = self.trip,
                email='existing@test.com',
                permission_level=TripPermissionLevel.EDITOR,
                invited_by_user=self.user,
                send_email=True
            )

        # Verify NO new user created (security: can't hijack existing accounts)
        self.assertFalse(result.new_user_created)
        self.assertEqual(result.trip_member.user, existing_user)

        # Verify invitation email sent (not signup email)
        mock_sender.return_value.send.assert_called_once()
        email_data = mock_sender.call_args[1]['data']
        self.assertEqual(
            email_data.subject_template_name,
            MemberInvitationManager.INVITATION_SUBJECT_TEMPLATE_NAME
        )

    def test_invite_member_new_user_security_defaults(self):
        """Test new user creation has secure defaults."""
        with patch('tt.apps.members.invitation_manager.EmailSender') as mock_sender:
            result = self.manager.invite_member(
                request=self.mock_request,
                trip=self.trip,
                email='newuser@test.com',
                permission_level=TripPermissionLevel.VIEWER,
                invited_by_user=self.user
            )

        # Verify new user created
        self.assertTrue(result.new_user_created)

        # Verify security defaults
        new_user = result.trip_member.user
        self.assertEqual(new_user.email, 'newuser@test.com')
        self.assertFalse(new_user.email_verified)  # CRITICAL: Not verified yet
        self.assertTrue(new_user.is_active)  # But active for login
        self.assertFalse(new_user.is_staff)
        self.assertFalse(new_user.is_superuser)

        # Verify signup email sent (not invitation email)
        mock_sender.return_value.send.assert_called_once()
        email_data = mock_sender.call_args[1]['data']
        self.assertEqual(
            email_data.subject_template_name,
            MemberInvitationManager.SIGNUP_SUBJECT_TEMPLATE_NAME
        )

    def test_invite_member_email_normalization(self):
        """Test email addresses are normalized (security: prevent duplicate accounts)."""
        with patch('tt.apps.members.invitation_manager.EmailSender'):
            # Invite with uppercase and whitespace
            result = self.manager.invite_member(
                request=self.mock_request,
                trip=self.trip,
                email='  NewUser@TEST.COM  ',  # Mixed case with whitespace
                permission_level=TripPermissionLevel.VIEWER,
                invited_by_user=self.user
            )

        # Verify email normalized to lowercase, trimmed
        self.assertEqual(result.trip_member.user.email, 'newuser@test.com')

    def test_invite_member_email_error_after_database_commit(self):
        """Test email error doesn't affect database commit (email is outside transaction)."""
        # Force email sending to fail
        with patch('tt.apps.members.invitation_manager.EmailSender') as mock_sender:
            mock_sender.return_value.send.side_effect = Exception('Email server error')

            with self.assertRaises(Exception):
                self.manager.invite_member(
                    request=self.mock_request,
                    trip=self.trip,
                    email='newuser@test.com',
                    permission_level=TripPermissionLevel.VIEWER,
                    invited_by_user=self.user,
                    send_email=True
                )

        # Verify database operations completed (email is sent outside transaction)
        self.assertTrue(User.objects.filter(email='newuser@test.com').exists())
        # Trip owner + new member should exist
        self.assertEqual(TripMember.objects.filter(trip=self.trip).count(), 2)

    def test_invite_member_send_email_false_no_email_sent(self):
        """Test send_email=False bypasses email sending (for testing/admin use)."""
        with patch('tt.apps.members.invitation_manager.EmailSender') as mock_sender:
            result = self.manager.invite_member(
                request=self.mock_request,
                trip=self.trip,
                email='newuser@test.com',
                permission_level=TripPermissionLevel.VIEWER,
                invited_by_user=self.user,
                send_email=False  # Bypass email
            )

        # Verify member created but NO email sent
        self.assertIsNotNone(result.trip_member)
        mock_sender.assert_not_called()

    def test_invite_member_permission_update_on_reinvite(self):
        """Test re-inviting existing member updates permissions (not a duplicate)."""
        invited_user = User.objects.create_user(email='invited@test.com', password='pass')

        with patch('tt.apps.members.invitation_manager.EmailSender'):
            # First invitation with VIEW permission
            result1 = self.manager.invite_member(
                request=self.mock_request,
                trip=self.trip,
                email='invited@test.com',
                permission_level=TripPermissionLevel.VIEWER,
                invited_by_user=self.user
            )

            # Second invitation with EDIT permission (upgrade)
            result2 = self.manager.invite_member(
                request=self.mock_request,
                trip=self.trip,
                email='invited@test.com',
                permission_level=TripPermissionLevel.EDITOR,
                invited_by_user=self.user
            )

        # Verify same member, permission upgraded, no duplicate
        self.assertEqual(result1.trip_member.id, result2.trip_member.id)
        self.assertEqual(result2.trip_member.permission_level, TripPermissionLevel.EDITOR)

        # Verify only one member record exists for this user/trip
        members = TripMember.objects.filter(trip=self.trip, user=invited_user)
        self.assertEqual(members.count(), 1)

    def test_invite_member_first_name_extraction(self):
        """Test new user first name extracted from email local part."""
        with patch('tt.apps.members.invitation_manager.EmailSender'):
            result = self.manager.invite_member(
                request=self.mock_request,
                trip=self.trip,
                email='john.doe@example.com',
                permission_level=TripPermissionLevel.VIEWER,
                invited_by_user=self.user
            )

        # Verify first name extracted from email
        self.assertEqual(result.trip_member.user.first_name, 'john.doe')


class TestMemberInvitationEdgeCases(BaseTestCase):
    """Test edge cases and boundary conditions."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(email='owner@test.com', password='pass')
        cls.trip = TripSyntheticData.create_test_trip(user=cls.user, title='Test Trip')

    def setUp(self):
        self.manager = MemberInvitationManager()

    def test_singleton_pattern_same_instance(self):
        """Test MemberInvitationManager follows singleton pattern."""
        manager1 = MemberInvitationManager()
        manager2 = MemberInvitationManager()

        # Should be same instance
        self.assertIs(manager1, manager2)

        # Token generator should be same
        self.assertIs(manager1._token_generator, manager2._token_generator)

    def test_verify_token_very_long_token(self):
        """Test token validation handles very long tokens gracefully."""
        very_long_token = 'a' * 10000

        # Should not raise exception, just return False
        result = self.manager.verify_invitation_token(self.user, very_long_token)
        self.assertFalse(result)

    def test_verify_token_special_characters(self):
        """Test token validation handles special characters."""
        special_tokens = [
            '<script>alert("xss")</script>',
            '../../etc/passwd',
            '\x00\x01\x02',
            '🚀🎉💯',
            'token\nwith\nnewlines'
        ]

        for token in special_tokens:
            with self.subTest(token=repr(token)):
                result = self.manager.verify_invitation_token(self.user, token)
                self.assertFalse(result)

    def test_email_case_insensitive_duplicate_prevention(self):
        """Test email case variations don't create duplicate users."""
        email_variations = [
            'user@test.com',
            'USER@TEST.COM',
            'User@Test.Com',
            '  user@test.com  ',
            'user@TEST.com'
        ]

        mock_request = Mock(spec=HttpRequest)
        mock_request.build_absolute_uri = Mock(return_value='http://test.com')

        created_users = []

        with patch('tt.apps.members.invitation_manager.EmailSender'):
            for email in email_variations:
                with self.subTest(email=email):
                    result = self.manager.invite_member(
                        request=mock_request,
                        trip=self.trip,
                        email=email,
                        permission_level=TripPermissionLevel.VIEWER,
                        invited_by_user=self.user,
                        send_email=False
                    )

                    if result.new_user_created:
                        created_users.append(result.trip_member.user)

        # Only one user should have been created (first variation)
        self.assertEqual(len(created_users), 1)

        # All variations should refer to the same user
        all_users = User.objects.filter(email='user@test.com')
        self.assertEqual(all_users.count(), 1)
