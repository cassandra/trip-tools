"""
Tests for TravelogPublicListBuilder.

Tests the business logic for building travelog lists:
- Date range calculation (excluding prologue/epilogue sentinel dates)
- Fallback to published_datetime for journals with only special entries
- Chronological sorting by latest entry date
- Display image selection (preferring dated entries)
- Access filtering via access_checker callback
"""
import logging
from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.test import TransactionTestCase

from tt.apps.journal.models import Journal, JournalEntry, PROLOGUE_DATE, EPILOGUE_DATE
from tt.apps.journal.enums import JournalVisibility
from tt.apps.trips.tests.synthetic_data import TripSyntheticData

from ..exceptions import PasswordRequiredException
from ..services import PublishingService, TravelogPublicListBuilder

logging.disable(logging.CRITICAL)

User = get_user_model()


class TestTravelogPublicListBuilderDateRange(TransactionTestCase):
    """Test date range calculation with special entries."""

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

    def test_date_range_excludes_prologue_epilogue(self):
        """Date range calculation excludes prologue/epilogue sentinel dates."""
        journal = Journal.objects.create(
            trip=self.trip,
            title='Test Journal',
            visibility=JournalVisibility.PUBLIC
        )

        # Create entries: prologue, dated entries, epilogue
        JournalEntry.objects.create(
            journal=journal, date=PROLOGUE_DATE, title='Prologue', text='Intro'
        )
        JournalEntry.objects.create(
            journal=journal, date=date(2024, 3, 15), title='Day 1', text='First day'
        )
        JournalEntry.objects.create(
            journal=journal, date=date(2024, 3, 20), title='Day 5', text='Last day'
        )
        JournalEntry.objects.create(
            journal=journal, date=EPILOGUE_DATE, title='Epilogue', text='Summary'
        )

        # Publish to create travelog
        with patch('tt.apps.travelog.services.get_redis_client'):
            PublishingService.publish_journal(journal, self.user)

        # Build list with access_checker that allows all
        items = TravelogPublicListBuilder.build(
            target_user=self.user,
            access_checker=lambda j: None
        )

        self.assertEqual(len(items), 1)
        item = items[0]

        # Dates should be from real entries, not sentinel dates
        self.assertEqual(item.earliest_entry_date, '2024-03-15')
        self.assertEqual(item.latest_entry_date, '2024-03-20')

    def test_fallback_to_published_datetime_for_only_special_entries(self):
        """Journals with only prologue/epilogue use published_datetime for sorting."""
        journal = Journal.objects.create(
            trip=self.trip,
            title='Special Only',
            visibility=JournalVisibility.PUBLIC
        )

        # Create only prologue and epilogue entries
        JournalEntry.objects.create(
            journal=journal, date=PROLOGUE_DATE, title='Prologue', text='Intro'
        )
        JournalEntry.objects.create(
            journal=journal, date=EPILOGUE_DATE, title='Epilogue', text='Summary'
        )

        # Publish to create travelog
        with patch('tt.apps.travelog.services.get_redis_client'):
            travelog = PublishingService.publish_journal(journal, self.user)

        # Build list
        items = TravelogPublicListBuilder.build(
            target_user=self.user,
            access_checker=lambda j: None
        )

        self.assertEqual(len(items), 1)
        item = items[0]

        # Dates should be from travelog published_datetime, not sentinel dates
        expected_date = travelog.published_datetime.strftime('%Y-%m-%d')
        self.assertEqual(item.earliest_entry_date, expected_date)
        self.assertEqual(item.latest_entry_date, expected_date)

        # Verify we're not using sentinel dates
        self.assertNotEqual(item.earliest_entry_date, '0001-01-01')
        self.assertNotEqual(item.latest_entry_date, '9999-12-31')


