"""
Tests for journal entry autosave functionality.

Tests HTML sanitization, version conflict detection, and atomic updates
for journal entries using ContentEditable.
"""
import logging

import json
from datetime import date
from django.contrib.auth import get_user_model
from django.test import TestCase, TransactionTestCase
from django.urls import reverse

from tt.apps.members.models import TripMember
from tt.apps.trips.models import Trip
from tt.apps.trips.enums import TripPermissionLevel
from tt.apps.journal.models import Journal, JournalEntry
from tt.apps.journal.autosave_helpers import JournalAutoSaveHelper

logging.disable(logging.CRITICAL)

User = get_user_model()


class JournalEntryAutosaveBasicTests(TestCase):
    """Basic tests for journal entry autosave functionality."""

    @classmethod
    def setUpTestData(cls):
        """Set up test fixtures once for all tests."""
        cls.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        cls.trip = Trip.objects.create(
            title='Test Trip',
            description='A test trip'
        )
        cls.trip_member = TripMember.objects.create(
            trip=cls.trip,
            user=cls.user,
            permission_level=TripPermissionLevel.OWNER
        )
        cls.journal = Journal.objects.create(
            trip=cls.trip,
            title='Test Journal',
            timezone='America/New_York',
            visibility='private',
            modified_by=cls.user
        )
        cls.entry = JournalEntry.objects.create(
            journal=cls.journal,
            date=date(2024, 1, 1),
            timezone='America/New_York',
            title='Day 1',
            text='<p>Initial content</p>',
            modified_by=cls.user
        )

    def setUp(self):
        """Set up per-test state."""
        self.client.login(email='test@example.com', password='testpass123')

    def test_autosave_basic_text_update(self):
        """Test basic autosave of text content."""
        url = reverse('journal_entry_autosave', kwargs={
            'entry_uuid': self.entry.uuid
        })

        data = {
            'text': '<p>Updated content with <strong>bold</strong> text</p>',
            'version': 1,
        }

        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data['status'], 'success')
        self.assertEqual(response_data['version'], 2)

        # Verify entry was updated
        self.entry.refresh_from_db()
        self.assertEqual(self.entry.edit_version, 2)
        self.assertIn('Updated content', self.entry.text)
        self.assertIn('<strong>bold</strong>', self.entry.text)

    def test_autosave_sanitizes_malicious_html(self):
        """Test that malicious HTML is sanitized."""
        url = reverse('journal_entry_autosave', kwargs={
            'entry_uuid': self.entry.uuid
        })

        data = {
            'text': '<p>Safe content</p><script>alert("XSS")</script>',
            'version': 1,
        }

        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)

        # Verify malicious content was removed
        self.entry.refresh_from_db()
        self.assertIn('Safe content', self.entry.text)
        self.assertNotIn('<script>', self.entry.text)
        self.assertNotIn('</script>', self.entry.text)

    def test_autosave_removes_event_handlers(self):
        """Test that event handlers are removed."""
        url = reverse('journal_entry_autosave', kwargs={
            'entry_uuid': self.entry.uuid
        })

        data = {
            'text': '<p onclick="alert(\'XSS\')">Click me</p>',
            'version': 1,
        }

        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)

        # Verify event handler was removed
        self.entry.refresh_from_db()
        self.assertNotIn('onclick', self.entry.text)
        self.assertIn('Click me', self.entry.text)

    def test_autosave_updates_title(self):
        """Test that title can be updated via autosave."""
        url = reverse('journal_entry_autosave', kwargs={
            'entry_uuid': self.entry.uuid
        })

        data = {
            'text': '<p>Content</p>',
            'new_title': 'Updated Day 1 Title',
            'version': 1,
        }

        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)

        self.entry.refresh_from_db()
        self.assertEqual(self.entry.title, 'Updated Day 1 Title')

    def test_autosave_updates_date(self):
        """Test that date can be updated via autosave."""
        url = reverse('journal_entry_autosave', kwargs={
            'entry_uuid': self.entry.uuid
        })

        new_date = '2024-01-02'
        data = {
            'text': '<p>Content</p>',
            'new_date': new_date,
            'version': 1,
        }

        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)

        self.entry.refresh_from_db()
        self.assertEqual(self.entry.date, date(2024, 1, 2))

    def test_autosave_date_conflict_detection(self):
        """Test that date conflicts are detected."""
        # Create another entry for Jan 2
        JournalEntry.objects.create(
            journal=self.journal,
            date=date(2024, 1, 2),
            timezone='America/New_York',
            title='Day 2',
            text='<p>Day 2 content</p>',
            modified_by=self.user
        )

        url = reverse('journal_entry_autosave', kwargs={
            'entry_uuid': self.entry.uuid
        })

        # Try to change entry date to Jan 2 (conflict)
        data = {
            'text': '<p>Content</p>',
            'new_date': '2024-01-02',
            'version': 1,
        }

        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertEqual(response_data['status'], 'error')
        self.assertIn('already exists', response_data['message'])

    def test_autosave_version_conflict_detection(self):
        """Test that version conflicts are detected."""
        url = reverse('journal_entry_autosave', kwargs={
            'entry_uuid': self.entry.uuid
        })

        data = {
            'text': '<p>Updated by stale client</p>',
            'version': 999,  # Wrong version
        }

        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 409)
        response_data = response.json()
        self.assertEqual(response_data['server_version'], 1)
        self.assertIn('modal', response_data)

    def test_autosave_invalid_json(self):
        """Test handling of invalid JSON."""
        url = reverse('journal_entry_autosave', kwargs={
            'entry_uuid': self.entry.uuid
        })

        response = self.client.post(
            url,
            data='invalid json',
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 400)

    def test_autosave_requires_authentication(self):
        """Test that autosave requires authentication."""
        self.client.logout()

        url = reverse('journal_entry_autosave', kwargs={
            'entry_uuid': self.entry.uuid
        })

        data = {
            'text': '<p>Content</p>',
            'version': 1,
        }

        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_autosave_requires_editor_permission(self):
        """Test that autosave requires editor permission."""
        # Create viewer user
        viewer = User.objects.create_user(
            email='viewer@example.com',
            password='testpass123',
            first_name='Viewer',
            last_name='User'
        )
        TripMember.objects.create(
            trip=self.trip,
            user=viewer,
            permission_level=TripPermissionLevel.VIEWER
        )

        self.client.login(email='viewer@example.com', password='testpass123')

        url = reverse('journal_entry_autosave', kwargs={
            'entry_uuid': self.entry.uuid
        })

        data = {
            'text': '<p>Content</p>',
            'version': 1,
        }

        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 403)

    def test_autosave_get_method_not_allowed(self):
        """Test that GET method is not allowed."""
        url = reverse('journal_entry_autosave', kwargs={
            'entry_uuid': self.entry.uuid
        })

        response = self.client.get(url)
        self.assertEqual(response.status_code, 405)

    def test_autosave_date_change_detection_with_default_title(self):
        """Test date change detection and title auto-regeneration."""
        # Set up entry with default title pattern
        self.entry.date = date(2024, 1, 15)  # Monday
        self.entry.title = 'Monday, January 15, 2024'
        self.entry.save()

        url = reverse('journal_entry_autosave', kwargs={
            'entry_uuid': self.entry.uuid
        })

        # Change date to Jan 16 - JS always sends current title
        data = {
            'text': '<p>Content</p>',
            'new_date': '2024-01-16',
            'new_title': 'Monday, January 15, 2024',  # Current title (matches old default)
            'version': 1,
        }

        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data['status'], 'success')
        self.assertTrue(response_data['date_changed'])
        self.assertTrue(response_data['title_updated'])

        # Verify entry was updated with new date and auto-generated title
        self.entry.refresh_from_db()
        self.assertEqual(self.entry.date, date(2024, 1, 16))
        self.assertEqual(self.entry.title, 'Tuesday, January 16, 2024')

    def test_autosave_date_change_with_custom_title_preserves_title(self):
        """Test that custom titles are preserved when date changes."""
        # Set up entry with custom title
        self.entry.date = date(2024, 1, 15)
        self.entry.title = 'My Custom Adventure Title'
        self.entry.save()

        url = reverse('journal_entry_autosave', kwargs={
            'entry_uuid': self.entry.uuid
        })

        # Change date - JS always sends current title
        data = {
            'text': '<p>Content</p>',
            'new_date': '2024-01-16',
            'new_title': 'My Custom Adventure Title',  # Custom title (not default pattern)
            'version': 1,
        }

        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data['status'], 'success')
        self.assertTrue(response_data['date_changed'])
        self.assertFalse(response_data['title_updated'])

        # Verify custom title was preserved
        self.entry.refresh_from_db()
        self.assertEqual(self.entry.date, date(2024, 1, 16))
        self.assertEqual(self.entry.title, 'My Custom Adventure Title')

    def test_autosave_no_date_change_no_flags(self):
        """Test that flags are False when date doesn't change."""
        url = reverse('journal_entry_autosave', kwargs={
            'entry_uuid': self.entry.uuid
        })

        data = {
            'text': '<p>Updated content</p>',
            'version': 1,
        }

        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data['status'], 'success')
        self.assertFalse(response_data['date_changed'])
        self.assertFalse(response_data['title_updated'])

    def test_autosave_date_change_with_explicit_title_override(self):
        """Test that explicit title in request takes precedence over auto-generation."""
        # Set up entry with default title
        self.entry.date = date(2024, 1, 15)
        self.entry.title = 'Monday, January 15, 2024'
        self.entry.save()

        url = reverse('journal_entry_autosave', kwargs={
            'entry_uuid': self.entry.uuid
        })

        # Change both date and title explicitly
        data = {
            'text': '<p>Content</p>',
            'new_date': '2024-01-16',
            'new_title': 'User Override Title',
            'version': 1,
        }

        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data['status'], 'success')
        self.assertTrue(response_data['date_changed'])
        # title_updated should be False because we're using explicit title from request
        self.assertFalse(response_data['title_updated'])

        # Verify explicit title was used
        self.entry.refresh_from_db()
        self.assertEqual(self.entry.date, date(2024, 1, 16))
        self.assertEqual(self.entry.title, 'User Override Title')


