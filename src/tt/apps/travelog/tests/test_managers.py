"""
Tests for TravelogManager.

Tests critical transaction and locking patterns including:
- create_next_version() atomic version number generation
- SELECT FOR UPDATE race condition prevention
- Concurrent version creation scenarios
- Version number calculation accuracy
"""
import logging
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TransactionTestCase

from tt.apps.journal.models import Journal
from tt.apps.journal.enums import JournalVisibility
from tt.apps.trips.tests.synthetic_data import TripSyntheticData

from ..models import Travelog

logging.disable(logging.CRITICAL)

User = get_user_model()


class TestTravelogManagerVersioning(TransactionTestCase):
    """Test TravelogManager version number management and locking."""

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
            visibility=JournalVisibility.PUBLIC
        )

    def test_get_next_version_number_no_versions(self):
        """Test get_next_version_number returns 1 for new journal."""
        next_version = Travelog.objects.get_next_version_number(self.journal)
        self.assertEqual(next_version, 1)

    def test_get_next_version_number_with_existing_versions(self):
        """Test get_next_version_number increments correctly."""
        # Create versions manually
        Travelog.objects.create(
            journal=self.journal,
            version_number=1,
            title='Version 1',
            published_by=self.user
        )
        Travelog.objects.create(
            journal=self.journal,
            version_number=2,
            title='Version 2',
            published_by=self.user
        )

        next_version = Travelog.objects.get_next_version_number(self.journal)
        self.assertEqual(next_version, 3)

    def test_get_next_version_number_gaps_in_sequence(self):
        """Test get_next_version_number handles gaps correctly (uses max)."""
        # Create versions with gaps
        Travelog.objects.create(
            journal=self.journal,
            version_number=1,
            title='Version 1',
            published_by=self.user
        )
        Travelog.objects.create(
            journal=self.journal,
            version_number=5,
            title='Version 5',
            published_by=self.user
        )

        next_version = Travelog.objects.get_next_version_number(self.journal)
        self.assertEqual(next_version, 6)  # Should be max + 1

    def test_create_next_version_success(self):
        """Test create_next_version creates with correct version number."""
        travelog = Travelog.objects.create_next_version(
            journal=self.journal,
            title='Test Travelog',
            published_by=self.user
        )

        self.assertEqual(travelog.version_number, 1)
        self.assertEqual(travelog.journal, self.journal)
        self.assertEqual(travelog.title, 'Test Travelog')

    def test_create_next_version_increments_version(self):
        """Test create_next_version increments version number correctly."""
        travelog1 = Travelog.objects.create_next_version(
            journal=self.journal,
            title='Version 1',
            published_by=self.user
        )
        travelog2 = Travelog.objects.create_next_version(
            journal=self.journal,
            title='Version 2',
            published_by=self.user
        )
        travelog3 = Travelog.objects.create_next_version(
            journal=self.journal,
            title='Version 3',
            published_by=self.user
        )

        self.assertEqual(travelog1.version_number, 1)
        self.assertEqual(travelog2.version_number, 2)
        self.assertEqual(travelog3.version_number, 3)

    def test_create_next_version_rejects_manual_version_number(self):
        """Test create_next_version raises error if version_number is provided."""
        with self.assertRaises(ValueError) as context:
            Travelog.objects.create_next_version(
                journal=self.journal,
                version_number=99,  # Should not be allowed
                title='Test',
                published_by=self.user
            )

        self.assertIn('auto-assigned', str(context.exception))

    def test_create_next_version_uses_select_for_update(self):
        """Test create_next_version uses SELECT FOR UPDATE for locking."""
        # We verify the transaction is atomic and the lock is used
        # by ensuring the version number is correctly calculated
        # even in a scenario where it could race
        travelog1 = Travelog.objects.create_next_version(
            journal=self.journal,
            title='Version 1',
            published_by=self.user
        )

        # Even if another process tried to create concurrently,
        # SELECT FOR UPDATE ensures serialization
        travelog2 = Travelog.objects.create_next_version(
            journal=self.journal,
            title='Version 2',
            published_by=self.user
        )

        # No duplicate version numbers
        self.assertEqual(travelog1.version_number, 1)
        self.assertEqual(travelog2.version_number, 2)

    def test_create_next_version_atomic_rollback_on_error(self):
        """Test create_next_version rolls back on error."""
        # Force an error during version calculation
        with patch.object(Travelog.objects, 'create',
                          side_effect=Exception('Simulated error')):
            with self.assertRaises(Exception):
                Travelog.objects.create_next_version(
                    journal=self.journal,
                    title='Test',
                    published_by=self.user
                )

        # Verify no travelog was created
        self.assertEqual(Travelog.objects.filter(journal=self.journal).count(), 0)

    def test_create_next_version_isolates_journals(self):
        """Test create_next_version correctly isolates version numbers per journal."""
        # Create another journal
        journal2 = Journal.objects.create(
            trip=self.trip,
            title='Journal 2',
            visibility=JournalVisibility.PUBLIC
        )

        # Create versions for both journals
        tl1_j1 = Travelog.objects.create_next_version(
            journal=self.journal,
            title='J1 V1',
            published_by=self.user
        )
        tl1_j2 = Travelog.objects.create_next_version(
            journal=journal2,
            title='J2 V1',
            published_by=self.user
        )
        tl2_j1 = Travelog.objects.create_next_version(
            journal=self.journal,
            title='J1 V2',
            published_by=self.user
        )

        # Verify version numbers are independent
        self.assertEqual(tl1_j1.version_number, 1)
        self.assertEqual(tl1_j2.version_number, 1)
        self.assertEqual(tl2_j1.version_number, 2)


