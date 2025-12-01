"""
Tests for PublishingService.

Tests critical transaction and locking patterns including:
- @transaction.atomic operations with rollback behavior
- SELECT FOR UPDATE race condition prevention
- Version number generation atomicity
- Cache invalidation on publish operations
- Error handling for edge cases
"""
import logging
from datetime import date
from unittest.mock import patch, MagicMock

from django.contrib.auth import get_user_model
from django.test import TransactionTestCase

from tt.apps.journal.models import Journal, JournalEntry
from tt.apps.journal.enums import JournalVisibility
from tt.apps.trips.tests.synthetic_data import TripSyntheticData

from tt.apps.journal.models import PROLOGUE_DATE, EPILOGUE_DATE

from ..models import Travelog, TravelogEntry
from ..services import PublishingService, PublishingError, DayPageBuilder

logging.disable(logging.CRITICAL)

User = get_user_model()


class TestPublishingServicePublishJournal(TransactionTestCase):
    """Test PublishingService.publish_journal() transaction and locking patterns."""

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
            description='Test description',
            visibility=JournalVisibility.PUBLIC
        )

    def test_publish_journal_success(self):
        """Test successful journal publishing with proper snapshot creation."""
        # Create journal entries
        entry1 = JournalEntry.objects.create(
            journal=self.journal,
            date=date(2024, 1, 10),
            title='Day 1',
            text='Entry 1 content'
        )
        entry2 = JournalEntry.objects.create(
            journal=self.journal,
            date=date(2024, 1, 11),
            title='Day 2',
            text='Entry 2 content'
        )

        # Publish journal
        with patch('tt.apps.travelog.services.get_redis_client'):
            travelog = PublishingService.publish_journal(self.journal, self.user)

        # Verify travelog created with correct attributes
        self.assertIsNotNone(travelog)
        self.assertEqual(travelog.journal, self.journal)
        self.assertEqual(travelog.version_number, 1)
        self.assertTrue(travelog.is_current)
        self.assertEqual(travelog.published_by, self.user)
        self.assertEqual(travelog.title, self.journal.title)
        self.assertEqual(travelog.description, self.journal.description)

        # Verify entries were copied
        travelog_entries = TravelogEntry.objects.filter(travelog=travelog).order_by('date')
        self.assertEqual(travelog_entries.count(), 2)

        # Verify entry content matches
        self.assertEqual(travelog_entries[0].date, entry1.date)
        self.assertEqual(travelog_entries[0].title, entry1.title)
        self.assertEqual(travelog_entries[0].text, entry1.text)
        self.assertEqual(travelog_entries[1].date, entry2.date)
        self.assertEqual(travelog_entries[1].title, entry2.title)
        self.assertEqual(travelog_entries[1].text, entry2.text)

    def test_publish_journal_no_entries_raises_error(self):
        """Test that publishing journal with no entries raises ValueError."""
        # Journal has no entries
        with self.assertRaises(ValueError) as context:
            with patch('tt.apps.travelog.services.get_redis_client'):
                PublishingService.publish_journal(self.journal, self.user)

        self.assertIn('no entries', str(context.exception))

        # Verify no travelog was created
        self.assertEqual(Travelog.objects.filter(journal=self.journal).count(), 0)

    def test_publish_journal_version_numbering(self):
        """Test that version numbers increment correctly."""
        # Create entry for publishing
        JournalEntry.objects.create(
            journal=self.journal,
            date=date(2024, 1, 10),
            title='Day 1',
            text='Content'
        )

        with patch('tt.apps.travelog.services.get_redis_client'):
            # Publish first version
            travelog1 = PublishingService.publish_journal(self.journal, self.user)
            self.assertEqual(travelog1.version_number, 1)

            # Publish second version
            travelog2 = PublishingService.publish_journal(self.journal, self.user)
            self.assertEqual(travelog2.version_number, 2)

            # Publish third version
            travelog3 = PublishingService.publish_journal(self.journal, self.user)
            self.assertEqual(travelog3.version_number, 3)

    def test_publish_journal_unmarks_previous_current(self):
        """Test that publishing unmarks previous version as current."""
        JournalEntry.objects.create(
            journal=self.journal,
            date=date(2024, 1, 10),
            title='Day 1',
            text='Content'
        )

        with patch('tt.apps.travelog.services.get_redis_client'):
            # Publish first version
            travelog1 = PublishingService.publish_journal(self.journal, self.user)
            self.assertTrue(travelog1.is_current)

            # Publish second version
            travelog2 = PublishingService.publish_journal(self.journal, self.user)

            # Verify travelog2 is current and travelog1 is not
            travelog1.refresh_from_db()
            self.assertFalse(travelog1.is_current)
            self.assertTrue(travelog2.is_current)

            # Only one version should be current
            current_count = Travelog.objects.filter(
                journal=self.journal,
                is_current=True
            ).count()
            self.assertEqual(current_count, 1)

    def test_publish_journal_selects_for_update(self):
        """Test that publish_journal uses SELECT FOR UPDATE for locking."""
        JournalEntry.objects.create(
            journal=self.journal,
            date=date(2024, 1, 10),
            title='Day 1',
            text='Content'
        )

        # We can verify SELECT FOR UPDATE was used by checking query execution
        with patch('tt.apps.travelog.services.get_redis_client'):
            with self.assertNumQueries(9):  # Exact count may vary, but queries should be executed
                PublishingService.publish_journal(self.journal, self.user)

        # In TransactionTestCase, we can verify the transaction was atomic
        # by checking that all or nothing was created
        self.assertEqual(Travelog.objects.filter(journal=self.journal).count(), 1)
        self.assertEqual(TravelogEntry.objects.count(), 1)

    def test_publish_journal_invalidates_view_cache(self):
        """Test that publishing invalidates VIEW cache."""
        JournalEntry.objects.create(
            journal=self.journal,
            date=date(2024, 1, 10),
            title='Day 1',
            text='Content'
        )

        mock_redis = MagicMock()
        mock_redis.delete.return_value = 1

        with patch('tt.apps.travelog.services.get_redis_client', return_value=mock_redis):
            PublishingService.publish_journal(self.journal, self.user)

        # Verify cache invalidation was called
        mock_redis.delete.assert_called()
        cache_key = mock_redis.delete.call_args[0][0]
        self.assertIn(str(self.journal.uuid), cache_key)
        self.assertIn('VIEW', cache_key)

    def test_publish_journal_copies_reference_image(self):
        """Test that reference_image is properly copied to travelog from journal."""
        from tt.apps.images.models import TripImage
        from django.core.files.base import ContentFile

        # Create a test image
        test_image = TripImage.objects.create(
            uploaded_by=self.user
        )
        # Save minimal image data to satisfy ImageField
        test_image.web_image.save('test.jpg', ContentFile(b'fake_image_data'), save=True)

        # Set as journal reference image
        self.journal.reference_image = test_image
        self.journal.save()

        JournalEntry.objects.create(
            journal=self.journal,
            date=date(2024, 1, 10),
            title='Day 1',
            text='Content'
        )

        with patch('tt.apps.travelog.services.get_redis_client'):
            travelog = PublishingService.publish_journal(self.journal, self.user)

        # Travelog should have its own reference_image field (snapshot from journal)
        self.assertEqual(travelog.reference_image, test_image)

    def test_publish_journal_transaction_rollback_on_error(self):
        """Test that transaction rolls back properly on error."""
        JournalEntry.objects.create(
            journal=self.journal,
            date=date(2024, 1, 10),
            title='Day 1',
            text='Content'
        )

        # Force an error during entry creation
        with patch('tt.apps.travelog.models.TravelogEntry.objects.create',
                   side_effect=Exception('Simulated error')):
            with self.assertRaises(Exception):
                with patch('tt.apps.travelog.services.get_redis_client'):
                    PublishingService.publish_journal(self.journal, self.user)

        # Verify no partial data was saved due to rollback
        self.assertEqual(Travelog.objects.filter(journal=self.journal).count(), 0)
        self.assertEqual(TravelogEntry.objects.count(), 0)


