"""
Tests for Journal Forms - password validation and security patterns.

Tests focus on:
- JournalVisibilityForm password validation logic
- Password action (keep existing vs set new) handling
- Security boundaries (PROTECTED visibility requires password)
- Edge cases (empty passwords, whitespace, long passwords)
- Form state transitions (no password -> password, password -> new password)
- Timezone validation for JournalForm and JournalEntryForm
"""
import logging

from django.contrib.auth import get_user_model
from django.test import TestCase

from tt.apps.journal.enums import JournalVisibility
from tt.apps.journal.forms import JournalForm, JournalEntryForm, JournalVisibilityForm
from tt.apps.journal.models import Journal
from tt.apps.trips.tests.synthetic_data import TripSyntheticData
from tt.constants import TIMEZONE_NAME_LIST

logging.disable(logging.CRITICAL)

User = get_user_model()


class JournalVisibilityFormPasswordValidationTestCase(TestCase):
    """Test password validation for PROTECTED visibility."""

    def setUp(self):
        self.user = User.objects.create_user(email='test@test.com', password='pass')
        self.trip = TripSyntheticData.create_test_trip(user=self.user, title='Test Trip')

    def test_protected_visibility_requires_password_new_journal(self):
        """PROTECTED visibility requires password for journal without existing password."""
        # Create journal without password
        journal = Journal.objects.create(
            trip=self.trip,
            title='Test Journal',
            visibility=JournalVisibility.PRIVATE,
            timezone='UTC',
        )

        form = JournalVisibilityForm(
            data={
                'visibility': JournalVisibility.PROTECTED.name,
                'password': '',  # Empty password
            },
            journal=journal,
        )

        self.assertFalse(form.is_valid())
        self.assertIn('password', form.errors)
        self.assertIn('required', form.errors['password'][0].lower())

    def test_protected_visibility_accepts_valid_password_new_journal(self):
        """PROTECTED visibility accepts valid password for new protection."""
        journal = Journal.objects.create(
            trip=self.trip,
            title='Test Journal',
            visibility=JournalVisibility.PRIVATE,
            timezone='UTC',
        )

        form = JournalVisibilityForm(
            data={
                'visibility': JournalVisibility.PROTECTED.name,
                'password': 'secure_password_123',
            },
            journal=journal,
        )

        self.assertTrue(form.is_valid())

    def test_protected_visibility_keep_existing_password(self):
        """PROTECTED visibility can keep existing password without providing new one."""
        # Create journal with existing password
        journal = Journal.objects.create(
            trip=self.trip,
            title='Test Journal',
            visibility=JournalVisibility.PROTECTED,
            timezone='UTC',
        )
        journal.set_password('existing_password')
        journal.save()

        form = JournalVisibilityForm(
            data={
                'visibility': JournalVisibility.PROTECTED.name,
                'password_action': JournalVisibilityForm.PASSWORD_KEEP_EXISTING,
                'password': '',  # Empty password is OK when keeping existing
            },
            journal=journal,
        )

        self.assertTrue(form.is_valid())

    def test_protected_visibility_set_new_password_requires_password(self):
        """PROTECTED visibility with SET_NEW action requires password."""
        journal = Journal.objects.create(
            trip=self.trip,
            title='Test Journal',
            visibility=JournalVisibility.PROTECTED,
            timezone='UTC',
        )
        journal.set_password('old_password')
        journal.save()

        form = JournalVisibilityForm(
            data={
                'visibility': JournalVisibility.PROTECTED.name,
                'password_action': JournalVisibilityForm.PASSWORD_SET_NEW,
                'password': '',  # Empty password not allowed
            },
            journal=journal,
        )

        self.assertFalse(form.is_valid())
        self.assertIn('password', form.errors)
        self.assertIn('required', form.errors['password'][0].lower())

    def test_protected_visibility_set_new_password_valid(self):
        """PROTECTED visibility with SET_NEW action accepts new password."""
        journal = Journal.objects.create(
            trip=self.trip,
            title='Test Journal',
            visibility=JournalVisibility.PROTECTED,
            timezone='UTC',
        )
        journal.set_password('old_password')
        journal.save()

        form = JournalVisibilityForm(
            data={
                'visibility': JournalVisibility.PROTECTED.name,
                'password_action': JournalVisibilityForm.PASSWORD_SET_NEW,
                'password': 'new_secure_password',
            },
            journal=journal,
        )

        self.assertTrue(form.is_valid())

    def test_private_visibility_ignores_password(self):
        """PRIVATE visibility should not require password."""
        journal = Journal.objects.create(
            trip=self.trip,
            title='Test Journal',
            visibility=JournalVisibility.PRIVATE,
            timezone='UTC',
        )

        form = JournalVisibilityForm(
            data={
                'visibility': JournalVisibility.PRIVATE.name,
                'password': '',  # Empty password is fine for PRIVATE
            },
            journal=journal,
        )

        self.assertTrue(form.is_valid())

    def test_public_visibility_ignores_password(self):
        """PUBLIC visibility should not require password."""
        journal = Journal.objects.create(
            trip=self.trip,
            title='Test Journal',
            visibility=JournalVisibility.PUBLIC,
            timezone='UTC',
        )

        form = JournalVisibilityForm(
            data={
                'visibility': JournalVisibility.PUBLIC.name,
                'password': '',  # Empty password is fine for PUBLIC
            },
            journal=journal,
        )

        self.assertTrue(form.is_valid())

    def test_should_update_password_no_existing_password(self):
        """should_update_password returns True when no existing password."""
        journal = Journal.objects.create(
            trip=self.trip,
            title='Test Journal',
            visibility=JournalVisibility.PRIVATE,
            timezone='UTC',
        )

        form = JournalVisibilityForm(
            data={
                'visibility': JournalVisibility.PROTECTED.name,
                'password': 'new_password',
            },
            journal=journal,
        )

        self.assertTrue(form.is_valid())
        self.assertTrue(form.should_update_password())

    def test_should_update_password_keep_existing(self):
        """should_update_password returns False when KEEP_EXISTING selected."""
        journal = Journal.objects.create(
            trip=self.trip,
            title='Test Journal',
            visibility=JournalVisibility.PROTECTED,
            timezone='UTC',
        )
        journal.set_password('existing_password')
        journal.save()

        form = JournalVisibilityForm(
            data={
                'visibility': JournalVisibility.PROTECTED.name,
                'password_action': JournalVisibilityForm.PASSWORD_KEEP_EXISTING,
                'password': '',
            },
            journal=journal,
        )

        self.assertTrue(form.is_valid())
        self.assertFalse(form.should_update_password())

    def test_should_update_password_set_new(self):
        """should_update_password returns True when SET_NEW selected."""
        journal = Journal.objects.create(
            trip=self.trip,
            title='Test Journal',
            visibility=JournalVisibility.PROTECTED,
            timezone='UTC',
        )
        journal.set_password('old_password')
        journal.save()

        form = JournalVisibilityForm(
            data={
                'visibility': JournalVisibility.PROTECTED.name,
                'password_action': JournalVisibilityForm.PASSWORD_SET_NEW,
                'password': 'new_password',
            },
            journal=journal,
        )

        self.assertTrue(form.is_valid())
        self.assertTrue(form.should_update_password())