class JournalEntryAutosaveHelperTests(TestCase):
    """Tests for JournalAutoSaveHelper utility functions."""

    def test_parse_autosave_request_basic(self):
        """Test parsing basic autosave request."""
        data = {
            'text': '<p>Test</p>',
            'version': 1,
        }
        request_body = json.dumps(data).encode('utf-8')

        autosave_request, error = JournalAutoSaveHelper.parse_autosave_request(request_body)

        self.assertIsNone(error)
        self.assertIsNotNone(autosave_request)
        self.assertEqual(autosave_request.text, '<p>Test</p>')
        self.assertEqual(autosave_request.client_version, 1)

    def test_parse_autosave_request_with_all_fields(self):
        """Test parsing autosave request with all fields."""
        data = {
            'text': '<p>Test</p>',
            'version': 5,
            'new_date': '2024-01-15',
            'new_title': 'New Title',
            'new_timezone': 'Europe/London',
            'reference_image_uuid': '550e8400-e29b-41d4-a716-446655440000',
        }
        request_body = json.dumps(data).encode('utf-8')

        autosave_request, error = JournalAutoSaveHelper.parse_autosave_request(request_body)

        self.assertIsNone(error)
        self.assertEqual(autosave_request.text, '<p>Test</p>')
        self.assertEqual(autosave_request.client_version, 5)
        self.assertEqual(autosave_request.new_date, date(2024, 1, 15))
        self.assertEqual(autosave_request.new_title, 'New Title')
        self.assertEqual(autosave_request.new_timezone, 'Europe/London')
        self.assertEqual(autosave_request.new_reference_image_uuid, '550e8400-e29b-41d4-a716-446655440000')

    def test_parse_autosave_request_invalid_json(self):
        """Test parsing invalid JSON."""
        request_body = b'invalid json'

        autosave_request, error = JournalAutoSaveHelper.parse_autosave_request(request_body)

        self.assertIsNone(autosave_request)
        self.assertIsNotNone(error)
        self.assertEqual(error.status_code, 400)

    def test_parse_autosave_request_invalid_date(self):
        """Test parsing request with invalid date."""
        data = {
            'text': '<p>Test</p>',
            'new_date': 'not-a-date',
        }
        request_body = json.dumps(data).encode('utf-8')

        autosave_request, error = JournalAutoSaveHelper.parse_autosave_request(request_body)

        self.assertIsNone(autosave_request)
        self.assertIsNotNone(error)
        self.assertEqual(error.status_code, 400)

    def test_sanitize_html_content(self):
        """Test HTML sanitization."""
        html = '<p>Safe</p><script>alert("XSS")</script>'
        sanitized = JournalAutoSaveHelper.sanitize_html_content(html)

        self.assertIn('Safe', sanitized)
        self.assertNotIn('<script>', sanitized)
        self.assertNotIn('</script>', sanitized)

    def test_is_default_title_for_date_match(self):
        """Test detecting when title matches default pattern."""
        test_date = date(2025, 11, 25)
        title = 'Tuesday, November 25, 2025'
        self.assertTrue(
            JournalAutoSaveHelper.is_default_title_for_date(title, test_date)
        )

    def test_is_default_title_for_date_custom_title(self):
        """Test detecting when title is custom (not default)."""
        test_date = date(2025, 11, 25)
        title = 'My Custom Title'
        self.assertFalse(
            JournalAutoSaveHelper.is_default_title_for_date(title, test_date)
        )

    def test_is_default_title_for_date_wrong_date(self):
        """Test detecting when title matches a different date."""
        test_date = date(2025, 11, 25)
        # Title for November 26 instead
        title = 'Wednesday, November 26, 2025'
        self.assertFalse(
            JournalAutoSaveHelper.is_default_title_for_date(title, test_date)
        )