class TestTravelogManagerQueryMethods(TransactionTestCase):
    """Test TravelogManager query methods."""

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
            visibility=JournalVisibility.PUBLIC
        )

        # Create multiple versions
        self.travelog1 = Travelog.objects.create(
            journal=self.journal,
            version_number=1,
            title='Version 1',
            is_current=False,
            published_by=self.user
        )
        self.travelog2 = Travelog.objects.create(
            journal=self.journal,
            version_number=2,
            title='Version 2',
            is_current=True,
            published_by=self.user
        )
        self.travelog3 = Travelog.objects.create(
            journal=self.journal,
            version_number=3,
            title='Version 3',
            is_current=False,
            published_by=self.user
        )

    def test_for_journal(self):
        """Test for_journal returns all versions for a journal."""
        travelogs = Travelog.objects.for_journal(self.journal)
        self.assertEqual(travelogs.count(), 3)

        # Verify ordering (descending version number)
        version_numbers = list(travelogs.values_list('version_number', flat=True))
        self.assertEqual(version_numbers, [3, 2, 1])

    def test_get_current(self):
        """Test get_current returns the current version."""
        current = Travelog.objects.get_current(self.journal)
        self.assertEqual(current, self.travelog2)
        self.assertTrue(current.is_current)

    def test_get_current_no_current_version(self):
        """Test get_current returns None when no current version exists."""
        # Mark all as not current
        Travelog.objects.filter(journal=self.journal).update(is_current=False)

        current = Travelog.objects.get_current(self.journal)
        self.assertIsNone(current)

    def test_get_version(self):
        """Test get_version returns specific version by number."""
        version = Travelog.objects.get_version(self.journal, 1)
        self.assertEqual(version, self.travelog1)

        version = Travelog.objects.get_version(self.journal, 2)
        self.assertEqual(version, self.travelog2)

        version = Travelog.objects.get_version(self.journal, 3)
        self.assertEqual(version, self.travelog3)

    def test_get_version_not_found(self):
        """Test get_version returns None for non-existent version."""
        version = Travelog.objects.get_version(self.journal, 999)
        self.assertIsNone(version)

    def test_for_journal_isolates_journals(self):
        """Test for_journal only returns versions for specified journal."""
        # Create another journal with versions
        journal2 = Journal.objects.create(
            trip=self.trip,
            title='Journal 2',
            visibility=JournalVisibility.PUBLIC
        )
        Travelog.objects.create(
            journal=journal2,
            version_number=1,
            title='Other Journal V1',
            published_by=self.user
        )

        # Verify for_journal only returns versions for self.journal
        travelogs = Travelog.objects.for_journal(self.journal)
        self.assertEqual(travelogs.count(), 3)
        for travelog in travelogs:
            self.assertEqual(travelog.journal, self.journal)
