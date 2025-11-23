"""
Tests for journal publishing status helpers.

This module tests the PublishingStatusHelper class which determines
publishing status and counts unpublished changes by comparing journal
entries with travelog entries.
"""
import logging
from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from tt.apps.journal.models import Journal, JournalEntry
from tt.apps.journal.schemas import PublishingStatusHelper, PublishingStatus
from tt.apps.journal.enums import JournalVisibility
from tt.apps.trips.enums import TripStatus
from tt.apps.trips.tests.synthetic_data import TripSyntheticData
from tt.apps.travelog.models import Travelog, TravelogEntry

User = get_user_model()
logging.disable(logging.CRITICAL)


class PublishingStatusHelperTestCase(TestCase):
    """Tests for PublishingStatusHelper class."""

    def setUp(self):
        """Set up test fixtures."""
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

    def test_unpublished_journal(self):
        """Test status for journal that has never been published."""
        status = PublishingStatusHelper.get_publishing_status(self.journal)

        self.assertIsNone(status.current_published_version)
        self.assertFalse(status.has_unpublished_changes)
        self.assertFalse(status.has_published_version)
        self.assertTrue(status.is_unpublished)
        self.assertFalse(status.is_published_with_changes)
        self.assertFalse(status.is_published_without_changes)

    def test_published_no_changes(self):
        """Test status for published journal with no unpublished changes."""
        # Create journal entries
        entry1 = JournalEntry.objects.create(
            journal=self.journal,
            date=date(2025, 1, 1),
            title='Day 1',
            text='<p>First day content</p>',
            timezone='UTC',
            modified_by=self.user,
        )
        entry2 = JournalEntry.objects.create(
            journal=self.journal,
            date=date(2025, 1, 2),
            title='Day 2',
            text='<p>Second day content</p>',
            timezone='UTC',
            modified_by=self.user,
        )

        # Create published version with matching content
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
            reference_image=entry1.reference_image,
        )
        TravelogEntry.objects.create(
            travelog=travelog,
            source_entry=entry2,
            date=entry2.date,
            title=entry2.title,
            text=entry2.text,
            timezone=entry2.timezone,
            reference_image=entry2.reference_image,
        )

        status = PublishingStatusHelper.get_publishing_status(self.journal)

        self.assertEqual(status.current_published_version, travelog)
        self.assertFalse(status.has_unpublished_changes)
        self.assertTrue(status.has_published_version)
        self.assertFalse(status.is_unpublished)
        self.assertFalse(status.is_published_with_changes)
        self.assertTrue(status.is_published_without_changes)

    def test_published_with_new_entry(self):
        """Test status when a new entry has been added after publishing."""
        # Create and publish one entry
        entry1 = JournalEntry.objects.create(
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
            source_entry=entry1,
            date=entry1.date,
            title=entry1.title,
            text=entry1.text,
            timezone=entry1.timezone,
        )

        # Add a new entry after publishing
        JournalEntry.objects.create(
            journal=self.journal,
            date=date(2025, 1, 2),
            title='Day 2',
            text='<p>Second day content</p>',
            timezone='UTC',
            modified_by=self.user,
        )

        status = PublishingStatusHelper.get_publishing_status(self.journal)

        self.assertEqual(status.current_published_version, travelog)
        self.assertTrue(status.has_unpublished_changes)
        self.assertTrue(status.has_published_version)
        self.assertTrue(status.is_published_with_changes)
        self.assertFalse(status.is_published_without_changes)

    def test_published_with_modified_entry_text(self):
        """Test status when entry text has been modified after publishing."""
        entry1 = JournalEntry.objects.create(
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
            source_entry=entry1,
            date=entry1.date,
            title=entry1.title,
            text=entry1.text,
            timezone=entry1.timezone,
        )

        # Modify the entry text
        entry1.text = '<p>Modified content</p>'
        entry1.save()

        status = PublishingStatusHelper.get_publishing_status(self.journal)

        self.assertTrue(status.has_unpublished_changes)
        self.assertTrue(status.is_published_with_changes)

    def test_published_with_modified_entry_title(self):
        """Test status when entry title has been modified after publishing."""
        entry1 = JournalEntry.objects.create(
            journal=self.journal,
            date=date(2025, 1, 1),
            title='Original Title',
            text='<p>Content</p>',
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

        # Modify the entry title
        entry1.title = 'Modified Title'
        entry1.save()

        status = PublishingStatusHelper.get_publishing_status(self.journal)

        self.assertTrue(status.has_unpublished_changes)
        self.assertTrue(status.is_published_with_changes)

    def test_published_with_modified_entry_timezone(self):
        """Test status when entry timezone has been modified after publishing."""
        entry1 = JournalEntry.objects.create(
            journal=self.journal,
            date=date(2025, 1, 1),
            title='Day 1',
            text='<p>Content</p>',
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

        # Modify the entry timezone
        entry1.timezone = 'America/New_York'
        entry1.save()

        status = PublishingStatusHelper.get_publishing_status(self.journal)

        self.assertTrue(status.has_unpublished_changes)
        self.assertTrue(status.is_published_with_changes)

    def test_published_with_deleted_entry(self):
        """Test status when an entry has been deleted after publishing."""
        entry1 = JournalEntry.objects.create(
            journal=self.journal,
            date=date(2025, 1, 1),
            title='Day 1',
            text='<p>Content</p>',
            timezone='UTC',
            modified_by=self.user,
        )
        entry2 = JournalEntry.objects.create(
            journal=self.journal,
            date=date(2025, 1, 2),
            title='Day 2',
            text='<p>Content</p>',
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
        TravelogEntry.objects.create(
            travelog=travelog,
            source_entry=entry2,
            date=entry2.date,
            title=entry2.title,
            text=entry2.text,
            timezone=entry2.timezone,
        )

        # Delete one entry
        entry2.delete()

        status = PublishingStatusHelper.get_publishing_status(self.journal)

        self.assertTrue(status.has_unpublished_changes)
        self.assertTrue(status.is_published_with_changes)

    def test_published_with_multiple_changes(self):
        """Test status with multiple types of changes."""
        # Create initial entries and publish
        entry1 = JournalEntry.objects.create(
            journal=self.journal,
            date=date(2025, 1, 1),
            title='Day 1',
            text='<p>Original content</p>',
            timezone='UTC',
            modified_by=self.user,
        )
        entry2 = JournalEntry.objects.create(
            journal=self.journal,
            date=date(2025, 1, 2),
            title='Day 2',
            text='<p>Second day</p>',
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
        TravelogEntry.objects.create(
            travelog=travelog,
            source_entry=entry2,
            date=entry2.date,
            title=entry2.title,
            text=entry2.text,
            timezone=entry2.timezone,
        )

        # Make multiple changes:
        # 1. Modify entry1 text
        entry1.text = '<p>Modified content</p>'
        entry1.save()

        # 2. Delete entry2
        entry2.delete()

        # 3. Add new entry3
        JournalEntry.objects.create(
            journal=self.journal,
            date=date(2025, 1, 3),
            title='Day 3',
            text='<p>New entry</p>',
            timezone='UTC',
            modified_by=self.user,
        )

        status = PublishingStatusHelper.get_publishing_status(self.journal)

        # Should detect that changes exist
        self.assertTrue(status.has_unpublished_changes)
        self.assertTrue(status.is_published_with_changes)

    def test_published_only_non_current_version(self):
        """Test that only is_current=True travelog is used for status."""
        entry1 = JournalEntry.objects.create(
            journal=self.journal,
            date=date(2025, 1, 1),
            title='Day 1',
            text='<p>Content</p>',
            timezone='UTC',
            modified_by=self.user,
        )

        # Create old version (not current)
        old_travelog = Travelog.objects.create(
            journal=self.journal,
            version_number=1,
            is_current=False,
            title=self.journal.title,
            description=self.journal.description,
            published_by=self.user,
        )
        TravelogEntry.objects.create(
            travelog=old_travelog,
            source_entry=entry1,
            date=entry1.date,
            title=entry1.title,
            text='<p>Old content</p>',
            timezone=entry1.timezone,
        )

        status = PublishingStatusHelper.get_publishing_status(self.journal)

        # Should treat as unpublished since no current version exists
        self.assertIsNone(status.current_published_version)
        self.assertFalse(status.has_published_version)
        self.assertTrue(status.is_unpublished)


class PublishingStatusDataclassTestCase(TestCase):
    """Tests for PublishingStatus dataclass properties."""

    def test_unpublished_properties(self):
        """Test properties for unpublished state."""
        status = PublishingStatus(
            current_published_version=None,
            has_unpublished_changes=False,
            has_published_version=False,
        )

        self.assertTrue(status.is_unpublished)
        self.assertFalse(status.is_published_with_changes)
        self.assertFalse(status.is_published_without_changes)

    def test_published_without_changes_properties(self):
        """Test properties for published without changes state."""
        status = PublishingStatus(
            current_published_version='mock_travelog',  # Mock object
            has_unpublished_changes=False,
            has_published_version=True,
        )

        self.assertFalse(status.is_unpublished)
        self.assertFalse(status.is_published_with_changes)
        self.assertTrue(status.is_published_without_changes)

    def test_published_with_changes_properties(self):
        """Test properties for published with changes state."""
        status = PublishingStatus(
            current_published_version='mock_travelog',  # Mock object
            has_unpublished_changes=True,
            has_published_version=True,
        )

        self.assertFalse(status.is_unpublished)
        self.assertTrue(status.is_published_with_changes)
        self.assertFalse(status.is_published_without_changes)
