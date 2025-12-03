"""
Tests for trip services, including TripOverviewBuilder.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model

from tt.apps.journal.models import Journal
from tt.apps.journal.enums import JournalVisibility
from tt.apps.members.models import TripMember
from tt.apps.travelog.models import Travelog
from tt.apps.trips.enums import TripPermissionLevel, TripStatus
from tt.apps.trips.services import TripOverviewBuilder
from tt.apps.trips.tests.synthetic_data import TripSyntheticData

User = get_user_model()


class TripOverviewBuilderTestCase(TestCase):
    """Tests for TripOverviewBuilder service."""

    def setUp(self):
        """Set up test fixtures."""
        self.owner = User.objects.create_user(
            email='owner@example.com',
            password='testpass123'
        )
        self.viewer = User.objects.create_user(
            email='viewer@example.com',
            password='testpass123'
        )
        self.trip = TripSyntheticData.create_test_trip(
            user=self.owner,
            title='Test Trip',
            trip_status=TripStatus.CURRENT,
        )
        self.owner_member = TripMember.objects.get(trip=self.trip, user=self.owner)
        self.viewer_member = TripSyntheticData.add_trip_member(
            trip=self.trip,
            user=self.viewer,
            permission_level=TripPermissionLevel.VIEWER,
            added_by=self.owner,
        )

    # Editor Tests

    def test_editor_without_journal_shows_create_button(self):
        """Editor without journal should see create button."""
        overview = TripOverviewBuilder.build(
            trip=self.trip,
            journal=None,
            request_member=self.owner_member,
        )

        section = overview.journal_section
        self.assertTrue(section.show_editor_create_button)

    def test_editor_with_journal_shows_edit_button(self):
        """Editor with journal should see edit button."""
        journal = Journal.objects.create(
            trip=self.trip,
            title='Test Journal',
            visibility=JournalVisibility.PRIVATE,
        )

        overview = TripOverviewBuilder.build(
            trip=self.trip,
            journal=journal,
            request_member=self.owner_member,
        )

        section = overview.journal_section
        self.assertFalse(section.show_editor_create_button)

    # Viewer Tests

    def test_viewer_without_journal_shows_no_journal_alert(self):
        """Viewer without journal should see no journal alert."""
        overview = TripOverviewBuilder.build(
            trip=self.trip,
            journal=None,
            request_member=self.viewer_member,
        )

        section = overview.journal_section
        self.assertFalse(section.show_editor_create_button)

    def test_viewer_with_unpublished_journal_shows_unpublished_alert(self):
        """Viewer with unpublished journal should see unpublished alert."""
        journal = Journal.objects.create(
            trip=self.trip,
            title='Test Journal',
            visibility=JournalVisibility.PRIVATE,
        )

        overview = TripOverviewBuilder.build(
            trip=self.trip,
            journal=journal,
            request_member=self.viewer_member,
        )

        section = overview.journal_section
        self.assertIsNotNone(section.draft_url)
        self.assertIn('version=draft', section.draft_url)

    def test_viewer_with_published_journal_shows_published_alert(self):
        """Viewer with published journal should see published alert."""
        journal = Journal.objects.create(
            trip=self.trip,
            title='Test Journal',
            visibility=JournalVisibility.PRIVATE,
        )
        # Create a published travelog (is_current=True marks it as current version)
        Travelog.objects.create(
            journal=journal,
            title='Test Journal',
            description='',
            version_number=1,
            published_by=self.owner,
            is_current=True,
        )

        overview = TripOverviewBuilder.build(
            trip=self.trip,
            journal=journal,
            request_member=self.viewer_member,
        )

        section = overview.journal_section
        self.assertIsNotNone(section.published_url)
        self.assertIsNotNone(section.publishing_status)
        self.assertTrue(section.publishing_status.has_published_version)

    def test_viewer_with_published_journal_with_changes_shows_draft_button(self):
        """Viewer with published journal with unpublished changes shows draft preview."""
        journal = Journal.objects.create(
            trip=self.trip,
            title='Updated Journal Title',  # Different from travelog title
            visibility=JournalVisibility.PRIVATE,
        )
        # Create a published travelog with original title (is_current=True marks it as current)
        Travelog.objects.create(
            journal=journal,
            title='Original Title',
            description='',
            version_number=1,
            published_by=self.owner,
            is_current=True,
        )

        overview = TripOverviewBuilder.build(
            trip=self.trip,
            journal=journal,
            request_member=self.viewer_member,
        )

        section = overview.journal_section
        self.assertTrue(section.publishing_status.has_unpublished_changes)
        self.assertIsNotNone(section.draft_url)

    # URL Tests

    def test_urls_are_correctly_built(self):
        """Test that all URLs are correctly constructed."""
        journal = Journal.objects.create(
            trip=self.trip,
            title='Test Journal',
            visibility=JournalVisibility.PRIVATE,
        )

        overview = TripOverviewBuilder.build(
            trip=self.trip,
            journal=journal,
            request_member=self.owner_member,
        )

        section = overview.journal_section

        # Edit URL should point to journal home

        # Published URL should point to travelog
        self.assertIn('/travelog/', section.published_url)
        self.assertIn(str(journal.uuid), section.published_url)

        # Draft URL should have version=draft query param
        self.assertIn('/travelog/', section.draft_url)
        self.assertIn('version=draft', section.draft_url)
