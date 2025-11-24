"""
Integration tests for publishing status in JournalView.

Tests that the JournalView correctly provides publishing status context
to templates for displaying current published version and unpublished changes.
"""
import logging
from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

from tt.apps.journal.models import Journal, JournalEntry
from tt.apps.journal.enums import JournalVisibility
from tt.apps.trips.enums import TripStatus
from tt.apps.trips.tests.synthetic_data import TripSyntheticData
from tt.apps.travelog.models import Travelog, TravelogEntry

logging.disable(logging.CRITICAL)

User = get_user_model()


class JournalViewPublishingStatusTestCase(TestCase):
    """Tests for publishing status context in JournalView."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = Client()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.trip = TripSyntheticData.create_test_trip(
            user=self.user,
            title='Test Trip',
            description='A test trip',
            trip_status=TripStatus.CURRENT,
        )
        self.journal = Journal.objects.create(
            trip=self.trip,
            title='Test Journal',
            description='A test journal',
            timezone='UTC',
            visibility=JournalVisibility.PRIVATE,
            modified_by=self.user,
        )

    def test_unpublished_journal_context(self):
        """Test that unpublished journal provides correct context."""
        self.client.force_login(self.user)
        url = reverse('journal', kwargs={'journal_uuid': self.journal.uuid})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

        # Check context variables
        publishing_status = response.context['publishing_status']
        self.assertIsNone(publishing_status.current_published_version)
        self.assertFalse(publishing_status.has_unpublished_changes)
        self.assertFalse(publishing_status.has_published_version)

    def test_published_journal_no_changes_context(self):
        """Test that published journal with no changes provides correct context."""
        # Create and publish journal entry
        entry = JournalEntry.objects.create(
            journal=self.journal,
            date=date(2025, 1, 1),
            title='Day 1',
            text='<p>First day content</p>',
            timezone='UTC',
            modified_by=self.user,
        )

        travelog = Travelog.objects.create(
            journal=self.journal,
            version_number=1,
            is_current=True,
            title=self.journal.title,
            description=self.journal.description,
            published_by=self.user,
        )
        TravelogEntry.objects.create(
            travelog=travelog,
            source_entry=entry,
            date=entry.date,
            title=entry.title,
            text=entry.text,
            timezone=entry.timezone,
        )

        self.client.force_login(self.user)
        url = reverse('journal', kwargs={'journal_uuid': self.journal.uuid})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

        # Check context variables
        publishing_status = response.context['publishing_status']
        self.assertEqual(publishing_status.current_published_version, travelog)
        self.assertFalse(publishing_status.has_unpublished_changes)
        self.assertTrue(publishing_status.has_published_version)

    def test_published_journal_with_changes_context(self):
        """Test that published journal with changes provides correct context."""
        # Create and publish journal entry
        entry = JournalEntry.objects.create(
            journal=self.journal,
            date=date(2025, 1, 1),
            title='Day 1',
            text='<p>Original content</p>',
            timezone='UTC',
            modified_by=self.user,
        )

        travelog = Travelog.objects.create(
            journal=self.journal,
            version_number=1,
            is_current=True,
            title=self.journal.title,
            description=self.journal.description,
            published_by=self.user,
        )
        TravelogEntry.objects.create(
            travelog=travelog,
            source_entry=entry,
            date=entry.date,
            title=entry.title,
            text=entry.text,
            timezone=entry.timezone,
        )

        # Modify the entry
        entry.text = '<p>Modified content</p>'
        entry.save()

        self.client.force_login(self.user)
        url = reverse('journal', kwargs={'journal_uuid': self.journal.uuid})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

        # Check context variables
        publishing_status = response.context['publishing_status']
        self.assertEqual(publishing_status.current_published_version, travelog)
        self.assertTrue(publishing_status.has_unpublished_changes)
        self.assertTrue(publishing_status.has_published_version)

    def test_published_journal_with_new_entry_context(self):
        """Test that published journal with new entry shows correct count."""
        # Create and publish one entry
        entry1 = JournalEntry.objects.create(
            journal=self.journal,
            date=date(2025, 1, 1),
            title='Day 1',
            text='<p>First day</p>',
            timezone='UTC',
            modified_by=self.user,
        )

        travelog = Travelog.objects.create(
            journal=self.journal,
            version_number=1,
            is_current=True,
            title=self.journal.title,
            description=self.journal.description,
            published_by=self.user,
        )
        TravelogEntry.objects.create(
            travelog=travelog,
            source_entry=entry1,
            date=entry1.date,
            title=entry1.title,
            text=entry1.text,
            timezone=entry1.timezone,
        )

        # Add new entry
        JournalEntry.objects.create(
            journal=self.journal,
            date=date(2025, 1, 2),
            title='Day 2',
            text='<p>Second day</p>',
            timezone='UTC',
            modified_by=self.user,
        )

        self.client.force_login(self.user)
        url = reverse('journal', kwargs={'journal_uuid': self.journal.uuid})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

        # Check context variables
        publishing_status = response.context['publishing_status']
        self.assertEqual(publishing_status.current_published_version, travelog)
        self.assertTrue(publishing_status.has_unpublished_changes)
        self.assertTrue(publishing_status.has_published_version)
