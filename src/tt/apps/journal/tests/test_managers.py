"""
Tests for Journal and JournalEntry manager methods.

Tests focus on:
- Primary journal pattern (get_primary_for_trip)
- Journal filtering by trip (for_trip)
- Entry filtering by journal (for_journal)
- Ordering and retrieval patterns
- Edge cases (no journals, multiple journals)
- CASCADE deletion behavior
"""
import logging

from django.contrib.auth import get_user_model
from django.test import TestCase

from tt.apps.journal.enums import JournalVisibility
from tt.apps.journal.models import Journal, JournalEntry
from tt.apps.trips.tests.synthetic_data import TripSyntheticData

logging.disable(logging.CRITICAL)

User = get_user_model()


class JournalManagerForTripTestCase(TestCase):
    """Test JournalManager.for_trip filtering."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(email='user@test.com', password='pass')
        cls.trip = TripSyntheticData.create_test_trip(user=cls.user, title='Test Trip')

    def test_for_trip_returns_trip_journals(self):
        """for_trip should return all journals for the specified trip."""
        journal1 = Journal.objects.create(
            trip=self.trip,
            title='Journal 1',
            visibility=JournalVisibility.PRIVATE,
            timezone='UTC',
        )
        journal2 = Journal.objects.create(
            trip=self.trip,
            title='Journal 2',
            visibility=JournalVisibility.PUBLIC,
            timezone='America/New_York',
        )

        journals = Journal.objects.for_trip(self.trip)

        self.assertEqual(journals.count(), 2)
        self.assertIn(journal1, journals)
        self.assertIn(journal2, journals)

    def test_for_trip_excludes_other_trip_journals(self):
        """for_trip should not return journals from other trips."""
        trip2 = TripSyntheticData.create_test_trip(user=self.user, title='Other Trip')

        journal1 = Journal.objects.create(trip=self.trip, title='Trip 1 Journal', visibility=JournalVisibility.PRIVATE, timezone='UTC')
        journal2 = Journal.objects.create(trip=trip2, title='Trip 2 Journal', visibility=JournalVisibility.PRIVATE, timezone='UTC')

        trip1_journals = Journal.objects.for_trip(self.trip)

        self.assertEqual(trip1_journals.count(), 1)
        self.assertIn(journal1, trip1_journals)
        self.assertNotIn(journal2, trip1_journals)

    def test_for_trip_empty_for_trip_without_journals(self):
        """for_trip should return empty queryset for trips with no journals."""
        journals = Journal.objects.for_trip(self.trip)
        self.assertEqual(journals.count(), 0)

    def test_for_trip_returns_queryset(self):
        """for_trip should return a QuerySet (not a single object)."""
        Journal.objects.create(trip=self.trip, title='Journal', visibility=JournalVisibility.PRIVATE, timezone='UTC')

        journals = Journal.objects.for_trip(self.trip)

        # Should be a QuerySet
        self.assertTrue(hasattr(journals, 'count'))
        self.assertTrue(hasattr(journals, 'filter'))

    def test_for_trip_ordering(self):
        """for_trip should return journals in created_datetime descending order."""
        # Create journals in sequence (created_datetime auto-increments)
        journal1 = Journal.objects.create(trip=self.trip, title='First', visibility=JournalVisibility.PRIVATE, timezone='UTC')
        journal2 = Journal.objects.create(trip=self.trip, title='Second', visibility=JournalVisibility.PRIVATE, timezone='UTC')
        journal3 = Journal.objects.create(trip=self.trip, title='Third', visibility=JournalVisibility.PRIVATE, timezone='UTC')

        journals = Journal.objects.for_trip(self.trip)

        # Should be ordered newest first (Meta.ordering = ['-created_datetime'])
        journal_list = list(journals)
        self.assertEqual(journal_list[0], journal3)
        self.assertEqual(journal_list[1], journal2)
        self.assertEqual(journal_list[2], journal1)


class JournalManagerGetPrimaryForTripTestCase(TestCase):
    """Test JournalManager.get_primary_for_trip - MVP single journal pattern."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(email='user@test.com', password='pass')
        cls.trip = TripSyntheticData.create_test_trip(user=cls.user, title='Test Trip')

    def test_get_primary_returns_first_journal(self):
        """get_primary_for_trip should return the first (oldest) journal."""
        journal1 = Journal.objects.create(trip=self.trip, title='First', visibility=JournalVisibility.PRIVATE, timezone='UTC')
        Journal.objects.create(trip=self.trip, title='Second', visibility=JournalVisibility.PRIVATE, timezone='UTC')

        primary = Journal.objects.get_primary_for_trip(self.trip)

        # Should return the first created journal
        self.assertEqual(primary, journal1)

    def test_get_primary_returns_none_when_no_journals(self):
        """get_primary_for_trip should return None when trip has no journals."""
        primary = Journal.objects.get_primary_for_trip(self.trip)
        self.assertIsNone(primary)

    def test_get_primary_single_journal(self):
        """get_primary_for_trip should return the only journal if just one exists."""
        journal = Journal.objects.create(trip=self.trip, title='Only Journal', visibility=JournalVisibility.PRIVATE, timezone='UTC')

        primary = Journal.objects.get_primary_for_trip(self.trip)

        self.assertEqual(primary, journal)

    def test_get_primary_consistent_across_calls(self):
        """get_primary_for_trip should return same journal across multiple calls."""
        Journal.objects.create(trip=self.trip, title='Journal 1', visibility=JournalVisibility.PRIVATE, timezone='UTC')
        Journal.objects.create(trip=self.trip, title='Journal 2', visibility=JournalVisibility.PRIVATE, timezone='UTC')

        primary1 = Journal.objects.get_primary_for_trip(self.trip)
        primary2 = Journal.objects.get_primary_for_trip(self.trip)

        self.assertEqual(primary1, primary2)

    def test_get_primary_orders_by_created_datetime(self):
        """get_primary_for_trip should use created_datetime ordering."""
        # Create journals (created_datetime auto-set)
        oldest = Journal.objects.create(trip=self.trip, title='Oldest', visibility=JournalVisibility.PRIVATE, timezone='UTC')
        Journal.objects.create(trip=self.trip, title='Middle', visibility=JournalVisibility.PRIVATE, timezone='UTC')
        Journal.objects.create(trip=self.trip, title='Newest', visibility=JournalVisibility.PRIVATE, timezone='UTC')

        primary = Journal.objects.get_primary_for_trip(self.trip)

        # Should return the oldest (first created)
        self.assertEqual(primary, oldest)

    def test_get_primary_different_trips_isolated(self):
        """get_primary_for_trip should isolate journals by trip."""
        trip2 = TripSyntheticData.create_test_trip(user=self.user, title='Other Trip')

        journal1 = Journal.objects.create(trip=self.trip, title='Trip 1 Journal', visibility=JournalVisibility.PRIVATE, timezone='UTC')
        journal2 = Journal.objects.create(trip=trip2, title='Trip 2 Journal', visibility=JournalVisibility.PRIVATE, timezone='UTC')

        primary1 = Journal.objects.get_primary_for_trip(self.trip)
        primary2 = Journal.objects.get_primary_for_trip(trip2)

        self.assertEqual(primary1, journal1)
        self.assertEqual(primary2, journal2)


