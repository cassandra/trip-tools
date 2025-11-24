"""
Tests for Journal model password security and business logic.

Tests critical security patterns including:
- Password hashing and verification
- Password version tracking for session invalidation
- Security configuration validation (is_misconfigured_protected)
- Password clearing and state management
"""
import logging

from django.contrib.auth import get_user_model
from django.test import TestCase

from tt.apps.journal.models import Journal
from tt.apps.journal.enums import JournalVisibility
from tt.apps.trips.tests.synthetic_data import TripSyntheticData

logging.disable(logging.CRITICAL)

User = get_user_model()


class TestJournalPasswordSecurity(TestCase):
    """Test Journal password hashing and verification."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.trip = TripSyntheticData.create_test_trip(
            user=self.user,
            title='Test Trip'
        )
        self.journal = Journal.objects.create(
            trip=self.trip,
            title='Test Journal',
            visibility=JournalVisibility.PROTECTED
        )

    def test_set_password_hashes_password(self):
        """Test set_password stores hashed password, not plaintext."""
        raw_password = 'my_secret_password_123'
        self.journal.set_password(raw_password)

        # Password should be hashed, not stored as plaintext
        self.assertNotEqual(self.journal._password, raw_password)
        self.assertTrue(len(self.journal._password) > len(raw_password))
        self.assertTrue(self.journal.has_password)

    def test_check_password_correct_password(self):
        """Test check_password returns True for correct password."""
        raw_password = 'my_secret_password_123'
        self.journal.set_password(raw_password)

        # Correct password should verify
        self.assertTrue(self.journal.check_password(raw_password))

    def test_check_password_incorrect_password(self):
        """Test check_password returns False for incorrect password."""
        self.journal.set_password('correct_password')

        # Incorrect password should fail
        self.assertFalse(self.journal.check_password('wrong_password'))
        self.assertFalse(self.journal.check_password(''))
        self.assertFalse(self.journal.check_password('correct_password_typo'))

    def test_check_password_no_password_set(self):
        """Test check_password returns False when no password is set."""
        # Journal has no password set
        self.assertFalse(self.journal.has_password)
        self.assertFalse(self.journal.check_password('any_password'))
        self.assertFalse(self.journal.check_password(''))

    def test_set_password_increments_version(self):
        """Test set_password increments password_version."""
        # Initial version
        initial_version = self.journal.password_version
        self.assertEqual(initial_version, 1)

        # Set password
        self.journal.set_password('first_password')
        self.assertEqual(self.journal.password_version, 2)

        # Change password again
        self.journal.set_password('second_password')
        self.assertEqual(self.journal.password_version, 3)

        # Change password again
        self.journal.set_password('third_password')
        self.assertEqual(self.journal.password_version, 4)

    def test_set_password_empty_clears_password(self):
        """Test set_password with empty string clears the password."""
        # Set a password first
        self.journal.set_password('some_password')
        self.assertTrue(self.journal.has_password)

        # Clear with empty string
        self.journal.set_password('')
        self.assertFalse(self.journal.has_password)
        self.assertIsNone(self.journal._password)

    def test_set_password_none_clears_password(self):
        """Test set_password with None clears the password."""
        # Set a password first
        self.journal.set_password('some_password')
        self.assertTrue(self.journal.has_password)

        # Clear with None
        self.journal.set_password(None)
        self.assertFalse(self.journal.has_password)
        self.assertIsNone(self.journal._password)

    def test_has_password_property(self):
        """Test has_password property reflects password state correctly."""
        # No password initially
        self.assertFalse(self.journal.has_password)

        # Set password
        self.journal.set_password('password123')
        self.assertTrue(self.journal.has_password)

        # Clear password
        self.journal.set_password(None)
        self.assertFalse(self.journal.has_password)

    def test_password_version_session_invalidation_use_case(self):
        """Test password_version increments enable session invalidation."""
        # Simulate: User logs in, we store password_version in session
        self.journal.set_password('initial_password')
        session_version = self.journal.password_version
        self.assertEqual(session_version, 2)

        # User changes password
        self.journal.set_password('new_password')
        current_version = self.journal.password_version
        self.assertEqual(current_version, 3)

        # Session version no longer matches - session should be invalidated
        self.assertNotEqual(session_version, current_version)

    def test_password_hashing_uses_django_hasher(self):
        """Test password hashing uses Django's password hasher format."""
        self.journal.set_password('test_password')

        # Django password hashes start with algorithm identifier
        # Common formats: pbkdf2_sha256$..., argon2$..., etc.
        self.assertIn('$', self.journal._password)
        # Should have multiple components separated by $
        parts = self.journal._password.split('$')
        self.assertGreaterEqual(len(parts), 3)

    def test_password_same_plaintext_different_hashes(self):
        """Test same password creates different hashes (due to salt)."""
        journal2 = Journal.objects.create(
            trip=self.trip,
            title='Another Journal',
            visibility=JournalVisibility.PROTECTED
        )

        password = 'same_password_123'
        self.journal.set_password(password)
        journal2.set_password(password)

        # Same plaintext should produce different hashes (salt)
        self.assertNotEqual(self.journal._password, journal2._password)

        # But both should verify correctly
        self.assertTrue(self.journal.check_password(password))
        self.assertTrue(journal2.check_password(password))


