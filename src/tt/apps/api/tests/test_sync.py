"""
Tests for sync infrastructure.

Focuses on high-value testing of:
- SyncableModel version increment behavior
- SyncDeletionLog creation on Location deletion
- SyncEnvelopeBuilder query logic
"""
import logging
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from tt.apps.api.enums import SyncObjectType
from tt.apps.api.models import SyncDeletionLog
from tt.apps.api.sync import SyncEnvelopeBuilder
from tt.apps.locations.models import Location
from tt.apps.trips.tests.synthetic_data import TripSyntheticData

logging.disable(logging.CRITICAL)

User = get_user_model()


# =============================================================================
# SyncableModel Version Increment Tests
# =============================================================================

class SyncableModelVersionIncrementTestCase(TestCase):
    """Test SyncableModel.save() version increment behavior."""

    @classmethod
    def setUpTestData(cls):
        """Create test user once for all tests."""
        cls.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpass123'
        )

    def test_trip_created_with_version_1(self):
        """Test new Trip is created with version=1."""
        trip = TripSyntheticData.create_test_trip(
            user=self.user,
            title='Version Test Trip'
        )

        self.assertEqual(trip.version, 1)

    def test_trip_version_increments_on_save(self):
        """Test Trip version increments when saved."""
        trip = TripSyntheticData.create_test_trip(
            user=self.user,
            title='Version Test Trip'
        )

        initial_version = trip.version
        self.assertEqual(initial_version, 1)

        # Modify and save
        trip.title = 'Updated Title'
        trip.save()

        # Verify version incremented
        trip.refresh_from_db()
        self.assertEqual(trip.version, 2)

    def test_trip_version_increments_multiple_times(self):
        """Test Trip version increments correctly over multiple saves."""
        trip = TripSyntheticData.create_test_trip(
            user=self.user,
            title='Version Test Trip'
        )

        for expected_version in range(2, 6):
            trip.title = f'Update {expected_version}'
            trip.save()
            trip.refresh_from_db()
            self.assertEqual(trip.version, expected_version)

    def test_location_created_with_version_1(self):
        """Test new Location is created with version=1."""
        trip = TripSyntheticData.create_test_trip(
            user=self.user,
            title='Test Trip'
        )
        location = Location.objects.create(
            trip=trip,
            title='Test Location'
        )

        self.assertEqual(location.version, 1)

    def test_location_version_increments_on_save(self):
        """Test Location version increments when saved."""
        trip = TripSyntheticData.create_test_trip(
            user=self.user,
            title='Test Trip'
        )
        location = Location.objects.create(
            trip=trip,
            title='Test Location'
        )

        initial_version = location.version
        location.title = 'Updated Location'
        location.save()

        location.refresh_from_db()
        self.assertEqual(location.version, initial_version + 1)


# =============================================================================
# SyncDeletionLog Tests
# =============================================================================

class SyncDeletionLogCreationTestCase(TestCase):
    """Test SyncDeletionLog creation on Location deletion."""

    @classmethod
    def setUpTestData(cls):
        """Create test user once for all tests."""
        cls.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpass123'
        )

    def test_location_deletion_creates_sync_deletion_log(self):
        """Test Location deletion creates SyncDeletionLog entry."""
        trip = TripSyntheticData.create_test_trip(
            user=self.user,
            title='Test Trip'
        )
        location = Location.objects.create(
            trip=trip,
            title='Test Location'
        )

        location_uuid = location.uuid
        trip_uuid = trip.uuid

        # Delete the location
        location.delete()

        # Verify SyncDeletionLog was created
        log_entry = SyncDeletionLog.objects.get(uuid=location_uuid)
        self.assertEqual(log_entry.object_type, SyncObjectType.LOCATION)
        self.assertEqual(log_entry.trip_uuid, trip_uuid)

    def test_location_deletion_log_has_correct_object_type(self):
        """Test SyncDeletionLog has LOCATION object_type."""
        trip = TripSyntheticData.create_test_trip(
            user=self.user,
            title='Test Trip'
        )
        location = Location.objects.create(
            trip=trip,
            title='Test Location'
        )
        location_uuid = location.uuid

        location.delete()

        log_entry = SyncDeletionLog.objects.get(uuid=location_uuid)
        self.assertEqual(log_entry.object_type, SyncObjectType.LOCATION)
        self.assertEqual(str(log_entry.object_type), 'location')

    def test_location_deletion_log_records_trip_uuid(self):
        """Test SyncDeletionLog correctly records the trip_uuid."""
        trip = TripSyntheticData.create_test_trip(
            user=self.user,
            title='Test Trip'
        )
        location = Location.objects.create(
            trip=trip,
            title='Test Location'
        )
        location_uuid = location.uuid
        expected_trip_uuid = trip.uuid

        location.delete()

        log_entry = SyncDeletionLog.objects.get(uuid=location_uuid)
        self.assertEqual(log_entry.trip_uuid, expected_trip_uuid)

    def test_multiple_location_deletions_create_separate_logs(self):
        """Test each location deletion creates its own log entry."""
        trip = TripSyntheticData.create_test_trip(
            user=self.user,
            title='Test Trip'
        )
        location1 = Location.objects.create(trip=trip, title='Location 1')
        location2 = Location.objects.create(trip=trip, title='Location 2')

        uuid1 = location1.uuid
        uuid2 = location2.uuid

        location1.delete()
        location2.delete()

        self.assertEqual(SyncDeletionLog.objects.count(), 2)
        self.assertTrue(SyncDeletionLog.objects.filter(uuid=uuid1).exists())
        self.assertTrue(SyncDeletionLog.objects.filter(uuid=uuid2).exists())