class TestTravelogPublicListBuilderSorting(TransactionTestCase):
    """Test chronological sorting of travelogs."""

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

    def test_sorts_by_latest_date_descending(self):
        """Travelogs are sorted by latest_entry_date (newest first)."""
        # Create three journals with different date ranges
        journal_old = Journal.objects.create(
            trip=self.trip, title='Old Journal', visibility=JournalVisibility.PUBLIC
        )
        JournalEntry.objects.create(
            journal=journal_old, date=date(2023, 1, 10), title='Day', text='Old'
        )

        journal_mid = Journal.objects.create(
            trip=self.trip, title='Mid Journal', visibility=JournalVisibility.PUBLIC
        )
        JournalEntry.objects.create(
            journal=journal_mid, date=date(2024, 6, 15), title='Day', text='Mid'
        )

        journal_new = Journal.objects.create(
            trip=self.trip, title='New Journal', visibility=JournalVisibility.PUBLIC
        )
        JournalEntry.objects.create(
            journal=journal_new, date=date(2024, 12, 25), title='Day', text='New'
        )

        # Publish all journals
        with patch('tt.apps.travelog.services.get_redis_client'):
            PublishingService.publish_journal(journal_old, self.user)
            PublishingService.publish_journal(journal_mid, self.user)
            PublishingService.publish_journal(journal_new, self.user)

        # Build list
        items = TravelogPublicListBuilder.build(
            target_user=self.user,
            access_checker=lambda j: None
        )

        self.assertEqual(len(items), 3)

        # Should be sorted newest first
        self.assertEqual(items[0].journal.title, 'New Journal')
        self.assertEqual(items[1].journal.title, 'Mid Journal')
        self.assertEqual(items[2].journal.title, 'Old Journal')


class TestTravelogPublicListBuilderAccessFiltering(TransactionTestCase):
    """Test access filtering via access_checker callback."""

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

    def test_password_required_sets_requires_password_flag(self):
        """PasswordRequiredException sets requires_password=True on item."""
        journal = Journal.objects.create(
            trip=self.trip, title='Protected Journal', visibility=JournalVisibility.PUBLIC
        )
        JournalEntry.objects.create(
            journal=journal, date=date(2024, 5, 1), title='Day', text='Content'
        )

        with patch('tt.apps.travelog.services.get_redis_client'):
            PublishingService.publish_journal(journal, self.user)

        # Access checker raises PasswordRequiredException
        def access_checker(j):
            raise PasswordRequiredException(journal_uuid=j.uuid)

        items = TravelogPublicListBuilder.build(
            target_user=self.user,
            access_checker=access_checker
        )

        self.assertEqual(len(items), 1)
        self.assertTrue(items[0].requires_password)

    def test_http404_excludes_from_list(self):
        """Http404 exception excludes journal from list."""
        journal = Journal.objects.create(
            trip=self.trip, title='Hidden Journal', visibility=JournalVisibility.PUBLIC
        )
        JournalEntry.objects.create(
            journal=journal, date=date(2024, 5, 1), title='Day', text='Content'
        )

        with patch('tt.apps.travelog.services.get_redis_client'):
            PublishingService.publish_journal(journal, self.user)

        # Access checker raises Http404
        def access_checker(j):
            raise Http404()

        items = TravelogPublicListBuilder.build(
            target_user=self.user,
            access_checker=access_checker
        )

        self.assertEqual(len(items), 0)

    def test_permission_denied_excludes_from_list(self):
        """PermissionDenied exception excludes journal from list."""
        journal = Journal.objects.create(
            trip=self.trip, title='Private Journal', visibility=JournalVisibility.PUBLIC
        )
        JournalEntry.objects.create(
            journal=journal, date=date(2024, 5, 1), title='Day', text='Content'
        )

        with patch('tt.apps.travelog.services.get_redis_client'):
            PublishingService.publish_journal(journal, self.user)

        # Access checker raises PermissionDenied
        def access_checker(j):
            raise PermissionDenied()

        items = TravelogPublicListBuilder.build(
            target_user=self.user,
            access_checker=access_checker
        )

        self.assertEqual(len(items), 0)