class JournalEntryAtomicUpdateTests(TransactionTestCase):
    """Tests for atomic updates with version control."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        self.trip = Trip.objects.create(
            title='Test Trip',
            description='A test trip'
        )
        self.trip_member = TripMember.objects.create(
            trip=self.trip,
            user=self.user,
            permission_level=TripPermissionLevel.OWNER
        )
        self.journal = Journal.objects.create(
            trip=self.trip,
            title='Test Journal',
            timezone='America/New_York',
            visibility='private',
            modified_by=self.user
        )
        self.entry = JournalEntry.objects.create(
            journal=self.journal,
            date=date(2024, 1, 1),
            timezone='America/New_York',
            title='Day 1',
            text='<p>Initial content</p>',
            modified_by=self.user
        )

    def test_version_increments_atomically(self):
        """Test that version increments atomically."""
        initial_version = self.entry.edit_version

        updated_entry = JournalAutoSaveHelper.update_entry_atomically(
            entry=self.entry,
            text='<p>Updated</p>',
            user=self.user
        )

        self.assertEqual(updated_entry.edit_version, initial_version + 1)
        self.assertEqual(updated_entry.text, '<p>Updated</p>')

    def test_multiple_fields_update_atomically(self):
        """Test that multiple fields update atomically."""
        updated_entry = JournalAutoSaveHelper.update_entry_atomically(
            entry=self.entry,
            text='<p>New text</p>',
            user=self.user,
            new_date=date(2024, 1, 5),
            new_title='New Title',
            new_timezone='Europe/Paris'
        )

        self.assertEqual(updated_entry.text, '<p>New text</p>')
        self.assertEqual(updated_entry.date, date(2024, 1, 5))
        self.assertEqual(updated_entry.title, 'New Title')
        self.assertEqual(updated_entry.timezone, 'Europe/Paris')
        self.assertEqual(updated_entry.edit_version, 2)
