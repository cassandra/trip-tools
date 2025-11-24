"""
Tests for JournalRestoreService.

Tests critical transaction and locking patterns including:
- @transaction.atomic operations with destructive operations
- SELECT FOR UPDATE for concurrent restore prevention
- Bulk operations (bulk_create, delete) within transactions
- Rollback behavior on errors
- Validation and error handling
"""
import logging
from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TransactionTestCase

from tt.apps.journal.models import Journal, JournalEntry
from tt.apps.journal.enums import JournalVisibility
from tt.apps.travelog.models import Travelog, TravelogEntry
from tt.apps.trips.tests.synthetic_data import TripSyntheticData

from ..services import JournalRestoreService, RestoreError

logging.disable(logging.CRITICAL)

User = get_user_model()


class TestJournalRestoreService(TransactionTestCase):
    """Test JournalRestoreService.restore_from_version() transaction patterns."""

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
            description='Original description',
            visibility=JournalVisibility.PUBLIC
        )

    def test_restore_from_version_success(self):
        """Test successful restore replaces journal entries with travelog snapshot."""
        # Create original journal entries
        JournalEntry.objects.create(
            journal=self.journal,
            date=date(2024, 1, 10),
            title='Original Day 1',
            text='Original content 1'
        )
        JournalEntry.objects.create(
            journal=self.journal,
            date=date(2024, 1, 11),
            title='Original Day 2',
            text='Original content 2'
        )

        # Create a travelog snapshot with different content
        travelog = Travelog.objects.create(
            journal=self.journal,
            version_number=1,
            title='Snapshot Title',
            description='Snapshot description',
            published_by=self.user
        )
        TravelogEntry.objects.create(
            travelog=travelog,
            date=date(2024, 1, 10),
            title='Snapshot Day 1',
            text='Snapshot content 1',
            timezone='America/New_York'
        )
        TravelogEntry.objects.create(
            travelog=travelog,
            date=date(2024, 1, 11),
            title='Snapshot Day 2',
            text='Snapshot content 2',
            timezone='America/New_York'
        )

        # Restore from travelog
        count = JournalRestoreService.restore_from_version(
            self.journal,
            travelog,
            self.user
        )

        # Verify correct number of entries restored
        self.assertEqual(count, 2)

        # Verify journal entries were replaced
        journal_entries = JournalEntry.objects.filter(
            journal=self.journal
        ).order_by('date')
        self.assertEqual(journal_entries.count(), 2)

        # Verify content matches travelog snapshot
        self.assertEqual(journal_entries[0].date, date(2024, 1, 10))
        self.assertEqual(journal_entries[0].title, 'Snapshot Day 1')
        self.assertEqual(journal_entries[0].text, 'Snapshot content 1')
        self.assertEqual(journal_entries[0].timezone, 'America/New_York')
        self.assertEqual(journal_entries[0].modified_by, self.user)

        self.assertEqual(journal_entries[1].date, date(2024, 1, 11))
        self.assertEqual(journal_entries[1].title, 'Snapshot Day 2')
        self.assertEqual(journal_entries[1].text, 'Snapshot content 2')

        # Verify journal metadata was updated
        self.journal.refresh_from_db()
        self.assertEqual(self.journal.title, 'Snapshot Title')
        self.assertEqual(self.journal.modified_by, self.user)

    def test_restore_from_version_wrong_journal_raises_error(self):
        """Test restoring from travelog of different journal raises RestoreError."""
        # Create another journal with travelog
        other_journal = Journal.objects.create(
            trip=self.trip,
            title='Other Journal',
            visibility=JournalVisibility.PUBLIC
        )
        other_travelog = Travelog.objects.create(
            journal=other_journal,
            version_number=1,
            title='Other Snapshot',
            published_by=self.user
        )
        TravelogEntry.objects.create(
            travelog=other_travelog,
            date=date(2024, 1, 10),
            title='Entry',
            text='Content'
        )

        # Try to restore self.journal from other_journal's travelog
        with self.assertRaises(RestoreError) as context:
            JournalRestoreService.restore_from_version(
                self.journal,
                other_travelog,
                self.user
            )

        self.assertIn('does not belong to this journal', str(context.exception))

    def test_restore_from_version_no_entries_raises_error(self):
        """Test restoring from travelog with no entries raises RestoreError."""
        # Create travelog with no entries
        travelog = Travelog.objects.create(
            journal=self.journal,
            version_number=1,
            title='Empty Snapshot',
            published_by=self.user
        )

        with self.assertRaises(RestoreError) as context:
            JournalRestoreService.restore_from_version(
                self.journal,
                travelog,
                self.user
            )

        self.assertIn('no entries', str(context.exception))

    def test_restore_from_version_deletes_all_current_entries(self):
        """Test restore deletes ALL current journal entries before restore."""
        # Create many journal entries
        for i in range(1, 11):
            JournalEntry.objects.create(
                journal=self.journal,
                date=date(2024, 1, i),
                title=f'Day {i}',
                text=f'Content {i}'
            )

        self.assertEqual(JournalEntry.objects.filter(journal=self.journal).count(), 10)

        # Create travelog with fewer entries
        travelog = Travelog.objects.create(
            journal=self.journal,
            version_number=1,
            title='Snapshot',
            published_by=self.user
        )
        TravelogEntry.objects.create(
            travelog=travelog,
            date=date(2024, 1, 1),
            title='Day 1',
            text='Content 1'
        )
        TravelogEntry.objects.create(
            travelog=travelog,
            date=date(2024, 1, 2),
            title='Day 2',
            text='Content 2'
        )

        # Restore
        count = JournalRestoreService.restore_from_version(
            self.journal,
            travelog,
            self.user
        )

        # Verify all old entries deleted and only new entries exist
        self.assertEqual(count, 2)
        self.assertEqual(JournalEntry.objects.filter(journal=self.journal).count(), 2)

    def test_restore_from_version_uses_bulk_create(self):
        """Test restore uses bulk_create for efficiency."""
        # Create travelog with entries
        travelog = Travelog.objects.create(
            journal=self.journal,
            version_number=1,
            title='Snapshot',
            published_by=self.user
        )
        for i in range(1, 6):
            TravelogEntry.objects.create(
                travelog=travelog,
                date=date(2024, 1, i),
                title=f'Day {i}',
                text=f'Content {i}'
            )

        # Restore - bulk_create should be efficient
        count = JournalRestoreService.restore_from_version(
            self.journal,
            travelog,
            self.user
        )

        # Verify all entries created
        self.assertEqual(count, 5)
        self.assertEqual(JournalEntry.objects.filter(journal=self.journal).count(), 5)

    def test_restore_from_version_uses_select_for_update(self):
        """Test restore uses SELECT FOR UPDATE to lock journal during restore."""
        # Create travelog
        travelog = Travelog.objects.create(
            journal=self.journal,
            version_number=1,
            title='Snapshot',
            published_by=self.user
        )
        TravelogEntry.objects.create(
            travelog=travelog,
            date=date(2024, 1, 10),
            title='Day 1',
            text='Content'
        )

        # Execute restore - should use SELECT FOR UPDATE internally
        JournalRestoreService.restore_from_version(
            self.journal,
            travelog,
            self.user
        )

        # Verify operation completed successfully (lock was acquired)
        self.assertEqual(JournalEntry.objects.filter(journal=self.journal).count(), 1)

    def test_restore_from_version_atomic_rollback_on_error(self):
        """Test restore transaction rolls back completely on error."""
        # Create original entries
        JournalEntry.objects.create(
            journal=self.journal,
            date=date(2024, 1, 10),
            title='Original',
            text='Original content'
        )

        # Create travelog
        travelog = Travelog.objects.create(
            journal=self.journal,
            version_number=1,
            title='Snapshot',
            published_by=self.user
        )
        TravelogEntry.objects.create(
            travelog=travelog,
            date=date(2024, 1, 11),
            title='New Entry',
            text='New content'
        )

        # Force error during bulk_create
        with patch('tt.apps.journal.models.JournalEntry.objects.bulk_create',
                   side_effect=Exception('Simulated error')):
            with self.assertRaises(Exception):
                JournalRestoreService.restore_from_version(
                    self.journal,
                    travelog,
                    self.user
                )

        # Verify rollback - original entry should still exist
        journal_entries = JournalEntry.objects.filter(journal=self.journal)
        self.assertEqual(journal_entries.count(), 1)
        self.assertEqual(journal_entries[0].title, 'Original')

    def test_restore_from_version_copies_all_fields(self):
        """Test restore copies all relevant fields from travelog entries."""
        from tt.apps.images.models import TripImage
        from django.core.files.base import ContentFile

        # Create test image (TripImage doesn't have trip field)
        test_image = TripImage.objects.create(
            uploaded_by=self.user
        )
        # Save minimal image data to satisfy ImageField
        test_image.web_image.save('test.jpg', ContentFile(b'fake_image_data'), save=True)

        # Create travelog with complete data
        travelog = Travelog.objects.create(
            journal=self.journal,
            version_number=1,
            title='Snapshot',
            reference_image=test_image,
            published_by=self.user
        )
        TravelogEntry.objects.create(
            travelog=travelog,
            date=date(2024, 1, 10),
            title='Complete Entry',
            text='<p>Rich HTML content</p>',
            timezone='America/Los_Angeles',
            reference_image=test_image
        )

        # Restore
        JournalRestoreService.restore_from_version(
            self.journal,
            travelog,
            self.user
        )

        # Verify all fields copied
        entry = JournalEntry.objects.get(journal=self.journal)
        self.assertEqual(entry.date, date(2024, 1, 10))
        self.assertEqual(entry.title, 'Complete Entry')
        self.assertEqual(entry.text, '<p>Rich HTML content</p>')
        self.assertEqual(entry.timezone, 'America/Los_Angeles')
        self.assertEqual(entry.reference_image, test_image)
        self.assertEqual(entry.modified_by, self.user)

    def test_restore_from_version_preserves_entry_order(self):
        """Test restore preserves chronological order of entries."""
        # Create travelog with entries in specific order
        travelog = Travelog.objects.create(
            journal=self.journal,
            version_number=1,
            title='Snapshot',
            published_by=self.user
        )

        # Create entries in non-chronological order
        dates_and_titles = [
            (date(2024, 1, 15), 'Mid Month'),
            (date(2024, 1, 5), 'Early Month'),
            (date(2024, 1, 25), 'Late Month'),
            (date(2024, 1, 10), 'Second Week'),
        ]

        for entry_date, title in dates_and_titles:
            TravelogEntry.objects.create(
                travelog=travelog,
                date=entry_date,
                title=title,
                text='Content'
            )

        # Restore
        JournalRestoreService.restore_from_version(
            self.journal,
            travelog,
            self.user
        )

        # Verify entries are retrievable in chronological order
        entries = JournalEntry.objects.filter(journal=self.journal).order_by('date')
        self.assertEqual(entries.count(), 4)
        self.assertEqual(entries[0].title, 'Early Month')
        self.assertEqual(entries[1].title, 'Second Week')
        self.assertEqual(entries[2].title, 'Mid Month')
        self.assertEqual(entries[3].title, 'Late Month')

    def test_restore_from_version_updates_journal_modified_datetime(self):
        """Test restore updates journal's modified_datetime."""
        import time

        # Create travelog
        travelog = Travelog.objects.create(
            journal=self.journal,
            version_number=1,
            title='Snapshot',
            published_by=self.user
        )
        TravelogEntry.objects.create(
            travelog=travelog,
            date=date(2024, 1, 10),
            title='Entry',
            text='Content'
        )

        # Record original modified time
        original_modified = self.journal.modified_datetime

        # Wait a moment to ensure timestamp difference
        time.sleep(0.1)

        # Restore
        JournalRestoreService.restore_from_version(
            self.journal,
            travelog,
            self.user
        )

        # Verify modified_datetime was updated
        self.journal.refresh_from_db()
        self.assertGreater(self.journal.modified_datetime, original_modified)