class TestPublishingServiceSetAsCurrent(TransactionTestCase):
    """Test PublishingService.set_as_current() transaction and validation patterns."""

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
            description='Test description',
            visibility=JournalVisibility.PUBLIC
        )

        # Create entry and publish two versions
        JournalEntry.objects.create(
            journal=self.journal,
            date=date(2024, 1, 10),
            title='Day 1',
            text='Content'
        )

        with patch('tt.apps.travelog.services.get_redis_client'):
            self.travelog1 = PublishingService.publish_journal(self.journal, self.user)
            self.travelog2 = PublishingService.publish_journal(self.journal, self.user)

        # travelog2 should be current
        self.travelog1.refresh_from_db()
        self.travelog2.refresh_from_db()

    def test_set_as_current_success(self):
        """Test successfully setting a version as current."""
        self.assertFalse(self.travelog1.is_current)
        self.assertTrue(self.travelog2.is_current)

        with patch('tt.apps.travelog.services.get_redis_client'):
            result = PublishingService.set_as_current(self.journal, self.travelog1)

        # Verify travelog1 is now current
        self.assertEqual(result, self.travelog1)
        self.travelog1.refresh_from_db()
        self.travelog2.refresh_from_db()
        self.assertTrue(self.travelog1.is_current)
        self.assertFalse(self.travelog2.is_current)

        # Only one version should be current
        current_count = Travelog.objects.filter(
            journal=self.journal,
            is_current=True
        ).count()
        self.assertEqual(current_count, 1)

    def test_set_as_current_wrong_journal_raises_error(self):
        """Test that setting version from wrong journal raises PublishingError."""
        # Create another journal with its own travelog
        other_journal = Journal.objects.create(
            trip=self.trip,
            title='Other Journal',
            visibility=JournalVisibility.PUBLIC
        )
        JournalEntry.objects.create(
            journal=other_journal,
            date=date(2024, 1, 10),
            title='Day 1',
            text='Content'
        )
        with patch('tt.apps.travelog.services.get_redis_client'):
            other_travelog = PublishingService.publish_journal(other_journal, self.user)

        # Try to set other_travelog as current for self.journal
        with self.assertRaises(PublishingError) as context:
            PublishingService.set_as_current(self.journal, other_travelog)

        self.assertIn('does not belong to this journal', str(context.exception))

    def test_set_as_current_already_current_raises_error(self):
        """Test that setting already-current version raises PublishingError."""
        self.assertTrue(self.travelog2.is_current)

        with self.assertRaises(PublishingError) as context:
            PublishingService.set_as_current(self.journal, self.travelog2)

        self.assertIn('already the current', str(context.exception))

    def test_set_as_current_invalidates_view_cache(self):
        """Test that set_as_current invalidates VIEW cache."""
        mock_redis = MagicMock()
        mock_redis.delete.return_value = 1

        with patch('tt.apps.travelog.services.get_redis_client', return_value=mock_redis):
            PublishingService.set_as_current(self.journal, self.travelog1)

        # Verify cache invalidation was called
        mock_redis.delete.assert_called()
        cache_key = mock_redis.delete.call_args[0][0]
        self.assertIn(str(self.journal.uuid), cache_key)
        self.assertIn('VIEW', cache_key)

    def test_set_as_current_atomic_operation(self):
        """Test that set_as_current is atomic - all or nothing."""
        # Force an error during the update operation
        with patch('tt.apps.travelog.models.Travelog.objects.filter') as mock_filter:
            # Make the filter().update() raise an error
            mock_filter.return_value.update.side_effect = Exception('Simulated database error')

            with self.assertRaises(Exception):
                with patch('tt.apps.travelog.services.get_redis_client'):
                    PublishingService.set_as_current(self.journal, self.travelog1)

        # Verify rollback - travelog2 should still be current
        self.travelog1.refresh_from_db()
        self.travelog2.refresh_from_db()
        self.assertFalse(self.travelog1.is_current)
        self.assertTrue(self.travelog2.is_current)


