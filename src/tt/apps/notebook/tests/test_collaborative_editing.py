"""
Integration tests for collaborative note editing with optimistic locking.

These tests validate the end-to-end functionality of the optimistic locking
implementation for notebook entries, including:
- Version tracking and incrementing
- Conflict detection between multiple users
- Conflict resolution workflows
- Permission-based access control
- Edge cases and error handling

Tests use real database operations following the project's testing philosophy.
"""
import json
from datetime import date
from threading import Thread
from time import sleep

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse

from tt.apps.trips.enums import TripPermissionLevel, TripStatus
from tt.apps.trips.tests.synthetic_data import TripSyntheticData
from tt.apps.notebook.models import NotebookEntry

User = get_user_model()


class CollaborativeEditingVersionTrackingTests(TestCase):
    """Tests for basic version tracking functionality across the request/response cycle."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.trip = TripSyntheticData.create_test_trip(
            user=self.user,
            title='Test Trip',
            trip_status=TripStatus.UPCOMING
        )

    def test_new_entry_starts_with_version_one(self):
        """Test that newly created entries start with version 1."""
        self.client.force_login(self.user)
        new_url = reverse('notebook_new', kwargs={'trip_id': self.trip.pk})

        # Create new entry
        response = self.client.get(new_url)
        self.assertEqual(response.status_code, 302)

        # Verify database state
        entry = NotebookEntry.objects.get(trip=self.trip)
        self.assertEqual(entry.edit_version, 1)
        self.assertEqual(entry.text, '')

    def test_entry_version_persists_across_page_loads(self):
        """Test that version field persists correctly in database."""
        entry = NotebookEntry.objects.create(
            trip=self.trip,
            date=date(2024, 1, 15),
            text='Original text',
            edit_version=1
        )

        # Manually update version
        entry.edit_version = 5
        entry.save()

        # Verify persistence
        entry.refresh_from_db()
        self.assertEqual(entry.edit_version, 5)

    def test_successful_autosave_increments_version(self):
        """Test that successful auto-save increments version from N to N+1."""
        entry = NotebookEntry.objects.create(
            trip=self.trip,
            date=date(2024, 1, 15),
            text='Version 1 text',
            edit_version=1
        )
        autosave_url = reverse('notebook_autosave', kwargs={
            'trip_id': self.trip.pk,
            'entry_pk': entry.pk
        })

        self.client.force_login(self.user)

        # Save with version 1
        response = self.client.post(
            autosave_url,
            json.dumps({'text': 'Version 2 text', 'version': 1}),
            content_type='application/json'
        )

        # Verify response
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['version'], 2)

        # Verify database state
        entry.refresh_from_db()
        self.assertEqual(entry.edit_version, 2)
        self.assertEqual(entry.text, 'Version 2 text')

    def test_sequential_saves_increment_version_correctly(self):
        """Test that multiple sequential saves increment version correctly (1->2->3->4)."""
        entry = NotebookEntry.objects.create(
            trip=self.trip,
            date=date(2024, 1, 15),
            text='Version 1',
            edit_version=1
        )
        autosave_url = reverse('notebook_autosave', kwargs={
            'trip_id': self.trip.pk,
            'entry_pk': entry.pk
        })

        self.client.force_login(self.user)

        # First save: 1 -> 2
        response1 = self.client.post(
            autosave_url,
            json.dumps({'text': 'Version 2', 'version': 1}),
            content_type='application/json'
        )
        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response1.json()['version'], 2)

        # Second save: 2 -> 3
        response2 = self.client.post(
            autosave_url,
            json.dumps({'text': 'Version 3', 'version': 2}),
            content_type='application/json'
        )
        self.assertEqual(response2.status_code, 200)
        self.assertEqual(response2.json()['version'], 3)

        # Third save: 3 -> 4
        response3 = self.client.post(
            autosave_url,
            json.dumps({'text': 'Version 4', 'version': 3}),
            content_type='application/json'
        )
        self.assertEqual(response3.status_code, 200)
        self.assertEqual(response3.json()['version'], 4)

        # Verify final database state
        entry.refresh_from_db()
        self.assertEqual(entry.edit_version, 4)
        self.assertEqual(entry.text, 'Version 4')

    def test_version_returned_in_autosave_response(self):
        """Test that auto-save response includes version and modified_datetime."""
        entry = NotebookEntry.objects.create(
            trip=self.trip,
            date=date(2024, 1, 15),
            text='Test',
            edit_version=1
        )
        autosave_url = reverse('notebook_autosave', kwargs={
            'trip_id': self.trip.pk,
            'entry_pk': entry.pk
        })

        self.client.force_login(self.user)
        response = self.client.post(
            autosave_url,
            json.dumps({'text': 'Updated', 'version': 1}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('version', data)
        self.assertIn('modified_datetime', data)
        self.assertIn('status', data)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['version'], 2)


class CollaborativeEditingConflictDetectionTests(TestCase):
    """Tests for detecting version conflicts when multiple users edit the same entry."""

    def setUp(self):
        self.user_a = User.objects.create_user(
            email='user_a@example.com',
            password='testpass123'
        )
        self.user_b = User.objects.create_user(
            email='user_b@example.com',
            password='testpass123'
        )
        self.trip = TripSyntheticData.create_test_trip(
            user=self.user_a,
            title='Shared Trip',
            trip_status=TripStatus.UPCOMING
        )
        # Add user_b as editor
        TripSyntheticData.add_trip_member(
            trip=self.trip,
            user=self.user_b,
            permission_level=TripPermissionLevel.EDITOR,
            added_by=self.user_a
        )

    def test_concurrent_edit_conflict_detected(self):
        """
        Test classic concurrent editing conflict scenario:
        - User A and B both load entry at version 1
        - User A saves successfully (version becomes 2)
        - User B tries to save with stale version 1 -> 409 conflict
        """
        entry = NotebookEntry.objects.create(
            trip=self.trip,
            date=date(2024, 1, 15),
            text='Original text',
            edit_version=1
        )
        autosave_url = reverse('notebook_autosave', kwargs={
            'trip_id': self.trip.pk,
            'entry_pk': entry.pk
        })

        # Both users load entry (version 1)
        client_a = Client()
        client_b = Client()
        client_a.force_login(self.user_a)
        client_b.force_login(self.user_b)

        # User A saves successfully
        response_a = client_a.post(
            autosave_url,
            json.dumps({'text': 'User A changes', 'version': 1}),
            content_type='application/json'
        )
        self.assertEqual(response_a.status_code, 200)
        self.assertEqual(response_a.json()['version'], 2)

        # User B tries to save with stale version (conflict)
        response_b = client_b.post(
            autosave_url,
            json.dumps({'text': 'User B changes', 'version': 1}),
            content_type='application/json'
        )

        # Verify conflict response
        self.assertEqual(response_b.status_code, 409)
        conflict_data = response_b.json()
        self.assertEqual(conflict_data['status'], 'conflict')
        self.assertEqual(conflict_data['server_version'], 2)
        self.assertEqual(conflict_data['server_text'], 'User A changes')
        self.assertIn('server_modified_at', conflict_data)
        self.assertIn('message', conflict_data)

        # Verify database state (User A's changes preserved)
        entry.refresh_from_db()
        self.assertEqual(entry.text, 'User A changes')
        self.assertEqual(entry.edit_version, 2)

    def test_stale_version_prevents_data_corruption(self):
        """Test that stale version number prevents overwriting newer data."""
        entry = NotebookEntry.objects.create(
            trip=self.trip,
            date=date(2024, 1, 15),
            text='Version 1',
            edit_version=1
        )
        autosave_url = reverse('notebook_autosave', kwargs={
            'trip_id': self.trip.pk,
            'entry_pk': entry.pk
        })

        client = Client()
        client.force_login(self.user_a)

        # Advance version to 5
        entry.text = 'Version 5 - Latest'
        entry.edit_version = 5
        entry.save()

        # Try to save with stale version 2
        response = client.post(
            autosave_url,
            json.dumps({'text': 'Stale update', 'version': 2}),
            content_type='application/json'
        )

        # Verify conflict detected
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['server_version'], 5)

        # Verify database not corrupted
        entry.refresh_from_db()
        self.assertEqual(entry.text, 'Version 5 - Latest')
        self.assertEqual(entry.edit_version, 5)

    def test_conflict_includes_server_state(self):
        """Test that conflict response includes complete server state for resolution."""
        entry = NotebookEntry.objects.create(
            trip=self.trip,
            date=date(2024, 1, 15),
            text='Server version',
            edit_version=3
        )
        autosave_url = reverse('notebook_autosave', kwargs={
            'trip_id': self.trip.pk,
            'entry_pk': entry.pk
        })

        client = Client()
        client.force_login(self.user_a)

        # Try to save with stale version
        response = client.post(
            autosave_url,
            json.dumps({'text': 'My update', 'version': 2}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 409)
        data = response.json()

        # Verify all required fields for conflict resolution
        self.assertEqual(data['status'], 'conflict')
        self.assertEqual(data['server_version'], 3)
        self.assertEqual(data['server_text'], 'Server version')
        self.assertIn('server_modified_at', data)
        self.assertIn('message', data)
        self.assertIsInstance(data['server_modified_at'], str)

    def test_version_mismatch_by_one_triggers_conflict(self):
        """Test that even a version mismatch by 1 triggers conflict."""
        entry = NotebookEntry.objects.create(
            trip=self.trip,
            date=date(2024, 1, 15),
            text='Version 10',
            edit_version=10
        )
        autosave_url = reverse('notebook_autosave', kwargs={
            'trip_id': self.trip.pk,
            'entry_pk': entry.pk
        })

        client = Client()
        client.force_login(self.user_a)

        # Try to save with version 9 (off by 1)
        response = client.post(
            autosave_url,
            json.dumps({'text': 'Update', 'version': 9}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['server_version'], 10)


class CollaborativeEditingConflictResolutionTests(TestCase):
    """Tests for resolving version conflicts and continuing normal operation."""

    def setUp(self):
        self.user_a = User.objects.create_user(
            email='user_a@example.com',
            password='testpass123'
        )
        self.user_b = User.objects.create_user(
            email='user_b@example.com',
            password='testpass123'
        )
        self.trip = TripSyntheticData.create_test_trip(
            user=self.user_a,
            title='Shared Trip',
            trip_status=TripStatus.UPCOMING
        )
        TripSyntheticData.add_trip_member(
            trip=self.trip,
            user=self.user_b,
            permission_level=TripPermissionLevel.EDITOR,
            added_by=self.user_a
        )

    def test_resolution_with_correct_version_succeeds(self):
        """
        Test complete conflict resolution workflow:
        - User B encounters conflict
        - User B retries with correct version from conflict response
        - Save succeeds with incremented version
        """
        entry = NotebookEntry.objects.create(
            trip=self.trip,
            date=date(2024, 1, 15),
            text='Original',
            edit_version=1
        )
        autosave_url = reverse('notebook_autosave', kwargs={
            'trip_id': self.trip.pk,
            'entry_pk': entry.pk
        })

        client_a = Client()
        client_b = Client()
        client_a.force_login(self.user_a)
        client_b.force_login(self.user_b)

        # User A saves successfully
        client_a.post(
            autosave_url,
            json.dumps({'text': 'User A changes', 'version': 1}),
            content_type='application/json'
        )

        # User B gets conflict
        response_conflict = client_b.post(
            autosave_url,
            json.dumps({'text': 'User B changes', 'version': 1}),
            content_type='application/json'
        )
        self.assertEqual(response_conflict.status_code, 409)
        server_version = response_conflict.json()['server_version']

        # User B resolves with correct version
        response_resolved = client_b.post(
            autosave_url,
            json.dumps({'text': 'User B resolved changes', 'version': server_version}),
            content_type='application/json'
        )

        # Verify resolution succeeded
        self.assertEqual(response_resolved.status_code, 200)
        self.assertEqual(response_resolved.json()['version'], 3)

        # Verify database state
        entry.refresh_from_db()
        self.assertEqual(entry.text, 'User B resolved changes')
        self.assertEqual(entry.edit_version, 3)

    def test_version_continues_incrementing_after_conflict(self):
        """Test that version numbering continues correctly after conflict resolution."""
        entry = NotebookEntry.objects.create(
            trip=self.trip,
            date=date(2024, 1, 15),
            text='Version 1',
            edit_version=1
        )
        autosave_url = reverse('notebook_autosave', kwargs={
            'trip_id': self.trip.pk,
            'entry_pk': entry.pk
        })

        client_a = Client()
        client_b = Client()
        client_a.force_login(self.user_a)
        client_b.force_login(self.user_b)

        # User A: 1 -> 2
        client_a.post(
            autosave_url,
            json.dumps({'text': 'Version 2', 'version': 1}),
            content_type='application/json'
        )

        # User B: conflict at version 1
        client_b.post(
            autosave_url,
            json.dumps({'text': 'Conflict', 'version': 1}),
            content_type='application/json'
        )

        # User B: resolves 2 -> 3
        response_b = client_b.post(
            autosave_url,
            json.dumps({'text': 'Version 3', 'version': 2}),
            content_type='application/json'
        )
        self.assertEqual(response_b.json()['version'], 3)

        # User A: continues 3 -> 4
        response_a = client_a.post(
            autosave_url,
            json.dumps({'text': 'Version 4', 'version': 3}),
            content_type='application/json'
        )
        self.assertEqual(response_a.json()['version'], 4)

        # Verify database
        entry.refresh_from_db()
        self.assertEqual(entry.edit_version, 4)

    def test_multiple_conflicts_resolved_sequentially(self):
        """Test that multiple conflicts can be resolved in sequence."""
        entry = NotebookEntry.objects.create(
            trip=self.trip,
            date=date(2024, 1, 15),
            text='Start',
            edit_version=1
        )
        autosave_url = reverse('notebook_autosave', kwargs={
            'trip_id': self.trip.pk,
            'entry_pk': entry.pk
        })

        client_a = Client()
        client_b = Client()
        client_a.force_login(self.user_a)
        client_b.force_login(self.user_b)

        # First conflict cycle
        client_a.post(
            autosave_url,
            json.dumps({'text': 'A1', 'version': 1}),
            content_type='application/json'
        )
        conflict_1 = client_b.post(
            autosave_url,
            json.dumps({'text': 'B1', 'version': 1}),
            content_type='application/json'
        )
        self.assertEqual(conflict_1.status_code, 409)
        client_b.post(
            autosave_url,
            json.dumps({'text': 'B1-resolved', 'version': 2}),
            content_type='application/json'
        )

        # Second conflict cycle
        client_a.post(
            autosave_url,
            json.dumps({'text': 'A2', 'version': 3}),
            content_type='application/json'
        )
        conflict_2 = client_b.post(
            autosave_url,
            json.dumps({'text': 'B2', 'version': 3}),
            content_type='application/json'
        )
        self.assertEqual(conflict_2.status_code, 409)
        response_final = client_b.post(
            autosave_url,
            json.dumps({'text': 'B2-resolved', 'version': 4}),
            content_type='application/json'
        )

        # Verify final state
        self.assertEqual(response_final.status_code, 200)
        self.assertEqual(response_final.json()['version'], 5)
        entry.refresh_from_db()
        self.assertEqual(entry.edit_version, 5)


class CollaborativeEditingEdgeCasesTests(TestCase):
    """Tests for edge cases and error conditions in collaborative editing."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.trip = TripSyntheticData.create_test_trip(
            user=self.user,
            title='Test Trip',
            trip_status=TripStatus.UPCOMING
        )

    def test_backward_compatible_no_version_in_request(self):
        """Test that omitting version field still works (backward compatibility)."""
        entry = NotebookEntry.objects.create(
            trip=self.trip,
            date=date(2024, 1, 15),
            text='Original',
            edit_version=1
        )
        autosave_url = reverse('notebook_autosave', kwargs={
            'trip_id': self.trip.pk,
            'entry_pk': entry.pk
        })

        self.client.force_login(self.user)

        # Save without version field
        response = self.client.post(
            autosave_url,
            json.dumps({'text': 'Updated without version'}),
            content_type='application/json'
        )

        # Should succeed (no version check)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')
        self.assertIn('version', response.json())

        entry.refresh_from_db()
        self.assertEqual(entry.text, 'Updated without version')

    def test_null_version_treated_as_no_version(self):
        """Test that null version is treated as missing (backward compatible)."""
        entry = NotebookEntry.objects.create(
            trip=self.trip,
            date=date(2024, 1, 15),
            text='Original',
            edit_version=1
        )
        autosave_url = reverse('notebook_autosave', kwargs={
            'trip_id': self.trip.pk,
            'entry_pk': entry.pk
        })

        self.client.force_login(self.user)

        # Save with explicit null version
        response = self.client.post(
            autosave_url,
            json.dumps({'text': 'Updated', 'version': None}),
            content_type='application/json'
        )

        # Should succeed (null treated as no version check)
        self.assertEqual(response.status_code, 200)
        entry.refresh_from_db()
        self.assertEqual(entry.text, 'Updated')

    def test_zero_version_triggers_conflict_check(self):
        """Test that version=0 is treated as a version value (not null)."""
        entry = NotebookEntry.objects.create(
            trip=self.trip,
            date=date(2024, 1, 15),
            text='Original',
            edit_version=1
        )
        autosave_url = reverse('notebook_autosave', kwargs={
            'trip_id': self.trip.pk,
            'entry_pk': entry.pk
        })

        self.client.force_login(self.user)

        # Save with version=0 (mismatch with actual version 1)
        response = self.client.post(
            autosave_url,
            json.dumps({'text': 'Updated', 'version': 0}),
            content_type='application/json'
        )

        # Should trigger conflict
        self.assertEqual(response.status_code, 409)

    def test_rapid_sequential_autosaves_maintain_version_integrity(self):
        """Test that rapid sequential saves maintain version integrity."""
        entry = NotebookEntry.objects.create(
            trip=self.trip,
            date=date(2024, 1, 15),
            text='Start',
            edit_version=1
        )
        autosave_url = reverse('notebook_autosave', kwargs={
            'trip_id': self.trip.pk,
            'entry_pk': entry.pk
        })

        self.client.force_login(self.user)

        # Rapid sequential saves
        current_version = 1
        for i in range(10):
            response = self.client.post(
                autosave_url,
                json.dumps({'text': f'Version {i+2}', 'version': current_version}),
                content_type='application/json'
            )
            self.assertEqual(response.status_code, 200)
            current_version = response.json()['version']
            self.assertEqual(current_version, i + 2)

        # Verify final state
        entry.refresh_from_db()
        self.assertEqual(entry.edit_version, 11)
        self.assertEqual(entry.text, 'Version 11')

    def test_date_change_with_version_tracking(self):
        """Test that date changes work correctly with version tracking."""
        entry = NotebookEntry.objects.create(
            trip=self.trip,
            date=date(2024, 1, 15),
            text='Test',
            edit_version=1
        )
        autosave_url = reverse('notebook_autosave', kwargs={
            'trip_id': self.trip.pk,
            'entry_pk': entry.pk
        })

        self.client.force_login(self.user)

        # Change date with version tracking
        response = self.client.post(
            autosave_url,
            json.dumps({
                'text': 'Test',
                'date': '2024-01-20',
                'version': 1
            }),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['version'], 2)

        entry.refresh_from_db()
        self.assertEqual(entry.date, date(2024, 1, 20))
        self.assertEqual(entry.edit_version, 2)

    def test_date_conflict_with_version_tracking(self):
        """Test that date conflicts are detected independently from version conflicts."""
        # Create an entry for the target date to cause conflict
        NotebookEntry.objects.create(
            trip=self.trip,
            date=date(2024, 1, 15),
            text='Entry 1',
            edit_version=1
        )
        entry2 = NotebookEntry.objects.create(
            trip=self.trip,
            date=date(2024, 1, 20),
            text='Entry 2',
            edit_version=1
        )
        autosave_url = reverse('notebook_autosave', kwargs={
            'trip_id': self.trip.pk,
            'entry_pk': entry2.pk
        })

        self.client.force_login(self.user)

        # Try to change entry2's date to entry1's date (with correct version)
        response = self.client.post(
            autosave_url,
            json.dumps({
                'text': 'Entry 2',
                'date': '2024-01-15',
                'version': 1
            }),
            content_type='application/json'
        )

        # Should fail due to date conflict (not version conflict)
        self.assertEqual(response.status_code, 400)
        self.assertIn('already exists', response.json()['message'])

        # Verify entry2 unchanged
        entry2.refresh_from_db()
        self.assertEqual(entry2.date, date(2024, 1, 20))
        self.assertEqual(entry2.edit_version, 1)


