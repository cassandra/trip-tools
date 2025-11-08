"""
Tests for journal entry autosave functionality.

Tests HTML sanitization, version conflict detection, and atomic updates
for journal entries using ContentEditable.
"""
import json
from datetime import date
from django.contrib.auth import get_user_model
from django.test import TestCase, TransactionTestCase
from django.urls import reverse

from tt.apps.trips.models import Trip, TripMember
from tt.apps.trips.enums import TripPermissionLevel
from tt.apps.journal.models import Journal, JournalEntry
from tt.apps.journal.autosave_helpers import JournalAutoSaveHelper

User = get_user_model()


class JournalEntryAutosaveBasicTests(TestCase):
    """Basic tests for journal entry autosave functionality."""

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
        self.client.login(email='test@example.com', password='testpass123')

    def test_autosave_basic_text_update(self):
        """Test basic autosave of text content."""
        url = reverse('journal_entry_autosave', kwargs={
            'trip_id': self.trip.pk,
            'entry_pk': self.entry.pk
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
            'trip_id': self.trip.pk,
            'entry_pk': self.entry.pk
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
            'trip_id': self.trip.pk,
            'entry_pk': self.entry.pk
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
            'trip_id': self.trip.pk,
            'entry_pk': self.entry.pk
        })

        data = {
            'text': '<p>Content</p>',
            'title': 'Updated Day 1 Title',
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
            'trip_id': self.trip.pk,
            'entry_pk': self.entry.pk
        })

        new_date = '2024-01-02'
        data = {
            'text': '<p>Content</p>',
            'date': new_date,
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
            'trip_id': self.trip.pk,
            'entry_pk': self.entry.pk
        })

        # Try to change entry date to Jan 2 (conflict)
        data = {
            'text': '<p>Content</p>',
            'date': '2024-01-02',
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
            'trip_id': self.trip.pk,
            'entry_pk': self.entry.pk
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
            'trip_id': self.trip.pk,
            'entry_pk': self.entry.pk
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
            'trip_id': self.trip.pk,
            'entry_pk': self.entry.pk
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
            'trip_id': self.trip.pk,
            'entry_pk': self.entry.pk
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
            'trip_id': self.trip.pk,
            'entry_pk': self.entry.pk
        })

        response = self.client.get(url)
        self.assertEqual(response.status_code, 405)


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
            'date': '2024-01-15',
            'title': 'New Title',
            'timezone': 'Europe/London',
            'reference_image_id': 42,
        }
        request_body = json.dumps(data).encode('utf-8')

        autosave_request, error = JournalAutoSaveHelper.parse_autosave_request(request_body)

        self.assertIsNone(error)
        self.assertEqual(autosave_request.text, '<p>Test</p>')
        self.assertEqual(autosave_request.client_version, 5)
        self.assertEqual(autosave_request.new_date, date(2024, 1, 15))
        self.assertEqual(autosave_request.new_title, 'New Title')
        self.assertEqual(autosave_request.new_timezone, 'Europe/London')
        self.assertEqual(autosave_request.new_reference_image_id, 42)

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
            'date': 'not-a-date',
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