class TestJournalSecurityConfiguration(TestCase):
    """Test Journal security configuration validation."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.trip = TripSyntheticData.create_test_trip(
            user=self.user,
            title='Test Trip'
        )

    def test_is_misconfigured_protected_false_when_password_set(self):
        """Test is_misconfigured_protected is False when PROTECTED has password."""
        journal = Journal.objects.create(
            trip=self.trip,
            title='Test Journal',
            visibility=JournalVisibility.PROTECTED
        )
        journal.set_password('secure_password')

        # Properly configured - has password
        self.assertFalse(journal.is_misconfigured_protected)

    def test_is_misconfigured_protected_true_when_no_password(self):
        """Test is_misconfigured_protected is True when PROTECTED has no password."""
        journal = Journal.objects.create(
            trip=self.trip,
            title='Test Journal',
            visibility=JournalVisibility.PROTECTED
        )

        # Misconfigured - PROTECTED but no password
        self.assertTrue(journal.is_misconfigured_protected)

    def test_is_misconfigured_protected_false_for_public(self):
        """Test is_misconfigured_protected is False for PUBLIC journals."""
        journal = Journal.objects.create(
            trip=self.trip,
            title='Test Journal',
            visibility=JournalVisibility.PUBLIC
        )

        # PUBLIC journals don't need passwords
        self.assertFalse(journal.is_misconfigured_protected)

    def test_is_misconfigured_protected_false_for_private(self):
        """Test is_misconfigured_protected is False for PRIVATE journals."""
        journal = Journal.objects.create(
            trip=self.trip,
            title='Test Journal',
            visibility=JournalVisibility.PRIVATE
        )

        # PRIVATE journals don't need passwords
        self.assertFalse(journal.is_misconfigured_protected)

    def test_is_misconfigured_protected_after_password_cleared(self):
        """Test is_misconfigured_protected becomes True if password is cleared."""
        journal = Journal.objects.create(
            trip=self.trip,
            title='Test Journal',
            visibility=JournalVisibility.PROTECTED
        )

        # Set password - properly configured
        journal.set_password('password123')
        self.assertFalse(journal.is_misconfigured_protected)

        # Clear password - becomes misconfigured
        journal.set_password(None)
        self.assertTrue(journal.is_misconfigured_protected)

    def test_is_misconfigured_protected_after_visibility_change(self):
        """Test is_misconfigured_protected after changing visibility."""
        journal = Journal.objects.create(
            trip=self.trip,
            title='Test Journal',
            visibility=JournalVisibility.PUBLIC
        )

        # PUBLIC without password - not misconfigured
        self.assertFalse(journal.is_misconfigured_protected)

        # Change to PROTECTED without setting password - becomes misconfigured
        journal.visibility = JournalVisibility.PROTECTED
        self.assertTrue(journal.is_misconfigured_protected)

        # Set password - no longer misconfigured
        journal.set_password('new_password')
        self.assertFalse(journal.is_misconfigured_protected)


class TestJournalPasswordEdgeCases(TestCase):
    """Test Journal password edge cases and boundary conditions."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.trip = TripSyntheticData.create_test_trip(
            user=self.user,
            title='Test Trip'
        )
        self.journal = Journal.objects.create(
            trip=self.trip,
            title='Test Journal',
            visibility=JournalVisibility.PROTECTED
        )

    def test_password_with_special_characters(self):
        """Test password with special characters works correctly."""
        special_password = 'P@ssw0rd!#$%^&*()_+-=[]{}|;:,.<>?'
        self.journal.set_password(special_password)

        self.assertTrue(self.journal.check_password(special_password))
        self.assertFalse(self.journal.check_password('P@ssw0rd'))  # Partial match fails

    def test_password_with_unicode_characters(self):
        """Test password with unicode characters works correctly."""
        unicode_password = 'пароль密码🔒'
        self.journal.set_password(unicode_password)

        self.assertTrue(self.journal.check_password(unicode_password))
        self.assertFalse(self.journal.check_password('password'))

    def test_password_very_long(self):
        """Test very long password is handled correctly."""
        long_password = 'a' * 1000
        self.journal.set_password(long_password)

        self.assertTrue(self.journal.check_password(long_password))
        self.assertFalse(self.journal.check_password('a' * 999))

    def test_password_single_character(self):
        """Test single character password works (even if not recommended)."""
        self.journal.set_password('x')

        self.assertTrue(self.journal.check_password('x'))
        self.assertFalse(self.journal.check_password('xx'))

    def test_password_whitespace_only(self):
        """Test password with only whitespace."""
        whitespace_password = '   '
        self.journal.set_password(whitespace_password)

        # Should store and verify whitespace password
        self.assertTrue(self.journal.has_password)
        self.assertTrue(self.journal.check_password('   '))
        self.assertFalse(self.journal.check_password(''))
        self.assertFalse(self.journal.check_password('  '))  # Different whitespace

    def test_password_case_sensitivity(self):
        """Test password verification is case-sensitive."""
        self.journal.set_password('Password123')

        self.assertTrue(self.journal.check_password('Password123'))
        self.assertFalse(self.journal.check_password('password123'))
        self.assertFalse(self.journal.check_password('PASSWORD123'))

    def test_password_version_starts_at_one(self):
        """Test password_version starts at 1 for new journals."""
        new_journal = Journal.objects.create(
            trip=self.trip,
            title='New Journal',
            visibility=JournalVisibility.PUBLIC
        )

        self.assertEqual(new_journal.password_version, 1)

    def test_password_version_increments_from_zero(self):
        """Test password_version handles None/0 initial value."""
        # Simulate a journal with version set to 0
        self.journal.password_version = 0
        self.journal.save()

        self.journal.set_password('test_password')
        self.assertEqual(self.journal.password_version, 1)

    def test_password_version_only_increments_when_password_set(self):
        """Test password_version doesn't increment when clearing password."""
        initial_version = self.journal.password_version

        # Set password - version increments
        self.journal.set_password('password')
        self.assertEqual(self.journal.password_version, initial_version + 1)

        # Clear password - version doesn't increment
        version_before_clear = self.journal.password_version
        self.journal.set_password(None)
        # Version doesn't change when clearing (no password to set)
        self.assertEqual(self.journal.password_version, version_before_clear)

    def test_has_password_with_empty_string_stored(self):
        """Test has_password returns False for empty string (edge case)."""
        # Manually set _password to empty string (shouldn't happen normally)
        self.journal._password = ''
        self.assertFalse(self.journal.has_password)

        # Whitespace-only is also considered blank/no password
        self.journal._password = ' '
        self.assertFalse(self.journal.has_password)

        # But actual content (even with surrounding whitespace) is considered a password
        self.journal._password = ' x '
        self.assertTrue(self.journal.has_password)