class CollaborativeEditingPermissionIntegrationTests(TestCase):
    """Tests for version tracking integration with trip permission system."""

    def setUp(self):
        self.owner = User.objects.create_user(
            email='owner@example.com',
            password='testpass123'
        )
        self.editor = User.objects.create_user(
            email='editor@example.com',
            password='testpass123'
        )
        self.viewer = User.objects.create_user(
            email='viewer@example.com',
            password='testpass123'
        )
        self.outsider = User.objects.create_user(
            email='outsider@example.com',
            password='testpass123'
        )
        self.trip = TripSyntheticData.create_test_trip(
            user=self.owner,
            title='Shared Trip',
            trip_status=TripStatus.UPCOMING
        )
        TripSyntheticData.add_trip_member(
            trip=self.trip,
            user=self.editor,
            permission_level=TripPermissionLevel.EDITOR,
            added_by=self.owner
        )
        TripSyntheticData.add_trip_member(
            trip=self.trip,
            user=self.viewer,
            permission_level=TripPermissionLevel.VIEWER,
            added_by=self.owner
        )

    def test_owner_and_editor_can_trigger_version_conflicts(self):
        """Test that both owner and editor can participate in version conflicts."""
        entry = NotebookEntry.objects.create(
            trip=self.trip,
            date=date(2024, 1, 15),
            text='Original',
            edit_version=1
        )
        autosave_url = reverse('notebook_autosave', kwargs={
            'trip_id': self.trip.pk,
            'entry_pk': entry.pk
        })

        owner_client = Client()
        editor_client = Client()
        owner_client.force_login(self.owner)
        editor_client.force_login(self.editor)

        # Owner saves first
        response_owner = owner_client.post(
            autosave_url,
            json.dumps({'text': 'Owner changes', 'version': 1}),
            content_type='application/json'
        )
        self.assertEqual(response_owner.status_code, 200)

        # Editor gets conflict
        response_editor = editor_client.post(
            autosave_url,
            json.dumps({'text': 'Editor changes', 'version': 1}),
            content_type='application/json'
        )
        self.assertEqual(response_editor.status_code, 409)
        self.assertEqual(response_editor.json()['server_text'], 'Owner changes')

    def test_viewer_cannot_autosave(self):
        """Test that viewer cannot access auto-save endpoint."""
        entry = NotebookEntry.objects.create(
            trip=self.trip,
            date=date(2024, 1, 15),
            text='Original',
            edit_version=1
        )
        autosave_url = reverse('notebook_autosave', kwargs={
            'trip_id': self.trip.pk,
            'entry_pk': entry.pk
        })

        viewer_client = Client()
        viewer_client.force_login(self.viewer)

        # Viewer attempts to save
        response = viewer_client.post(
            autosave_url,
            json.dumps({'text': 'Viewer changes', 'version': 1}),
            content_type='application/json'
        )

        # Should be forbidden (permission check happens before version check)
        self.assertIn(response.status_code, [403, 404])

        # Verify entry unchanged
        entry.refresh_from_db()
        self.assertEqual(entry.text, 'Original')
        self.assertEqual(entry.edit_version, 1)

    def test_outsider_cannot_access_entry(self):
        """Test that users without trip access cannot access auto-save endpoint."""
        entry = NotebookEntry.objects.create(
            trip=self.trip,
            date=date(2024, 1, 15),
            text='Original',
            edit_version=1
        )
        autosave_url = reverse('notebook_autosave', kwargs={
            'trip_id': self.trip.pk,
            'entry_pk': entry.pk
        })

        outsider_client = Client()
        outsider_client.force_login(self.outsider)

        # Outsider attempts to save
        response = outsider_client.post(
            autosave_url,
            json.dumps({'text': 'Outsider changes', 'version': 1}),
            content_type='application/json'
        )

        # Should return 404 (not 403 to avoid information disclosure)
        self.assertEqual(response.status_code, 404)


