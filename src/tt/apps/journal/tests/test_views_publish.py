"""
Tests for JournalPublishModalView.

Tests the journal publishing modal view which handles:
- GET: Display publish modal with entry selection and visibility form
- POST: Execute publishing workflow with entry selection and visibility changes
"""
import logging
from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase, TransactionTestCase, Client
from django.urls import reverse

from tt.apps.journal.enums import JournalVisibility
from tt.apps.journal.models import Journal, JournalEntry
from tt.apps.travelog.models import Travelog
from tt.apps.trips.enums import TripPermissionLevel, TripStatus
from tt.apps.trips.tests.synthetic_data import TripSyntheticData

logging.disable(logging.CRITICAL)

User = get_user_model()


class JournalPublishModalViewGetTestCase(TestCase):
    """Tests for JournalPublishModalView GET request handling."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = Client()
        self.user = User.objects.create_user(
            email='admin@example.com',
            password='testpass123'
        )
        self.trip = TripSyntheticData.create_test_trip(
            user=self.user,
            title='Test Trip',
            trip_status=TripStatus.CURRENT,
        )
        self.journal = Journal.objects.create(
            trip=self.trip,
            title='Test Journal',
            timezone='UTC',
            visibility=JournalVisibility.PRIVATE,
            modified_by=self.user,
        )
        self.url = reverse('journal_publish', kwargs={'journal_uuid': self.journal.uuid})

    def test_get_returns_200_for_admin(self):
        """Test that admin users can access the publish modal."""
        self.client.force_login(self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

    def test_get_includes_required_context(self):
        """Test that GET response includes all required context fields."""
        JournalEntry.objects.create(
            journal=self.journal,
            date=date(2025, 1, 1),
            title='Day 1',
            include_in_publish=True,
            modified_by=self.user,
        )

        self.client.force_login(self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertIn('journal', response.context)
        self.assertIn('trip', response.context)
        self.assertIn('publishing_status', response.context)
        self.assertIn('visibility_form', response.context)
        self.assertIn('journal_entries', response.context)
        self.assertIn('total_entries', response.context)
        self.assertIn('included_entries', response.context)
        self.assertIn('all_entries_included', response.context)

    def test_get_correct_entry_counts(self):
        """Test that entry counts are correctly calculated."""
        JournalEntry.objects.create(
            journal=self.journal,
            date=date(2025, 1, 1),
            title='Day 1',
            include_in_publish=True,
            modified_by=self.user,
        )
        JournalEntry.objects.create(
            journal=self.journal,
            date=date(2025, 1, 2),
            title='Day 2',
            include_in_publish=False,
            modified_by=self.user,
        )
        JournalEntry.objects.create(
            journal=self.journal,
            date=date(2025, 1, 3),
            title='Day 3',
            include_in_publish=True,
            modified_by=self.user,
        )

        self.client.force_login(self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.context['total_entries'], 3)
        self.assertEqual(response.context['included_entries'], 2)
        self.assertFalse(response.context['all_entries_included'])

    def test_get_entries_ordered_by_date(self):
        """Test that journal entries are ordered by date."""
        # Created in non-chronological order to test sorting
        JournalEntry.objects.create(
            journal=self.journal,
            date=date(2025, 1, 3),
            title='Day 3',
            include_in_publish=True,
            modified_by=self.user,
        )
        JournalEntry.objects.create(
            journal=self.journal,
            date=date(2025, 1, 1),
            title='Day 1',
            include_in_publish=True,
            modified_by=self.user,
        )

        self.client.force_login(self.user)
        response = self.client.get(self.url)

        entries = response.context['journal_entries']
        self.assertEqual(entries[0].title, 'Day 1')
        self.assertEqual(entries[1].title, 'Day 3')

    def test_get_requires_login(self):
        """Test that unauthenticated users are redirected to signin."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertIn('signin', response.url)

    def test_get_non_admin_forbidden(self):
        """Test that non-admin trip members cannot access publish modal."""
        # Create a non-admin user with viewer access
        viewer = User.objects.create_user(
            email='viewer@example.com',
            password='testpass123'
        )
        TripSyntheticData.add_trip_member(
            trip=self.trip,
            user=viewer,
            permission_level=TripPermissionLevel.VIEWER,
        )

        self.client.force_login(viewer)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)