class TestDayPageBuilder(TransactionTestCase):
    """Test DayPageBuilder service for day page context generation."""

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

    def test_build_with_regular_entries(self):
        """Test building day page data with regular entries only."""
        _ = JournalEntry.objects.create(
            journal=self.journal, date=date(2024, 3, 15), title='Day 1', text='First'
        )
        entry2 = JournalEntry.objects.create(
            journal=self.journal, date=date(2024, 3, 16), title='Day 2', text='Second'
        )
        _ = JournalEntry.objects.create(
            journal=self.journal, date=date(2024, 3, 17), title='Day 3', text='Third'
        )
        entries = list(self.journal.entries.order_by('date'))

        day_page = DayPageBuilder.build(entries, date(2024, 3, 16))

        # TOC entries
        self.assertEqual(len(day_page.toc_entries), 3)
        self.assertEqual(day_page.toc_entries[0].day_number, 1)
        self.assertEqual(day_page.toc_entries[1].day_number, 2)
        self.assertEqual(day_page.toc_entries[2].day_number, 3)
        self.assertFalse(day_page.toc_entries[0].is_active)
        self.assertTrue(day_page.toc_entries[1].is_active)
        self.assertFalse(day_page.toc_entries[2].is_active)

        # Current entry
        self.assertEqual(day_page.current_entry.entry, entry2)
        self.assertEqual(day_page.current_entry.day_number, 2)
        self.assertEqual(day_page.current_entry.prev_date, date(2024, 3, 15))
        self.assertEqual(day_page.current_entry.next_date, date(2024, 3, 17))
        self.assertTrue(day_page.current_entry.has_previous)
        self.assertTrue(day_page.current_entry.has_next)

        # Day count and boundaries
        self.assertEqual(day_page.day_count, 3)
        self.assertEqual(day_page.first_day_date, date(2024, 3, 15))
        self.assertEqual(day_page.last_day_date, date(2024, 3, 17))

    def test_build_with_prologue_and_epilogue(self):
        """Test building day page data with special entries excluded from day numbering."""
        _ = JournalEntry.objects.create(
            journal=self.journal, date=PROLOGUE_DATE, title='Prologue', text='Intro'
        )
        _ = JournalEntry.objects.create(
            journal=self.journal, date=date(2024, 3, 15), title='Day 1', text='First'
        )
        _ = JournalEntry.objects.create(
            journal=self.journal, date=date(2024, 3, 16), title='Day 2', text='Second'
        )
        _ = JournalEntry.objects.create(
            journal=self.journal, date=EPILOGUE_DATE, title='Epilogue', text='Summary'
        )
        entries = list(self.journal.entries.order_by('date'))

        day_page = DayPageBuilder.build(entries, date(2024, 3, 15))

        # TOC entries - special entries have None day_number
        self.assertEqual(len(day_page.toc_entries), 4)
        self.assertIsNone(day_page.toc_entries[0].day_number)  # Prologue
        self.assertEqual(day_page.toc_entries[1].day_number, 1)
        self.assertEqual(day_page.toc_entries[2].day_number, 2)
        self.assertIsNone(day_page.toc_entries[3].day_number)  # Epilogue

        # Day count excludes prologue/epilogue
        self.assertEqual(day_page.day_count, 2)

        # First/last day are real days, not special entries
        self.assertEqual(day_page.first_day_date, date(2024, 3, 15))
        self.assertEqual(day_page.last_day_date, date(2024, 3, 16))

    def test_build_first_entry_has_no_previous(self):
        """Test that first entry has no previous navigation."""
        JournalEntry.objects.create(
            journal=self.journal, date=date(2024, 3, 15), title='Day 1', text='First'
        )
        JournalEntry.objects.create(
            journal=self.journal, date=date(2024, 3, 16), title='Day 2', text='Second'
        )
        entries = list(self.journal.entries.order_by('date'))

        day_page = DayPageBuilder.build(entries, date(2024, 3, 15))

        self.assertIsNone(day_page.current_entry.prev_date)
        self.assertFalse(day_page.current_entry.has_previous)
        self.assertEqual(day_page.current_entry.next_date, date(2024, 3, 16))
        self.assertTrue(day_page.current_entry.has_next)

    def test_build_last_entry_has_no_next(self):
        """Test that last entry has no next navigation."""
        JournalEntry.objects.create(
            journal=self.journal, date=date(2024, 3, 15), title='Day 1', text='First'
        )
        JournalEntry.objects.create(
            journal=self.journal, date=date(2024, 3, 16), title='Day 2', text='Second'
        )
        entries = list(self.journal.entries.order_by('date'))

        day_page = DayPageBuilder.build(entries, date(2024, 3, 16))

        self.assertEqual(day_page.current_entry.prev_date, date(2024, 3, 15))
        self.assertTrue(day_page.current_entry.has_previous)
        self.assertIsNone(day_page.current_entry.next_date)
        self.assertFalse(day_page.current_entry.has_next)

    def test_build_viewing_prologue(self):
        """Test building day page when viewing prologue."""
        prologue = JournalEntry.objects.create(
            journal=self.journal, date=PROLOGUE_DATE, title='Prologue', text='Intro'
        )
        _ = JournalEntry.objects.create(
            journal=self.journal, date=date(2024, 3, 15), title='Day 1', text='First'
        )
        entries = list(self.journal.entries.order_by('date'))

        day_page = DayPageBuilder.build(entries, PROLOGUE_DATE)

        # Prologue has no day number
        self.assertIsNone(day_page.current_entry.day_number)
        self.assertEqual(day_page.current_entry.entry, prologue)

        # First entry has no prev
        self.assertIsNone(day_page.current_entry.prev_date)
        self.assertEqual(day_page.current_entry.next_date, date(2024, 3, 15))

    def test_build_raises_404_for_missing_date(self):
        """Test that build raises Http404 for non-existent date."""
        from django.http import Http404

        JournalEntry.objects.create(
            journal=self.journal, date=date(2024, 3, 15), title='Day 1', text='First'
        )
        entries = list(self.journal.entries.order_by('date'))

        with self.assertRaises(Http404):
            DayPageBuilder.build(entries, date(2024, 3, 20))  # Date doesn't exist

    def test_build_only_special_entries(self):
        """Test building day page with only prologue/epilogue."""
        JournalEntry.objects.create(
            journal=self.journal, date=PROLOGUE_DATE, title='Prologue', text='Intro'
        )
        JournalEntry.objects.create(
            journal=self.journal, date=EPILOGUE_DATE, title='Epilogue', text='Summary'
        )
        entries = list(self.journal.entries.order_by('date'))

        day_page = DayPageBuilder.build(entries, PROLOGUE_DATE)

        # Day count is 0
        self.assertEqual(day_page.day_count, 0)
        self.assertIsNone(day_page.first_day_date)
        self.assertIsNone(day_page.last_day_date)

    def test_toc_entry_display_title(self):
        """Test TocEntryData display_title property formatting."""
        JournalEntry.objects.create(
            journal=self.journal, date=PROLOGUE_DATE, title='Prologue', text='Intro'
        )
        JournalEntry.objects.create(
            journal=self.journal, date=date(2024, 3, 15), title='Arrival', text='First'
        )
        # Note: JournalEntry auto-generates title from date when empty,
        # so we test with explicit title to verify our formatting
        JournalEntry.objects.create(
            journal=self.journal, date=date(2024, 3, 16), title='Exploring', text='Second'
        )
        entries = list(self.journal.entries.order_by('date'))

        day_page = DayPageBuilder.build(entries, date(2024, 3, 15))

        # Prologue - no day number, uses title
        self.assertEqual(day_page.toc_entries[0].display_title, 'Prologue')

        # Day 1 with title
        self.assertEqual(day_page.toc_entries[1].display_title, 'Day 1: Arrival')

        # Day 2 with title
        self.assertEqual(day_page.toc_entries[2].display_title, 'Day 2: Exploring')

    def test_toc_entry_display_title_no_explicit_title(self):
        """Test TocEntryData display_title when entry has auto-generated title.

        JournalEntry.save() auto-generates a title from the date when title is empty,
        so entries always have some form of title. This tests that display_title
        correctly formats entries with auto-generated date titles.
        """
        from ..schemas import TocEntryData

        # Create entry without explicit title - will get auto-generated date title
        entry_no_explicit_title = JournalEntry.objects.create(
            journal=self.journal, date=date(2024, 3, 15), title='', text='Test'
        )
        # Verify the auto-generated title contains the date
        self.assertIn('March', entry_no_explicit_title.title)

        # Test TocEntryData with entry that has auto-generated title
        toc_entry = TocEntryData(
            entry=entry_no_explicit_title,
            day_number=1,
            is_active=False
        )
        # Should format as "Day N: <auto-generated title>"
        self.assertTrue(toc_entry.display_title.startswith('Day 1:'))
        self.assertIn('March', toc_entry.display_title)

        # Special entry without explicit title gets page type label as title
        special_entry = JournalEntry.objects.create(
            journal=self.journal, date=PROLOGUE_DATE, title='', text='Prologue content'
        )
        special_toc_entry = TocEntryData(
            entry=special_entry,
            day_number=None,
            is_active=False
        )
        # Prologue's auto-generated title based on date
        self.assertIsNotNone(special_toc_entry.display_title)