class CollaborativeEditingRaceConditionTests(TransactionTestCase):
    """
    Tests for race condition handling using TransactionTestCase.

    These tests verify that the optimistic locking implementation
    properly handles true concurrent database access scenarios.
    """

    def setUp(self):
        self.user_a = User.objects.create_user(
            email='user_a@example.com',
            password='testpass123'
        )
        self.user_b = User.objects.create_user(
            email='user_b@example.com',
            password='testpass123'
        )
        self.trip = TripSyntheticData.create_test_trip(
            user=self.user_a,
            title='Test Trip',
            trip_status=TripStatus.UPCOMING
        )
        TripSyntheticData.add_trip_member(
            trip=self.trip,
            user=self.user_b,
            permission_level=TripPermissionLevel.EDITOR,
            added_by=self.user_a
        )

    def test_select_for_update_prevents_lost_updates(self):
        """
        Test that select_for_update() prevents lost updates in concurrent scenarios.

        This verifies that the database-level locking works correctly to ensure
        one transaction completes before the other begins.
        """
        entry = NotebookEntry.objects.create(
            trip=self.trip,
            date=date(2024, 1, 15),
            text='Original',
            edit_version=1
        )
        autosave_url = reverse('notebook_autosave', kwargs={
            'trip_id': self.trip.pk,
            'entry_pk': entry.pk
        })

        results = {'user_a': None, 'user_b': None}

        def save_as_user_a():
            client = Client()
            client.force_login(self.user_a)
            response = client.post(
                autosave_url,
                json.dumps({'text': 'User A changes', 'version': 1}),
                content_type='application/json'
            )
            results['user_a'] = response.status_code

        def save_as_user_b():
            # Small delay to ensure both threads hit the endpoint near-simultaneously
            sleep(0.01)
            client = Client()
            client.force_login(self.user_b)
            response = client.post(
                autosave_url,
                json.dumps({'text': 'User B changes', 'version': 1}),
                content_type='application/json'
            )
            results['user_b'] = response.status_code

        # Execute both requests in threads (simulating concurrent access)
        thread_a = Thread(target=save_as_user_a)
        thread_b = Thread(target=save_as_user_b)

        thread_a.start()
        thread_b.start()
        thread_a.join()
        thread_b.join()

        # Verify: one succeeded (200), one conflicted (409)
        status_codes = sorted([results['user_a'], results['user_b']])
        self.assertEqual(status_codes, [200, 409])

        # Verify database integrity
        entry.refresh_from_db()
        self.assertEqual(entry.edit_version, 2)
        self.assertIn(entry.text, ['User A changes', 'User B changes'])

    def test_atomic_version_increment_with_f_expression(self):
        """
        Test that F() expression ensures atomic version increment.

        This verifies that version increments happen atomically in the database,
        preventing race conditions in version numbering.
        """
        entry = NotebookEntry.objects.create(
            trip=self.trip,
            date=date(2024, 1, 15),
            text='Start',
            edit_version=1
        )
        autosave_url = reverse('notebook_autosave', kwargs={
            'trip_id': self.trip.pk,
            'entry_pk': entry.pk
        })

        client_a = Client()
        client_b = Client()
        client_a.force_login(self.user_a)
        client_b.force_login(self.user_b)

        # User A saves: 1 -> 2
        response_a1 = client_a.post(
            autosave_url,
            json.dumps({'text': 'A1', 'version': 1}),
            content_type='application/json'
        )
        self.assertEqual(response_a1.status_code, 200)
        self.assertEqual(response_a1.json()['version'], 2)

        # User B saves: 2 -> 3
        response_b1 = client_b.post(
            autosave_url,
            json.dumps({'text': 'B1', 'version': 2}),
            content_type='application/json'
        )
        self.assertEqual(response_b1.status_code, 200)
        self.assertEqual(response_b1.json()['version'], 3)

        # Verify no version gaps or duplicates
        entry.refresh_from_db()
        self.assertEqual(entry.edit_version, 3)