class TestTravelogPublicListBuilderDisplayImage(TransactionTestCase):
    """Test display image selection logic."""

    def setUp(self):
        """Set up test fixtures."""
        from django.core.files.base import ContentFile
        from tt.apps.images.models import TripImage

        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.trip = TripSyntheticData.create_test_trip(
            user=self.user,
            title='Test Trip'
        )

        # Create test images
        self.prologue_image = TripImage.objects.create(uploaded_by=self.user)
        self.prologue_image.web_image.save('prologue.jpg', ContentFile(b'img1'), save=True)

        self.dated_image = TripImage.objects.create(uploaded_by=self.user)
        self.dated_image.web_image.save('dated.jpg', ContentFile(b'img2'), save=True)

    def test_prefers_journal_reference_image(self):
        """Journal reference_image takes precedence over entry images."""
        from django.core.files.base import ContentFile
        from tt.apps.images.models import TripImage

        journal_image = TripImage.objects.create(uploaded_by=self.user)
        journal_image.web_image.save('journal.jpg', ContentFile(b'img'), save=True)

        journal = Journal.objects.create(
            trip=self.trip,
            title='Journal with Image',
            visibility=JournalVisibility.PUBLIC,
            reference_image=journal_image
        )
        JournalEntry.objects.create(
            journal=journal,
            date=date(2024, 5, 1),
            title='Day',
            text='Content',
            reference_image=self.dated_image
        )

        with patch('tt.apps.travelog.services.get_redis_client'):
            PublishingService.publish_journal(journal, self.user)

        items = TravelogPublicListBuilder.build(
            target_user=self.user,
            access_checker=lambda j: None
        )

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].display_image, journal_image)

    def test_prefers_dated_entry_over_special_entry(self):
        """Dated entry images are preferred over prologue/epilogue images."""
        journal = Journal.objects.create(
            trip=self.trip,
            title='Mixed Entries',
            visibility=JournalVisibility.PUBLIC
        )

        # Create prologue with image first (lower order)
        JournalEntry.objects.create(
            journal=journal,
            date=PROLOGUE_DATE,
            title='Prologue',
            text='Intro',
            reference_image=self.prologue_image
        )
        # Create dated entry with image
        JournalEntry.objects.create(
            journal=journal,
            date=date(2024, 5, 1),
            title='Day 1',
            text='Content',
            reference_image=self.dated_image
        )

        with patch('tt.apps.travelog.services.get_redis_client'):
            PublishingService.publish_journal(journal, self.user)

        items = TravelogPublicListBuilder.build(
            target_user=self.user,
            access_checker=lambda j: None
        )

        self.assertEqual(len(items), 1)
        # Should prefer dated entry image over prologue image
        self.assertEqual(items[0].display_image, self.dated_image)

    def test_falls_back_to_special_entry_image(self):
        """Uses special entry image when no dated entries have images."""
        journal = Journal.objects.create(
            trip=self.trip,
            title='Special Only Images',
            visibility=JournalVisibility.PUBLIC
        )

        # Prologue with image
        JournalEntry.objects.create(
            journal=journal,
            date=PROLOGUE_DATE,
            title='Prologue',
            text='Intro',
            reference_image=self.prologue_image
        )
        # Dated entry without image
        JournalEntry.objects.create(
            journal=journal,
            date=date(2024, 5, 1),
            title='Day 1',
            text='Content'
        )

        with patch('tt.apps.travelog.services.get_redis_client'):
            PublishingService.publish_journal(journal, self.user)

        items = TravelogPublicListBuilder.build(
            target_user=self.user,
            access_checker=lambda j: None
        )

        self.assertEqual(len(items), 1)
        # Should fall back to prologue image
        self.assertEqual(items[0].display_image, self.prologue_image)