class JournalEntryManagerForJournalTestCase(TestCase):
    """Test JournalEntryManager.for_journal filtering."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(email='user@test.com', password='pass')
        cls.trip = TripSyntheticData.create_test_trip(user=cls.user, title='Test Trip')
        cls.journal = Journal.objects.create(
            trip=cls.trip,
            title='Test Journal',
            visibility=JournalVisibility.PRIVATE,
            timezone='UTC',
        )

    def test_for_journal_returns_journal_entries(self):
        """for_journal should return all entries for the specified journal."""
        from datetime import date

        entry1 = JournalEntry.objects.create(journal=self.journal, date=date(2025, 1, 15), timezone='UTC')
        entry2 = JournalEntry.objects.create(journal=self.journal, date=date(2025, 1, 16), timezone='UTC')

        entries = JournalEntry.objects.for_journal(self.journal)

        self.assertEqual(entries.count(), 2)
        self.assertIn(entry1, entries)
        self.assertIn(entry2, entries)

    def test_for_journal_excludes_other_journal_entries(self):
        """for_journal should not return entries from other journals."""
        from datetime import date

        journal2 = Journal.objects.create(trip=self.trip, title='Other Journal', visibility=JournalVisibility.PRIVATE, timezone='UTC')

        entry1 = JournalEntry.objects.create(journal=self.journal, date=date(2025, 1, 15), timezone='UTC')
        entry2 = JournalEntry.objects.create(journal=journal2, date=date(2025, 1, 15), timezone='UTC')

        journal1_entries = JournalEntry.objects.for_journal(self.journal)

        self.assertEqual(journal1_entries.count(), 1)
        self.assertIn(entry1, journal1_entries)
        self.assertNotIn(entry2, journal1_entries)

    def test_for_journal_empty_for_journal_without_entries(self):
        """for_journal should return empty queryset for journals with no entries."""
        entries = JournalEntry.objects.for_journal(self.journal)
        self.assertEqual(entries.count(), 0)

    def test_for_journal_returns_queryset(self):
        """for_journal should return a QuerySet."""
        from datetime import date

        JournalEntry.objects.create(journal=self.journal, date=date(2025, 1, 15), timezone='UTC')

        entries = JournalEntry.objects.for_journal(self.journal)

        # Should be a QuerySet
        self.assertTrue(hasattr(entries, 'count'))
        self.assertTrue(hasattr(entries, 'filter'))

    def test_for_journal_ordering(self):
        """for_journal should return entries ordered by date ascending."""
        from datetime import date

        entry3 = JournalEntry.objects.create(journal=self.journal, date=date(2025, 1, 17), timezone='UTC')
        entry1 = JournalEntry.objects.create(journal=self.journal, date=date(2025, 1, 15), timezone='UTC')
        entry2 = JournalEntry.objects.create(journal=self.journal, date=date(2025, 1, 16), timezone='UTC')

        entries = JournalEntry.objects.for_journal(self.journal)

        # Should be ordered by date ascending (Meta.ordering = ['date'])
        entry_list = list(entries)
        self.assertEqual(entry_list[0], entry1)
        self.assertEqual(entry_list[1], entry2)
        self.assertEqual(entry_list[2], entry3)


class JournalCascadeDeletionTestCase(TestCase):
    """Test CASCADE deletion behavior for journals and entries."""

    def setUp(self):
        self.user = User.objects.create_user(email='user@test.com', password='pass')
        self.trip = TripSyntheticData.create_test_trip(user=self.user, title='Test Trip')

    def test_delete_trip_deletes_journals(self):
        """Deleting trip should CASCADE delete all journals."""
        Journal.objects.create(trip=self.trip, title='Journal 1', visibility=JournalVisibility.PRIVATE, timezone='UTC')
        Journal.objects.create(trip=self.trip, title='Journal 2', visibility=JournalVisibility.PRIVATE, timezone='UTC')

        trip_id = self.trip.pk
        self.assertEqual(Journal.objects.filter(trip_id=trip_id).count(), 2)

        self.trip.delete()

        # Journals should be deleted
        self.assertEqual(Journal.objects.filter(trip_id=trip_id).count(), 0)

    def test_delete_journal_deletes_entries(self):
        """Deleting journal should CASCADE delete all journal entries."""
        from datetime import date

        journal = Journal.objects.create(trip=self.trip, title='Journal', visibility=JournalVisibility.PRIVATE, timezone='UTC')

        JournalEntry.objects.create(journal=journal, date=date(2025, 1, 15), timezone='UTC')
        JournalEntry.objects.create(journal=journal, date=date(2025, 1, 16), timezone='UTC')

        journal_id = journal.pk
        self.assertEqual(JournalEntry.objects.filter(journal_id=journal_id).count(), 2)

        journal.delete()

        # Entries should be deleted
        self.assertEqual(JournalEntry.objects.filter(journal_id=journal_id).count(), 0)

    def test_delete_trip_deletes_journals_and_entries(self):
        """Deleting trip should CASCADE delete journals and all their entries."""
        from datetime import date

        journal = Journal.objects.create(trip=self.trip, title='Journal', visibility=JournalVisibility.PRIVATE, timezone='UTC')
        JournalEntry.objects.create(journal=journal, date=date(2025, 1, 15), timezone='UTC')

        trip_id = self.trip.pk
        journal_id = journal.pk

        self.trip.delete()

        # Both journal and entries should be deleted
        self.assertEqual(Journal.objects.filter(trip_id=trip_id).count(), 0)
        self.assertEqual(JournalEntry.objects.filter(journal_id=journal_id).count(), 0)


class JournalManagerEdgeCasesTestCase(TestCase):
    """Test edge cases and boundary conditions."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(email='user@test.com', password='pass')
        cls.trip = TripSyntheticData.create_test_trip(user=cls.user, title='Test Trip')

    def test_for_trip_multiple_journals_different_visibilities(self):
        """for_trip should return journals regardless of visibility."""
        journal1 = Journal.objects.create(trip=self.trip, title='Private', visibility=JournalVisibility.PRIVATE, timezone='UTC')
        journal2 = Journal.objects.create(trip=self.trip, title='Protected', visibility=JournalVisibility.PROTECTED, timezone='UTC')
        journal3 = Journal.objects.create(trip=self.trip, title='Public', visibility=JournalVisibility.PUBLIC, timezone='UTC')

        journals = Journal.objects.for_trip(self.trip)

        self.assertEqual(journals.count(), 3)
        self.assertIn(journal1, journals)
        self.assertIn(journal2, journals)
        self.assertIn(journal3, journals)

    def test_for_trip_multiple_journals_different_timezones(self):
        """for_trip should return journals with different timezones."""
        Journal.objects.create(trip=self.trip, title='UTC Journal', visibility=JournalVisibility.PRIVATE, timezone='UTC')
        Journal.objects.create(trip=self.trip, title='NY Journal', visibility=JournalVisibility.PRIVATE, timezone='America/New_York')
        Journal.objects.create(trip=self.trip, title='Tokyo Journal', visibility=JournalVisibility.PRIVATE, timezone='Asia/Tokyo')

        journals = Journal.objects.for_trip(self.trip)

        self.assertEqual(journals.count(), 3)

    def test_get_primary_many_journals(self):
        """get_primary_for_trip should handle trips with many journals."""
        # Create many journals
        journals_created = []
        for i in range(20):
            journal = Journal.objects.create(
                trip=self.trip,
                title=f'Journal {i}',
                visibility=JournalVisibility.PRIVATE,
                timezone='UTC',
            )
            journals_created.append(journal)

        primary = Journal.objects.get_primary_for_trip(self.trip)

        # Should return the first created
        self.assertEqual(primary, journals_created[0])

    def test_for_journal_entries_with_same_date(self):
        """for_journal should handle entries with same date (edge case for unique constraint)."""
        from datetime import date

        # Journal entries have unique_together constraint on (journal, date)
        # This test verifies we can't create duplicates
        journal = Journal.objects.create(trip=self.trip, title='Journal', visibility=JournalVisibility.PRIVATE, timezone='UTC')

        JournalEntry.objects.create(journal=journal, date=date(2025, 1, 15), timezone='UTC')

        # Attempting to create another entry with same date should fail
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            JournalEntry.objects.create(journal=journal, date=date(2025, 1, 15), timezone='America/New_York')

    def test_journal_get_entries_method(self):
        """Journal.get_entries() should return queryset of journal entries."""
        from datetime import date

        journal = Journal.objects.create(trip=self.trip, title='Journal', visibility=JournalVisibility.PRIVATE, timezone='UTC')

        entry1 = JournalEntry.objects.create(journal=journal, date=date(2025, 1, 15), timezone='UTC')
        entry2 = JournalEntry.objects.create(journal=journal, date=date(2025, 1, 16), timezone='UTC')

        entries = journal.get_entries()

        self.assertEqual(entries.count(), 2)
        self.assertIn(entry1, entries)
        self.assertIn(entry2, entries)

    def test_journal_password_properties(self):
        """Journal password-related properties should work correctly."""
        journal = Journal.objects.create(
            trip=self.trip,
            title='Protected Journal',
            visibility=JournalVisibility.PROTECTED,
            timezone='UTC',
        )

        # No password initially
        self.assertFalse(journal.has_password)
        self.assertTrue(journal.is_misconfigured_protected)

        # Set password
        journal.set_password('secure_password')
        journal.save()

        # Reload from database
        journal.refresh_from_db()

        # Should have password now
        self.assertTrue(journal.has_password)
        self.assertFalse(journal.is_misconfigured_protected)

        # Check password
        self.assertTrue(journal.check_password('secure_password'))
        self.assertFalse(journal.check_password('wrong_password'))

    def test_journal_password_version_increments(self):
        """Setting password should increment password_version."""
        journal = Journal.objects.create(
            trip=self.trip,
            title='Journal',
            visibility=JournalVisibility.PROTECTED,
            timezone='UTC',
        )

        initial_version = journal.password_version

        # Set password
        journal.set_password('password1')
        journal.save()

        # Version should increment
        self.assertEqual(journal.password_version, initial_version + 1)

        # Change password again
        journal.set_password('password2')
        journal.save()

        # Version should increment again
        self.assertEqual(journal.password_version, initial_version + 2)

    def test_journal_entry_auto_title_generation(self):
        """JournalEntry should auto-generate title from date if not provided."""
        from datetime import date

        journal = Journal.objects.create(trip=self.trip, title='Journal', visibility=JournalVisibility.PRIVATE, timezone='UTC')

        entry = JournalEntry.objects.create(
            journal=journal,
            date=date(2025, 1, 15),
            timezone='UTC',
            title='',  # Empty title
        )

        # Title should be auto-generated
        self.assertNotEqual(entry.title, '')
        self.assertIn('January', entry.title)
        self.assertIn('15', entry.title)
        self.assertIn('2025', entry.title)

    def test_journal_entry_generate_default_title(self):
        """JournalEntry.generate_default_title returns correct format."""
        from datetime import date

        test_date = date(2025, 11, 25)  # A Tuesday
        title = JournalEntry.generate_default_title(test_date)
        self.assertEqual(title, 'Tuesday, November 25, 2025')

    def test_journal_str_representation(self):
        """Journal __str__ should return meaningful string."""
        journal = Journal.objects.create(
            trip=self.trip,
            title='My Travel Journal',
            visibility=JournalVisibility.PRIVATE,
            timezone='UTC',
        )

        str_repr = str(journal)

        self.assertIn('My Travel Journal', str_repr)
        self.assertIn('Test Trip', str_repr)

    def test_journal_entry_str_representation(self):
        """JournalEntry __str__ should return meaningful string."""
        from datetime import date

        journal = Journal.objects.create(trip=self.trip, title='Journal', visibility=JournalVisibility.PRIVATE, timezone='UTC')
        entry = JournalEntry.objects.create(journal=journal, date=date(2025, 1, 15), timezone='UTC', title='Day 1')

        str_repr = str(entry)

        self.assertIn('Journal', str_repr)
        self.assertIn('2025-01-15', str_repr)