class JournalPublishModalViewPostTestCase(TransactionTestCase):
    """Tests for JournalPublishModalView POST request handling."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = Client()
        self.user = User.objects.create_user(
            email='admin@example.com',
            password='testpass123'
        )
        self.trip = TripSyntheticData.create_test_trip(
            user=self.user,
            title='Test Trip',
        )
        self.journal = Journal.objects.create(
            trip=self.trip,
            title='Test Journal',
            timezone='UTC',
            visibility=JournalVisibility.PRIVATE,
            modified_by=self.user,
        )
        self.url = reverse('journal_publish', kwargs={'journal_uuid': self.journal.uuid})

    def test_post_successful_publish(self):
        """Test successful publish workflow creates travelog."""
        entry = JournalEntry.objects.create(
            journal=self.journal,
            date=date(2025, 1, 1),
            title='Day 1',
            text='<p>Content</p>',
            include_in_publish=True,
            modified_by=self.user,
        )

        self.client.force_login(self.user)
        response = self.client.post(self.url, {
            'selected_entries': [str(entry.uuid)],
            'visibility': 'PUBLIC',
        })

        # Verify success response
        self.assertEqual(response.status_code, 200)

        # Verify travelog was created
        travelog = Travelog.objects.get(journal=self.journal, is_current=True)
        self.assertEqual(travelog.version_number, 1)
        self.assertEqual(travelog.entries.count(), 1)

        # Verify visibility was updated
        self.journal.refresh_from_db()
        self.assertEqual(self.journal.visibility, JournalVisibility.PUBLIC)

    def test_post_updates_entry_selections(self):
        """Test that POST updates include_in_publish for entries."""
        entry1 = JournalEntry.objects.create(
            journal=self.journal,
            date=date(2025, 1, 1),
            title='Day 1',
            text='<p>Content 1</p>',
            include_in_publish=False,
            modified_by=self.user,
        )
        entry2 = JournalEntry.objects.create(
            journal=self.journal,
            date=date(2025, 1, 2),
            title='Day 2',
            text='<p>Content 2</p>',
            include_in_publish=True,
            modified_by=self.user,
        )

        self.client.force_login(self.user)
        # Only select entry1
        response = self.client.post(self.url, {
            'selected_entries': [str(entry1.uuid)],
            'visibility': 'PUBLIC',
        })

        self.assertEqual(response.status_code, 200)

        entry1.refresh_from_db()
        entry2.refresh_from_db()

        self.assertTrue(entry1.include_in_publish)
        self.assertFalse(entry2.include_in_publish)

    def test_post_protected_visibility_with_password(self):
        """Test publishing with PROTECTED visibility sets password."""
        entry = JournalEntry.objects.create(
            journal=self.journal,
            date=date(2025, 1, 1),
            title='Day 1',
            text='<p>Content</p>',
            include_in_publish=True,
            modified_by=self.user,
        )

        self.client.force_login(self.user)
        response = self.client.post(self.url, {
            'selected_entries': [str(entry.uuid)],
            'visibility': 'PROTECTED',
            'password_action': 'SET_NEW',
            'password': 'secret123',
            'password_confirm': 'secret123',
        })

        self.assertEqual(response.status_code, 200)

        self.journal.refresh_from_db()
        self.assertEqual(self.journal.visibility, JournalVisibility.PROTECTED)
        self.assertTrue(self.journal.check_password('secret123'))

    def test_post_no_entries_selected_returns_error(self):
        """Test that publishing with no selected entries returns error."""
        # Create an entry that exists but won't be selected
        JournalEntry.objects.create(
            journal=self.journal,
            date=date(2025, 1, 1),
            title='Day 1',
            text='<p>Content</p>',
            include_in_publish=True,
            modified_by=self.user,
        )

        self.client.force_login(self.user)
        # Send empty selection - should fail
        response = self.client.post(self.url, {
            'selected_entries': [],
            'visibility': 'PUBLIC',
        })

        # Should return 400 with error
        self.assertEqual(response.status_code, 400)

        # No travelog should be created
        self.assertFalse(Travelog.objects.filter(journal=self.journal).exists())

    def test_post_invalid_form_returns_400(self):
        """Test that invalid form data returns 400 with context."""
        entry = JournalEntry.objects.create(
            journal=self.journal,
            date=date(2025, 1, 1),
            title='Day 1',
            text='<p>Content</p>',
            include_in_publish=True,
            modified_by=self.user,
        )

        self.client.force_login(self.user)
        # Send PROTECTED without password - should fail validation
        response = self.client.post(self.url, {
            'selected_entries': [str(entry.uuid)],  # noqa: F841 (used in POST)
            'visibility': 'PROTECTED',
            'password_action': 'SET_NEW',
            # Missing password fields
        })

        self.assertEqual(response.status_code, 400)

        # Context should include all fields for re-display
        self.assertIn('journal', response.context)
        self.assertIn('visibility_form', response.context)
        self.assertIn('journal_entries', response.context)

    def test_post_selective_publishing(self):
        """Test that only selected entries are published to travelog."""
        entry1 = JournalEntry.objects.create(
            journal=self.journal,
            date=date(2025, 1, 1),
            title='Day 1',
            text='<p>Content 1</p>',
            include_in_publish=True,
            modified_by=self.user,
        )
        # Create entry2 but don't select it - should be excluded from travelog
        JournalEntry.objects.create(
            journal=self.journal,
            date=date(2025, 1, 2),
            title='Day 2',
            text='<p>Content 2</p>',
            include_in_publish=True,
            modified_by=self.user,
        )
        entry3 = JournalEntry.objects.create(
            journal=self.journal,
            date=date(2025, 1, 3),
            title='Day 3',
            text='<p>Content 3</p>',
            include_in_publish=True,
            modified_by=self.user,
        )

        self.client.force_login(self.user)
        # Only select entries 1 and 3 - entry2 should be excluded
        response = self.client.post(self.url, {
            'selected_entries': [str(entry1.uuid), str(entry3.uuid)],
            'visibility': 'PUBLIC',
        })

        self.assertEqual(response.status_code, 200)

        # Verify travelog has only 2 entries
        travelog = Travelog.objects.get(journal=self.journal, is_current=True)
        self.assertEqual(travelog.entries.count(), 2)

        # Verify which entries are in travelog
        travelog_entry_titles = set(
            travelog.entries.values_list('title', flat=True)
        )
        self.assertEqual(travelog_entry_titles, {'Day 1', 'Day 3'})

    def test_post_requires_admin_access(self):
        """Test that non-admin users cannot publish."""
        entry = JournalEntry.objects.create(
            journal=self.journal,
            date=date(2025, 1, 1),
            title='Day 1',
            text='<p>Content</p>',
            include_in_publish=True,
            modified_by=self.user,
        )

        # Create a non-admin user with editor access
        editor = User.objects.create_user(
            email='editor@example.com',
            password='testpass123'
        )
        TripSyntheticData.add_trip_member(
            trip=self.trip,
            user=editor,
            permission_level=TripPermissionLevel.EDITOR,
        )

        self.client.force_login(editor)
        response = self.client.post(self.url, {
            'selected_entries': [str(entry.uuid)],
            'visibility': 'PUBLIC',
        })

        self.assertEqual(response.status_code, 403)

        # No travelog should be created
        self.assertFalse(Travelog.objects.filter(journal=self.journal).exists())