class JournalVisibilityFormInitializationTestCase(TestCase):
    """Test form initialization with journal instance."""

    def setUp(self):
        self.user = User.objects.create_user(email='test@test.com', password='pass')
        self.trip = TripSyntheticData.create_test_trip(user=self.user, title='Test Trip')

    def test_form_pre_populates_visibility(self):
        """Form should pre-populate visibility from journal."""
        journal = Journal.objects.create(
            trip=self.trip,
            title='Test Journal',
            visibility=JournalVisibility.PUBLIC,
            timezone='UTC',
        )

        form = JournalVisibilityForm(journal=journal)

        self.assertEqual(form.initial['visibility'], JournalVisibility.PUBLIC.name)

    def test_form_shows_password_action_when_password_exists(self):
        """Form should show password_action field when journal has password."""
        journal = Journal.objects.create(
            trip=self.trip,
            title='Test Journal',
            visibility=JournalVisibility.PROTECTED,
            timezone='UTC',
        )
        journal.set_password('existing_password')
        journal.save()

        form = JournalVisibilityForm(journal=journal)

        # Password action should be visible (not HiddenInput)
        self.assertNotEqual(
            form.fields['password_action'].widget.__class__.__name__,
            'HiddenInput'
        )
        self.assertEqual(
            form.initial['password_action'],
            JournalVisibilityForm.PASSWORD_KEEP_EXISTING
        )

    def test_form_hides_password_action_when_no_password(self):
        """Form should hide password_action field when journal has no password."""
        journal = Journal.objects.create(
            trip=self.trip,
            title='Test Journal',
            visibility=JournalVisibility.PRIVATE,
            timezone='UTC',
        )

        form = JournalVisibilityForm(journal=journal)

        # Password action should be hidden
        self.assertEqual(
            form.fields['password_action'].widget.__class__.__name__,
            'HiddenInput'
        )

    def test_form_without_journal_instance(self):
        """Form should work without journal instance (for new journals)."""
        form = JournalVisibilityForm(
            data={
                'visibility': JournalVisibility.PRIVATE.name,
            }
        )

        # Should be valid (PRIVATE doesn't require password)
        self.assertTrue(form.is_valid())