# =============================================================================
# SyncEnvelopeBuilder Tests
# =============================================================================

class SyncEnvelopeBuilderTripSyncTestCase(TestCase):
    """Test SyncEnvelopeBuilder trip sync behavior."""

    @classmethod
    def setUpTestData(cls):
        """Create test users and trips once for all tests."""
        cls.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpass123'
        )
        cls.other_user = User.objects.create_user(
            email='other@example.com',
            password='testpass123'
        )

    def test_build_returns_all_accessible_trips(self):
        """Test trip sync returns ALL accessible trips (presence-based detection)."""
        trip1 = TripSyntheticData.create_test_trip(
            user=self.user,
            title='Trip 1'
        )
        trip2 = TripSyntheticData.create_test_trip(
            user=self.user,
            title='Trip 2'
        )

        builder = SyncEnvelopeBuilder(self.user)
        envelope = builder.build()

        trip_updates = envelope['trip']['updates']
        self.assertEqual(len(trip_updates), 2)
        self.assertIn(str(trip1.uuid), trip_updates)
        self.assertIn(str(trip2.uuid), trip_updates)

    def test_build_returns_only_user_trips(self):
        """Test trip sync only returns trips accessible to the user."""
        user_trip = TripSyntheticData.create_test_trip(
            user=self.user,
            title='User Trip'
        )
        other_trip = TripSyntheticData.create_test_trip(
            user=self.other_user,
            title='Other User Trip'
        )

        builder = SyncEnvelopeBuilder(self.user)
        envelope = builder.build()

        trip_updates = envelope['trip']['updates']
        self.assertEqual(len(trip_updates), 1)
        self.assertIn(str(user_trip.uuid), trip_updates)
        self.assertNotIn(str(other_trip.uuid), trip_updates)

    def test_build_trips_filtered_by_since(self):
        """Test trip sync IS filtered by since timestamp (delta pattern)."""
        # Create old trip
        old_trip = TripSyntheticData.create_test_trip(
            user=self.user,
            title='Old Trip'
        )

        # Artificially set modified_datetime in past
        old_time = timezone.now() - timedelta(days=5)
        from tt.apps.trips.models import Trip
        Trip.objects.filter(pk=old_trip.pk).update(modified_datetime=old_time)

        # Create new trip
        new_trip = TripSyntheticData.create_test_trip(
            user=self.user,
            title='New Trip'
        )

        # Build with since after old trip
        since = timezone.now() - timedelta(days=1)
        builder = SyncEnvelopeBuilder(self.user, since=since)
        envelope = builder.build()

        # Only new trip should be returned (delta filtering)
        trip_updates = envelope['trip']['updates']
        self.assertEqual(len(trip_updates), 1)
        self.assertNotIn(str(old_trip.uuid), trip_updates)
        self.assertIn(str(new_trip.uuid), trip_updates)

    def test_build_includes_correct_metadata(self):
        """Test trip sync includes correct version, gmm_map_id, and title."""
        trip = TripSyntheticData.create_test_trip(
            user=self.user,
            title='Test Trip'
        )
        trip.gmm_map_id = 'test-map-123'
        trip.save()
        trip.refresh_from_db()

        builder = SyncEnvelopeBuilder(self.user)
        envelope = builder.build()

        trip_updates = envelope['trip']['updates']
        trip_data = trip_updates[str(trip.uuid)]
        self.assertEqual(trip_data['version'], trip.version)
        self.assertEqual(trip_data['gmm_map_id'], 'test-map-123')
        self.assertEqual(trip_data['title'], 'Test Trip')

    def test_build_trips_includes_past_trips(self):
        """Test trip sync includes PAST trips for GMM map index."""
        from tt.apps.trips.enums import TripStatus

        active_trip = TripSyntheticData.create_test_trip(
            user=self.user,
            title='Active Trip'
        )
        past_trip = TripSyntheticData.create_test_trip(
            user=self.user,
            title='Past Trip'
        )
        past_trip.trip_status = TripStatus.PAST
        past_trip.save()

        builder = SyncEnvelopeBuilder(self.user)
        envelope = builder.build()

        trip_updates = envelope['trip']['updates']
        self.assertEqual(len(trip_updates), 2)
        self.assertIn(str(active_trip.uuid), trip_updates)
        self.assertIn(str(past_trip.uuid), trip_updates)

    def test_build_trips_includes_deleted_array(self):
        """Test trip sync includes deleted array structure."""
        TripSyntheticData.create_test_trip(
            user=self.user,
            title='Test Trip'
        )

        builder = SyncEnvelopeBuilder(self.user)
        envelope = builder.build()

        self.assertIn('deleted', envelope['trip'])
        self.assertIsInstance(envelope['trip']['deleted'], list)

    def test_build_trips_includes_deleted_uuids_with_since(self):
        """Test trip sync includes deleted trip UUIDs when since provided."""
        trip = TripSyntheticData.create_test_trip(
            user=self.user,
            title='Test Trip'
        )
        trip_uuid = trip.uuid

        trip.delete()

        since = timezone.now() - timedelta(minutes=5)
        builder = SyncEnvelopeBuilder(self.user, since=since)
        envelope = builder.build()

        deleted_uuids = envelope['trip']['deleted']
        self.assertIn(str(trip_uuid), deleted_uuids)

    def test_build_trips_includes_deleted_uuids_without_since(self):
        """Test trip sync includes deleted trip UUIDs for full sync (no since)."""
        trip = TripSyntheticData.create_test_trip(
            user=self.user,
            title='Test Trip'
        )
        trip_uuid = trip.uuid

        trip.delete()

        # Full sync - no since timestamp
        builder = SyncEnvelopeBuilder(self.user, since=None)
        envelope = builder.build()

        deleted_uuids = envelope['trip']['deleted']
        self.assertIn(str(trip_uuid), deleted_uuids)

    def test_build_trips_gmm_map_id_none_when_unlinked(self):
        """Test trip sync returns None for gmm_map_id when trip not linked."""
        trip = TripSyntheticData.create_test_trip(
            user=self.user,
            title='Unlinked Trip'
        )

        builder = SyncEnvelopeBuilder(self.user)
        envelope = builder.build()

        trip_data = envelope['trip']['updates'][str(trip.uuid)]
        self.assertIsNone(trip_data['gmm_map_id'])