class CollaborativeEditingEndToEndTests(TestCase):
    """
    End-to-end integration tests simulating complete user workflows.

    These tests verify the entire flow from entry creation through
    conflict detection and resolution.
    """

    def setUp(self):
        self.user_a = User.objects.create_user(
            email='alice@example.com',
            password='testpass123'
        )
        self.user_b = User.objects.create_user(
            email='bob@example.com',
            password='testpass123'
        )
        self.trip = TripSyntheticData.create_test_trip(
            user=self.user_a,
            title='Alaska Adventure',
            trip_status=TripStatus.CURRENT
        )
        TripSyntheticData.add_trip_member(
            trip=self.trip,
            user=self.user_b,
            permission_level=TripPermissionLevel.EDITOR,
            added_by=self.user_a
        )

    def test_complete_collaborative_editing_workflow(self):
        """
        Test complete workflow: create entry, concurrent edits, conflict, resolution.

        This simulates the real-world scenario described in issue #22:
        - Alice creates a new entry
        - Alice and Bob both start editing
        - Alice saves first
        - Bob encounters conflict and resolves
        - Both continue editing without issues
        """
        client_alice = Client()
        client_bob = Client()
        client_alice.force_login(self.user_a)
        client_bob.force_login(self.user_b)

        # Alice creates new entry
        new_url = reverse('notebook_new', kwargs={'trip_id': self.trip.pk})
        response = client_alice.get(new_url)
        self.assertEqual(response.status_code, 302)

        entry = NotebookEntry.objects.get(trip=self.trip)
        self.assertEqual(entry.edit_version, 1)
        autosave_url = reverse('notebook_autosave', kwargs={
            'trip_id': self.trip.pk,
            'entry_pk': entry.pk
        })

        # Alice makes first edit
        response_a1 = client_alice.post(
            autosave_url,
            json.dumps({'text': 'Alice: Day 1 notes', 'version': 1}),
            content_type='application/json'
        )
        self.assertEqual(response_a1.status_code, 200)
        self.assertEqual(response_a1.json()['version'], 2)

        # Bob tries to edit with stale version (conflict)
        response_b_conflict = client_bob.post(
            autosave_url,
            json.dumps({'text': 'Bob: Day 1 notes', 'version': 1}),
            content_type='application/json'
        )
        self.assertEqual(response_b_conflict.status_code, 409)
        conflict_data = response_b_conflict.json()
        self.assertEqual(conflict_data['server_version'], 2)
        self.assertEqual(conflict_data['server_text'], 'Alice: Day 1 notes')

        # Bob resolves conflict with server version
        response_b_resolved = client_bob.post(
            autosave_url,
            json.dumps({
                'text': 'Alice: Day 1 notes\nBob: Additional details',
                'version': 2
            }),
            content_type='application/json'
        )
        self.assertEqual(response_b_resolved.status_code, 200)
        self.assertEqual(response_b_resolved.json()['version'], 3)

        # Alice continues editing with correct version
        response_a2 = client_alice.post(
            autosave_url,
            json.dumps({
                'text': 'Alice: Day 1 notes\nBob: Additional details\nAlice: More updates',
                'version': 3
            }),
            content_type='application/json'
        )
        self.assertEqual(response_a2.status_code, 200)
        self.assertEqual(response_a2.json()['version'], 4)

        # Verify final state
        entry.refresh_from_db()
        self.assertEqual(entry.edit_version, 4)
        self.assertIn('Alice', entry.text)
        self.assertIn('Bob', entry.text)

    def test_three_way_conflict_resolution(self):
        """
        Test scenario with three users editing concurrently.

        Verifies that the system handles multiple concurrent editors correctly.
        """
        user_c = User.objects.create_user(
            email='charlie@example.com',
            password='testpass123'
        )
        TripSyntheticData.add_trip_member(
            trip=self.trip,
            user=user_c,
            permission_level=TripPermissionLevel.EDITOR,
            added_by=self.user_a
        )

        entry = NotebookEntry.objects.create(
            trip=self.trip,
            date=date(2024, 1, 15),
            text='Original',
            edit_version=1
        )
        autosave_url = reverse('notebook_autosave', kwargs={
            'trip_id': self.trip.pk,
            'entry_pk': entry.pk
        })

        client_a = Client()
        client_b = Client()
        client_c = Client()
        client_a.force_login(self.user_a)
        client_b.force_login(self.user_b)
        client_c.force_login(user_c)

        # All three users read entry at version 1

        # User A saves successfully
        response_a = client_a.post(
            autosave_url,
            json.dumps({'text': 'User A changes', 'version': 1}),
            content_type='application/json'
        )
        self.assertEqual(response_a.status_code, 200)
        self.assertEqual(response_a.json()['version'], 2)

        # User B encounters conflict
        response_b = client_b.post(
            autosave_url,
            json.dumps({'text': 'User B changes', 'version': 1}),
            content_type='application/json'
        )
        self.assertEqual(response_b.status_code, 409)

        # User C also encounters conflict
        response_c = client_c.post(
            autosave_url,
            json.dumps({'text': 'User C changes', 'version': 1}),
            content_type='application/json'
        )
        self.assertEqual(response_c.status_code, 409)

        # User B resolves first
        response_b_resolved = client_b.post(
            autosave_url,
            json.dumps({'text': 'User B resolved', 'version': 2}),
            content_type='application/json'
        )
        self.assertEqual(response_b_resolved.status_code, 200)
        self.assertEqual(response_b_resolved.json()['version'], 3)

        # User C must resolve with new version
        response_c_old = client_c.post(
            autosave_url,
            json.dumps({'text': 'User C resolved', 'version': 2}),
            content_type='application/json'
        )
        self.assertEqual(response_c_old.status_code, 409)

        response_c_resolved = client_c.post(
            autosave_url,
            json.dumps({'text': 'User C resolved', 'version': 3}),
            content_type='application/json'
        )
        self.assertEqual(response_c_resolved.status_code, 200)
        self.assertEqual(response_c_resolved.json()['version'], 4)

        # Verify final state
        entry.refresh_from_db()
        self.assertEqual(entry.edit_version, 4)
        self.assertEqual(entry.text, 'User C resolved')