class JournalVisibilityFormEdgeCasesTestCase(TestCase):
    """Test edge cases and security boundaries."""

    def setUp(self):
        self.user = User.objects.create_user(email='test@test.com', password='pass')
        self.trip = TripSyntheticData.create_test_trip(user=self.user, title='Test Trip')

    def test_password_with_whitespace(self):
        """Password with whitespace should be accepted (but leading/trailing whitespace is stripped by Django)."""
        journal = Journal.objects.create(
            trip=self.trip,
            title='Test Journal',
            visibility=JournalVisibility.PRIVATE,
            timezone='UTC',
        )

        form = JournalVisibilityForm(
            data={
                'visibility': JournalVisibility.PROTECTED.name,
                'password': '  password with spaces  ',
            },
            journal=journal,
        )

        self.assertTrue(form.is_valid())
        # Django's PasswordInput strips leading/trailing whitespace by default
        self.assertEqual(form.cleaned_data['password'], 'password with spaces')

    def test_very_long_password(self):
        """Very long passwords should be accepted."""
        journal = Journal.objects.create(
            trip=self.trip,
            title='Test Journal',
            visibility=JournalVisibility.PRIVATE,
            timezone='UTC',
        )

        long_password = 'a' * 200

        form = JournalVisibilityForm(
            data={
                'visibility': JournalVisibility.PROTECTED.name,
                'password': long_password,
            },
            journal=journal,
        )

        self.assertTrue(form.is_valid())

    def test_password_with_special_characters(self):
        """Passwords with special characters should be accepted."""
        journal = Journal.objects.create(
            trip=self.trip,
            title='Test Journal',
            visibility=JournalVisibility.PRIVATE,
            timezone='UTC',
        )

        special_password = '!@#$%^&*()_+-=[]{}|;:,.<>?'

        form = JournalVisibilityForm(
            data={
                'visibility': JournalVisibility.PROTECTED.name,
                'password': special_password,
            },
            journal=journal,
        )

        self.assertTrue(form.is_valid())

    def test_password_with_unicode(self):
        """Unicode passwords should be accepted."""
        journal = Journal.objects.create(
            trip=self.trip,
            title='Test Journal',
            visibility=JournalVisibility.PRIVATE,
            timezone='UTC',
        )

        unicode_password = 'пароль密码🔒'

        form = JournalVisibilityForm(
            data={
                'visibility': JournalVisibility.PROTECTED.name,
                'password': unicode_password,
            },
            journal=journal,
        )

        self.assertTrue(form.is_valid())

    def test_switching_from_protected_to_private(self):
        """Switching from PROTECTED to PRIVATE should not require password."""
        journal = Journal.objects.create(
            trip=self.trip,
            title='Test Journal',
            visibility=JournalVisibility.PROTECTED,
            timezone='UTC',
        )
        journal.set_password('old_password')
        journal.save()

        form = JournalVisibilityForm(
            data={
                'visibility': JournalVisibility.PRIVATE.name,
                'password': '',  # Empty password is fine
            },
            journal=journal,
        )

        self.assertTrue(form.is_valid())

    def test_switching_from_private_to_protected(self):
        """Switching from PRIVATE to PROTECTED should require password."""
        journal = Journal.objects.create(
            trip=self.trip,
            title='Test Journal',
            visibility=JournalVisibility.PRIVATE,
            timezone='UTC',
        )

        form = JournalVisibilityForm(
            data={
                'visibility': JournalVisibility.PROTECTED.name,
                'password': '',  # Empty password not allowed
            },
            journal=journal,
        )

        self.assertFalse(form.is_valid())
        self.assertIn('password', form.errors)


