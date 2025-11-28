"""
Tests for journal publishing helper classes.

Tests EntrySelectionStats and JournalPublishContextBuilder which centralize
publishing-related context building and entry selection statistics.
"""
import logging
from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from tt.apps.journal.enums import JournalVisibility
from tt.apps.journal.models import Journal, JournalEntry
from tt.apps.journal.schemas import EntrySelectionStats
from tt.apps.trips.enums import TripStatus
from tt.apps.trips.tests.synthetic_data import TripSyntheticData

logging.disable(logging.CRITICAL)

User = get_user_model()


class TestEntrySelectionStats(TestCase):
    """Tests for EntrySelectionStats dataclass and calculations."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(
            email='test@example.com',
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

    def test_for_journal_empty_journal(self):
        """Test statistics for journal with no entries."""
        stats = EntrySelectionStats.for_journal(self.journal)

        self.assertEqual(stats.total_entries, 0)
        self.assertEqual(stats.included_entries, 0)
        self.assertEqual(stats.excluded_entries, 0)
        self.assertTrue(stats.all_entries_included)  # vacuous truth: 0/0
        self.assertTrue(stats.none_included)

    def test_for_journal_all_included(self):
        """Test statistics when all entries are included."""
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
            include_in_publish=True,
            modified_by=self.user,
        )

        stats = EntrySelectionStats.for_journal(self.journal)

        self.assertEqual(stats.total_entries, 2)
        self.assertEqual(stats.included_entries, 2)
        self.assertEqual(stats.excluded_entries, 0)
        self.assertTrue(stats.all_entries_included)
        self.assertFalse(stats.none_included)

    def test_for_journal_none_included(self):
        """Test statistics when no entries are included."""
        JournalEntry.objects.create(
            journal=self.journal,
            date=date(2025, 1, 1),
            title='Day 1',
            include_in_publish=False,
            modified_by=self.user,
        )
        JournalEntry.objects.create(
            journal=self.journal,
            date=date(2025, 1, 2),
            title='Day 2',
            include_in_publish=False,
            modified_by=self.user,
        )

        stats = EntrySelectionStats.for_journal(self.journal)

        self.assertEqual(stats.total_entries, 2)
        self.assertEqual(stats.included_entries, 0)
        self.assertEqual(stats.excluded_entries, 2)
        self.assertFalse(stats.all_entries_included)
        self.assertTrue(stats.none_included)

    def test_for_journal_partial_inclusion(self):
        """Test statistics with some entries included."""
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

        stats = EntrySelectionStats.for_journal(self.journal)

        self.assertEqual(stats.total_entries, 3)
        self.assertEqual(stats.included_entries, 2)
        self.assertEqual(stats.excluded_entries, 1)
        self.assertFalse(stats.all_entries_included)
        self.assertFalse(stats.none_included)