class SyncEnvelopeBuilderLocationSyncTestCase(TestCase):
    """Test SyncEnvelopeBuilder location sync behavior."""

    @classmethod
    def setUpTestData(cls):
        """Create test user and trip once for all tests."""
        cls.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpass123'
        )

    def test_build_without_trip_uuid_excludes_locations(self):
        """Test location sync is excluded when X-Sync-Trip not provided."""
        trip = TripSyntheticData.create_test_trip(
            user=self.user,
            title='Test Trip'
        )
        Location.objects.create(trip=trip, title='Test Location')

        builder = SyncEnvelopeBuilder(self.user, trip_uuid=None)
        envelope = builder.build()

        self.assertNotIn('location', envelope)

    def test_build_with_trip_uuid_includes_locations(self):
        """Test location sync is included when X-Sync-Trip provided."""
        trip = TripSyntheticData.create_test_trip(
            user=self.user,
            title='Test Trip'
        )
        location = Location.objects.create(trip=trip, title='Test Location')

        builder = SyncEnvelopeBuilder(self.user, trip_uuid=trip.uuid)
        envelope = builder.build()

        self.assertIn('location', envelope)
        location_versions = envelope['location']['versions']
        self.assertIn(str(location.uuid), location_versions)

    def test_build_location_filtered_by_since(self):
        """Test location sync is filtered by since timestamp."""
        trip = TripSyntheticData.create_test_trip(
            user=self.user,
            title='Test Trip'
        )

        # Create old location
        old_location = Location.objects.create(trip=trip, title='Old Location')

        # Artificially set modified_datetime in past
        old_time = timezone.now() - timedelta(days=5)
        Location.objects.filter(pk=old_location.pk).update(modified_datetime=old_time)

        # Create new location
        new_location = Location.objects.create(trip=trip, title='New Location')

        # Build with since after old location
        since = timezone.now() - timedelta(days=1)
        builder = SyncEnvelopeBuilder(self.user, since=since, trip_uuid=trip.uuid)
        envelope = builder.build()

        location_versions = envelope['location']['versions']
        # Only new location should be included
        self.assertNotIn(str(old_location.uuid), location_versions)
        self.assertIn(str(new_location.uuid), location_versions)

    def test_build_location_includes_deletions_with_since(self):
        """Test location sync includes deleted location UUIDs when since provided."""
        trip = TripSyntheticData.create_test_trip(
            user=self.user,
            title='Test Trip'
        )
        location = Location.objects.create(trip=trip, title='Test Location')
        location_uuid = location.uuid

        location.delete()

        since = timezone.now() - timedelta(minutes=5)
        builder = SyncEnvelopeBuilder(self.user, since=since, trip_uuid=trip.uuid)
        envelope = builder.build()

        deleted_uuids = envelope['location']['deleted']
        self.assertIn(str(location_uuid), deleted_uuids)

    def test_build_location_includes_deletions_without_since(self):
        """Test location sync includes deleted location UUIDs for full sync (no since)."""
        trip = TripSyntheticData.create_test_trip(
            user=self.user,
            title='Test Trip'
        )
        location = Location.objects.create(trip=trip, title='Test Location')
        location_uuid = location.uuid

        location.delete()

        # Full sync - no since timestamp
        builder = SyncEnvelopeBuilder(self.user, since=None, trip_uuid=trip.uuid)
        envelope = builder.build()

        deleted_uuids = envelope['location']['deleted']
        self.assertIn(str(location_uuid), deleted_uuids)

    def test_build_location_scoped_to_trip(self):
        """Test location sync is scoped to specified trip."""
        trip1 = TripSyntheticData.create_test_trip(
            user=self.user,
            title='Trip 1'
        )
        trip2 = TripSyntheticData.create_test_trip(
            user=self.user,
            title='Trip 2'
        )

        location1 = Location.objects.create(trip=trip1, title='Location 1')
        location2 = Location.objects.create(trip=trip2, title='Location 2')

        # Build for trip1 only
        builder = SyncEnvelopeBuilder(self.user, trip_uuid=trip1.uuid)
        envelope = builder.build()

        location_versions = envelope['location']['versions']
        self.assertIn(str(location1.uuid), location_versions)
        self.assertNotIn(str(location2.uuid), location_versions)


class SyncEnvelopeBuilderAsOfTestCase(TestCase):
    """Test SyncEnvelopeBuilder as_of timestamp behavior."""

    @classmethod
    def setUpTestData(cls):
        """Create test user once for all tests."""
        cls.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpass123'
        )

    def test_build_includes_as_of_timestamp(self):
        """Test envelope includes as_of ISO timestamp."""
        builder = SyncEnvelopeBuilder(self.user)
        before = timezone.now()
        envelope = builder.build()
        after = timezone.now()

        self.assertIn('as_of', envelope)
        # Parse the ISO timestamp
        from datetime import datetime
        as_of = datetime.fromisoformat(envelope['as_of'].replace('Z', '+00:00'))
        self.assertGreaterEqual(as_of.timestamp(), before.timestamp())
        self.assertLessEqual(as_of.timestamp(), after.timestamp())