class JournalFormTimezoneValidationTestCase(TestCase):
    """Test timezone validation for JournalForm."""

    def test_valid_timezone_accepted(self):
        """Valid timezone from TIMEZONE_NAME_LIST should be accepted."""
        form = JournalForm(
            data={
                'title': 'My Journal',
                'description': 'Test',
                'timezone': 'America/New_York',
                'theme': 'default',  # LabeledEnumField stores lowercase
            }
        )

        self.assertTrue(form.is_valid())

    def test_utc_timezone_accepted(self):
        """UTC timezone should be accepted."""
        form = JournalForm(
            data={
                'title': 'My Journal',
                'description': 'Test',
                'timezone': 'UTC',
                'theme': 'default',
            }
        )

        self.assertTrue(form.is_valid())

    def test_invalid_timezone_rejected(self):
        """Invalid timezone not in TIMEZONE_NAME_LIST should be rejected."""
        form = JournalForm(
            data={
                'title': 'My Journal',
                'description': 'Test',
                'timezone': 'Invalid/Timezone',
                'theme': 'default',
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn('timezone', form.errors)

    def test_empty_timezone_rejected(self):
        """Empty timezone should be rejected."""
        form = JournalForm(
            data={
                'title': 'My Journal',
                'description': 'Test',
                'timezone': '',
                'theme': 'default',
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn('timezone', form.errors)

    def test_all_timezones_in_list_valid(self):
        """All timezones in TIMEZONE_NAME_LIST should be valid choices."""
        for tz in TIMEZONE_NAME_LIST:
            with self.subTest(timezone=tz):
                form = JournalForm(
                    data={
                        'title': 'My Journal',
                        'description': '',
                        'timezone': tz,
                        'theme': 'default',
                    }
                )

                self.assertTrue(form.is_valid(), f"Timezone {tz} should be valid")


class JournalEntryFormTimezoneValidationTestCase(TestCase):
    """Test timezone validation for JournalEntryForm."""

    def test_valid_timezone_accepted(self):
        """Valid timezone from TIMEZONE_NAME_LIST should be accepted."""
        form = JournalEntryForm(
            data={
                'title': 'Day 1',
                'date': '2025-01-15',
                'timezone': 'Europe/London',
            }
        )

        self.assertTrue(form.is_valid())

    def test_invalid_timezone_rejected(self):
        """Invalid timezone should be rejected."""
        form = JournalEntryForm(
            data={
                'title': 'Day 1',
                'date': '2025-01-15',
                'timezone': 'Not/A/Timezone',
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn('timezone', form.errors)

    def test_asia_timezones_accepted(self):
        """Asian timezones should be accepted."""
        asian_timezones = [
            'Asia/Tokyo', 'Asia/Seoul', 'Asia/Shanghai',
            'Asia/Hong_Kong', 'Asia/Singapore', 'Asia/Kolkata'
        ]

        for tz in asian_timezones:
            with self.subTest(timezone=tz):
                form = JournalEntryForm(
                    data={
                        'title': 'Day 1',
                        'date': '2025-01-15',
                        'timezone': tz,
                    }
                )

                self.assertTrue(form.is_valid())

    def test_australia_timezones_accepted(self):
        """Australian timezones should be accepted."""
        form = JournalEntryForm(
            data={
                'title': 'Day 1',
                'date': '2025-01-15',
                'timezone': 'Australia/Sydney',
            }
        )

        self.assertTrue(form.is_valid())


class JournalFormFieldValidationTestCase(TestCase):
    """Test general field validation for JournalForm."""

    def test_title_required(self):
        """Title field should be required."""
        form = JournalForm(
            data={
                'title': '',
                'description': 'Test',
                'timezone': 'UTC',
                'theme': 'default',
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn('title', form.errors)

    def test_description_optional(self):
        """Description field should be optional."""
        form = JournalForm(
            data={
                'title': 'My Journal',
                'description': '',
                'timezone': 'UTC',
                'theme': 'default',
            }
        )

        self.assertTrue(form.is_valid())

    def test_long_title_accepted(self):
        """Long titles (up to max_length) should be accepted."""
        long_title = 'A' * 200  # Max length is 200

        form = JournalForm(
            data={
                'title': long_title,
                'description': '',
                'timezone': 'UTC',
                'theme': 'default',
            }
        )

        self.assertTrue(form.is_valid())

    def test_theme_customization_help_text(self):
        """Form should customize theme field help text."""
        form = JournalForm()

        self.assertIn('theme', form.fields)
        self.assertIn('Color theme', form.fields['theme'].help_text)
