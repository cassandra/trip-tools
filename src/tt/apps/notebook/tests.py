import json
from datetime import date

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from tt.apps.trips.enums import TripStatus
from tt.apps.trips.models import Trip
from .models import NotebookEntry

User = get_user_model()


class NotebookListViewTests(TestCase):
    """Tests for the notebook list view."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.trip = Trip.objects.create(
            user=self.user,
            title='Test Trip',
            trip_status=TripStatus.UPCOMING
        )
        self.list_url = reverse('notebook_list', kwargs={'trip_id': self.trip.pk})

    def test_list_requires_authentication(self):
        """Test that notebook list redirects unauthenticated users."""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/user/signin', response.url)

    def test_list_displays_for_authenticated_user(self):
        """Test that notebook list displays for authenticated user."""
        self.client.force_login(self.user)
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'notebook/pages/list.html')
        self.assertIn('trip', response.context)
        self.assertIn('entries', response.context)

    def test_list_only_shows_user_trips(self):
        """Test that users can only see notes for their own trips."""
        other_user = User.objects.create_user(
            email='other@example.com',
            password='testpass123'
        )
        other_trip = Trip.objects.create(
            user=other_user,
            title='Other Trip',
            trip_status=TripStatus.UPCOMING
        )

        self.client.force_login(self.user)
        other_trip_url = reverse('notebook_list', kwargs={'trip_id': other_trip.pk})
        response = self.client.get(other_trip_url)

        self.assertEqual(response.status_code, 404)

    def test_list_shows_entries_chronologically(self):
        """Test that entries are displayed in chronological order."""
        # Create entries out of order
        entry2 = NotebookEntry.objects.create(
            user=self.user,
            trip=self.trip,
            date=date(2024, 1, 15),
            text='Second entry'
        )
        entry1 = NotebookEntry.objects.create(
            user=self.user,
            trip=self.trip,
            date=date(2024, 1, 10),
            text='First entry'
        )
        entry3 = NotebookEntry.objects.create(
            user=self.user,
            trip=self.trip,
            date=date(2024, 1, 20),
            text='Third entry'
        )

        self.client.force_login(self.user)
        response = self.client.get(self.list_url)

        entries = response.context['entries']
        self.assertEqual(len(entries), 3)
        self.assertEqual(entries[0].pk, entry1.pk)
        self.assertEqual(entries[1].pk, entry2.pk)
        self.assertEqual(entries[2].pk, entry3.pk)


class NotebookEditViewTests(TestCase):
    """Tests for the notebook edit view."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.trip = Trip.objects.create(
            user=self.user,
            title='Test Trip',
            trip_status=TripStatus.UPCOMING
        )

    def test_new_entry_requires_authentication(self):
        """Test that creating new entry redirects unauthenticated users."""
        new_url = reverse('notebook_new', kwargs={'trip_id': self.trip.pk})
        response = self.client.get(new_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/user/signin', response.url)

    def test_edit_entry_requires_authentication(self):
        """Test that editing entry redirects unauthenticated users."""
        entry = NotebookEntry.objects.create(
            user=self.user,
            trip=self.trip,
            date=date(2024, 1, 15),
            text='Test content'
        )
        edit_url = reverse('notebook_edit', kwargs={
            'trip_id': self.trip.pk,
            'entry_pk': entry.pk
        })
        response = self.client.get(edit_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/user/signin', response.url)

    def test_new_entry_displays_for_authenticated_user(self):
        """Test that GET to new entry URL creates entry and redirects to edit."""
        self.client.force_login(self.user)
        new_url = reverse('notebook_new', kwargs={'trip_id': self.trip.pk})

        # Verify no entries exist yet
        self.assertEqual(NotebookEntry.objects.filter(trip=self.trip).count(), 0)

        response = self.client.get(new_url)

        # Should redirect to edit URL with new entry's PK
        self.assertEqual(response.status_code, 302)

        # Verify entry was created
        self.assertEqual(NotebookEntry.objects.filter(trip=self.trip).count(), 1)
        entry = NotebookEntry.objects.get(trip=self.trip)

        # Verify redirect URL points to edit view
        expected_url = reverse('notebook_edit', kwargs={
            'trip_id': self.trip.pk,
            'entry_pk': entry.pk
        })
        self.assertEqual(response.url, expected_url)

    def test_edit_entry_displays_for_authenticated_user(self):
        """Test that edit entry form displays for authenticated user."""
        entry = NotebookEntry.objects.create(
            user=self.user,
            trip=self.trip,
            date=date(2024, 1, 15),
            text='Test content'
        )
        self.client.force_login(self.user)
        edit_url = reverse('notebook_edit', kwargs={
            'trip_id': self.trip.pk,
            'entry_pk': entry.pk
        })
        response = self.client.get(edit_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'notebook/pages/editor.html')
        self.assertIn('trip', response.context)
        self.assertIn('form', response.context)
        self.assertEqual(response.context['entry'], entry)

    def test_edit_only_shows_user_trips(self):
        """Test that users can only edit notes for their own trips."""
        other_user = User.objects.create_user(
            email='other@example.com',
            password='testpass123'
        )
        other_trip = Trip.objects.create(
            user=other_user,
            title='Other Trip',
            trip_status=TripStatus.UPCOMING
        )
        other_entry = NotebookEntry.objects.create(
            user=other_user,
            trip=other_trip,
            date=date(2024, 1, 15),
            text='Other user content'
        )

        self.client.force_login(self.user)
        other_trip_url = reverse('notebook_edit', kwargs={
            'trip_id': other_trip.pk,
            'entry_pk': other_entry.pk
        })
        response = self.client.get(other_trip_url)

        self.assertEqual(response.status_code, 404)

    def test_edit_only_shows_user_entries(self):
        """Test that users can only edit their own entries even with correct trip."""
        other_user = User.objects.create_user(
            email='other@example.com',
            password='testpass123'
        )
        # Entry by other user for same trip (shouldn't be possible in practice)
        other_entry = NotebookEntry.objects.create(
            user=other_user,
            trip=self.trip,
            date=date(2024, 1, 15),
            text='Other user content'
        )

        self.client.force_login(self.user)
        edit_url = reverse('notebook_edit', kwargs={
            'trip_id': self.trip.pk,
            'entry_pk': other_entry.pk
        })
        response = self.client.get(edit_url)

        self.assertEqual(response.status_code, 404)

    def test_edit_loads_existing_entry(self):
        """Test that editing loads existing entry data."""
        entry = NotebookEntry.objects.create(
            user=self.user,
            trip=self.trip,
            date=date(2024, 1, 15),
            text='Existing note content'
        )

        self.client.force_login(self.user)
        edit_url = reverse('notebook_edit', kwargs={
            'trip_id': self.trip.pk,
            'entry_pk': entry.pk
        })
        response = self.client.get(edit_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Existing note content')
        self.assertEqual(response.context['entry'], entry)

    def test_new_entry_creates_with_todays_date(self):
        """Test that new entries are created with today's date by default."""
        self.client.force_login(self.user)
        new_url = reverse('notebook_new', kwargs={'trip_id': self.trip.pk})

        response = self.client.get(new_url)

        # Should redirect after creating entry
        self.assertEqual(response.status_code, 302)

        # Verify entry was created with today's date
        entry = NotebookEntry.objects.get(trip=self.trip)
        self.assertEqual(entry.date, date.today())
        self.assertEqual(entry.user, self.user)

    def test_new_entry_creates_blank_text(self):
        """Test that new entries start with empty text."""
        self.client.force_login(self.user)
        new_url = reverse('notebook_new', kwargs={'trip_id': self.trip.pk})

        response = self.client.get(new_url)

        # Should redirect after creating entry
        self.assertEqual(response.status_code, 302)

        # Verify entry was created with empty text
        entry = NotebookEntry.objects.get(trip=self.trip)
        self.assertEqual(entry.text, '')

    def test_post_updates_existing_entry(self):
        """Test that posting to edit URL updates an existing entry."""
        entry = NotebookEntry.objects.create(
            user=self.user,
            trip=self.trip,
            date=date(2024, 1, 15),
            text='Original content'
        )

        self.client.force_login(self.user)
        edit_url = reverse('notebook_edit', kwargs={
            'trip_id': self.trip.pk,
            'entry_pk': entry.pk
        })
        response = self.client.post(edit_url, {
            'date': entry.date.strftime('%Y-%m-%d'),
            'text': 'Updated content'
        })

        # Should redirect to same edit view
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, edit_url)

        # Verify entry was updated (not duplicated)
        self.assertEqual(NotebookEntry.objects.filter(trip=self.trip).count(), 1)
        entry.refresh_from_db()
        self.assertEqual(entry.text, 'Updated content')

    def test_post_updates_entry_date(self):
        """Test that posting with a new date updates the entry date."""
        entry = NotebookEntry.objects.create(
            user=self.user,
            trip=self.trip,
            date=date(2024, 1, 15),
            text='Test content'
        )
        new_date = date(2024, 1, 20)

        self.client.force_login(self.user)
        edit_url = reverse('notebook_edit', kwargs={
            'trip_id': self.trip.pk,
            'entry_pk': entry.pk
        })
        response = self.client.post(edit_url, {
            'date': new_date.strftime('%Y-%m-%d'),
            'text': 'Test content'
        })

        self.assertEqual(response.status_code, 302)

        # Verify date was updated
        entry.refresh_from_db()
        self.assertEqual(entry.date, new_date)

        # Verify no duplicate entries
        self.assertEqual(NotebookEntry.objects.filter(trip=self.trip).count(), 1)

    def test_date_conflict_on_new_entry(self):
        """Test that editing a newly created entry to a conflicting date shows validation error."""
        # Create an existing entry with specific date
        existing_entry = NotebookEntry.objects.create(
            user=self.user,
            trip=self.trip,
            date=date(2024, 1, 15),
            text='Existing content'
        )

        self.client.force_login(self.user)

        # Create a new entry (which will have today's date)
        new_url = reverse('notebook_new', kwargs={'trip_id': self.trip.pk})
        response = self.client.get(new_url)
        self.assertEqual(response.status_code, 302)

        # Get the newly created entry
        new_entry = NotebookEntry.objects.exclude(pk=existing_entry.pk).get(trip=self.trip)

        # Try to edit the new entry to use the existing entry's date
        edit_url = reverse('notebook_edit', kwargs={
            'trip_id': self.trip.pk,
            'entry_pk': new_entry.pk
        })
        response = self.client.post(edit_url, {
            'date': existing_entry.date.strftime('%Y-%m-%d'),
            'text': 'Conflicting content'
        })

        # Should return form with error (400 status)
        self.assertEqual(response.status_code, 400)
        self.assertFormError(response.context['form'], 'date', 'An entry for January 15, 2024 already exists.')

        # Verify new entry's date wasn't changed
        new_entry.refresh_from_db()
        self.assertNotEqual(new_entry.date, existing_entry.date)

        # Verify we still have exactly 2 entries
        self.assertEqual(NotebookEntry.objects.filter(trip=self.trip).count(), 2)

    def test_date_conflict_on_edit(self):
        """Test that changing entry date to existing date shows validation error."""
        entry1 = NotebookEntry.objects.create(
            user=self.user,
            trip=self.trip,
            date=date(2024, 1, 15),
            text='Entry 1'
        )
        entry2 = NotebookEntry.objects.create(
            user=self.user,
            trip=self.trip,
            date=date(2024, 1, 20),
            text='Entry 2'
        )

        self.client.force_login(self.user)
        edit_url = reverse('notebook_edit', kwargs={
            'trip_id': self.trip.pk,
            'entry_pk': entry2.pk
        })
        response = self.client.post(edit_url, {
            'date': entry1.date.strftime('%Y-%m-%d'),  # Try to change to entry1's date
            'text': 'Entry 2 updated'
        })

        # Should return form with error
        self.assertEqual(response.status_code, 400)
        self.assertFormError(response.context['form'], 'date', 'An entry for January 15, 2024 already exists.')

        # Verify entry2's date wasn't changed
        entry2.refresh_from_db()
        self.assertEqual(entry2.date, date(2024, 1, 20))

    def test_can_edit_same_entry_with_same_date(self):
        """Test that editing an entry with its current date works (no conflict with itself)."""
        entry = NotebookEntry.objects.create(
            user=self.user,
            trip=self.trip,
            date=date(2024, 1, 15),
            text='Original content'
        )

        self.client.force_login(self.user)
        edit_url = reverse('notebook_edit', kwargs={
            'trip_id': self.trip.pk,
            'entry_pk': entry.pk
        })
        response = self.client.post(edit_url, {
            'date': entry.date.strftime('%Y-%m-%d'),  # Same date
            'text': 'Updated content'
        })

        # Should succeed
        self.assertEqual(response.status_code, 302)

        entry.refresh_from_db()
        self.assertEqual(entry.text, 'Updated content')
        self.assertEqual(entry.date, date(2024, 1, 15))


class NotebookAutoSaveViewTests(TestCase):
    """Tests for the notebook auto-save AJAX endpoint."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.trip = Trip.objects.create(
            user=self.user,
            title='Test Trip',
            trip_status=TripStatus.UPCOMING
        )

    def test_autosave_requires_authentication(self):
        """Test that auto-save requires authentication."""
        entry = NotebookEntry.objects.create(
            user=self.user,
            trip=self.trip,
            date=date(2024, 1, 15),
            text='Test'
        )
        autosave_url = reverse('notebook_autosave', kwargs={
            'trip_id': self.trip.pk,
            'entry_pk': entry.pk
        })

        response = self.client.post(
            autosave_url,
            json.dumps({'text': 'Test'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('/user/signin', response.url)

    def test_autosave_only_post_method(self):
        """Test that auto-save only accepts POST."""
        entry = NotebookEntry.objects.create(
            user=self.user,
            trip=self.trip,
            date=date(2024, 1, 15),
            text='Test'
        )
        autosave_url = reverse('notebook_autosave', kwargs={
            'trip_id': self.trip.pk,
            'entry_pk': entry.pk
        })

        self.client.force_login(self.user)
        response = self.client.get(autosave_url)
        self.assertEqual(response.status_code, 405)  # Method not allowed

    def test_autosave_requires_existing_entry(self):
        """Test that auto-save requires an existing entry (can't create new)."""
        self.client.force_login(self.user)

        # Try to auto-save with non-existent entry_pk
        fake_autosave_url = reverse('notebook_autosave', kwargs={
            'trip_id': self.trip.pk,
            'entry_pk': 99999
        })
        response = self.client.post(
            fake_autosave_url,
            json.dumps({'text': 'Should fail'}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 404)

    def test_autosave_updates_existing_entry(self):
        """Test that auto-save updates an existing entry."""
        entry = NotebookEntry.objects.create(
            user=self.user,
            trip=self.trip,
            date=date(2024, 1, 15),
            text='Original'
        )
        original_created = entry.created_datetime
        autosave_url = reverse('notebook_autosave', kwargs={
            'trip_id': self.trip.pk,
            'entry_pk': entry.pk
        })

        self.client.force_login(self.user)
        response = self.client.post(
            autosave_url,
            json.dumps({'text': 'Updated via auto-save'}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('modified_datetime', data)

        # Verify entry was updated
        entry.refresh_from_db()
        self.assertEqual(entry.text, 'Updated via auto-save')
        self.assertEqual(entry.created_datetime, original_created)  # Created time unchanged
        self.assertGreater(entry.modified_datetime, original_created)  # Modified time updated

    def test_autosave_updates_entry_date(self):
        """Test that auto-save can update entry date."""
        entry = NotebookEntry.objects.create(
            user=self.user,
            trip=self.trip,
            date=date(2024, 1, 15),
            text='Test content'
        )
        new_date = date(2024, 1, 20)
        autosave_url = reverse('notebook_autosave', kwargs={
            'trip_id': self.trip.pk,
            'entry_pk': entry.pk
        })

        self.client.force_login(self.user)
        response = self.client.post(
            autosave_url,
            json.dumps({
                'date': new_date.strftime('%Y-%m-%d'),
                'text': 'Test content'
            }),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')

        # Verify date was updated
        entry.refresh_from_db()
        self.assertEqual(entry.date, new_date)

    def test_autosave_date_conflict(self):
        """Test that auto-save detects date conflicts."""
        entry1 = NotebookEntry.objects.create(
            user=self.user,
            trip=self.trip,
            date=date(2024, 1, 15),
            text='Entry 1'
        )
        entry2 = NotebookEntry.objects.create(
            user=self.user,
            trip=self.trip,
            date=date(2024, 1, 20),
            text='Entry 2'
        )
        autosave_url = reverse('notebook_autosave', kwargs={
            'trip_id': self.trip.pk,
            'entry_pk': entry2.pk
        })

        self.client.force_login(self.user)
        response = self.client.post(
            autosave_url,
            json.dumps({
                'date': entry1.date.strftime('%Y-%m-%d'),  # Try to change to entry1's date
                'text': 'Entry 2 updated'
            }),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['status'], 'error')
        self.assertIn('already exists', data['message'])

        # Verify entry2's date wasn't changed
        entry2.refresh_from_db()
        self.assertEqual(entry2.date, date(2024, 1, 20))

    def test_autosave_same_date_no_conflict(self):
        """Test that auto-save with same date doesn't trigger conflict."""
        entry = NotebookEntry.objects.create(
            user=self.user,
            trip=self.trip,
            date=date(2024, 1, 15),
            text='Original'
        )
        autosave_url = reverse('notebook_autosave', kwargs={
            'trip_id': self.trip.pk,
            'entry_pk': entry.pk
        })

        self.client.force_login(self.user)
        response = self.client.post(
            autosave_url,
            json.dumps({
                'date': entry.date.strftime('%Y-%m-%d'),  # Same date
                'text': 'Updated content'
            }),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')

        entry.refresh_from_db()
        self.assertEqual(entry.text, 'Updated content')

    def test_autosave_validates_user_ownership(self):
        """Test that auto-save validates user owns the trip."""
        other_user = User.objects.create_user(
            email='other@example.com',
            password='testpass123'
        )
        other_trip = Trip.objects.create(
            user=other_user,
            title='Other Trip',
            trip_status=TripStatus.UPCOMING
        )
        other_entry = NotebookEntry.objects.create(
            user=other_user,
            trip=other_trip,
            date=date(2024, 1, 15),
            text='Other user entry'
        )

        self.client.force_login(self.user)
        other_trip_url = reverse('notebook_autosave', kwargs={
            'trip_id': other_trip.pk,
            'entry_pk': other_entry.pk
        })
        response = self.client.post(
            other_trip_url,
            json.dumps({'text': 'Unauthorized save'}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 404)

    def test_autosave_validates_entry_belongs_to_trip(self):
        """Test that auto-save validates entry belongs to the specified trip."""
        other_trip = Trip.objects.create(
            user=self.user,
            title='Other Trip',
            trip_status=TripStatus.UPCOMING
        )
        entry_other_trip = NotebookEntry.objects.create(
            user=self.user,
            trip=other_trip,
            date=date(2024, 1, 15),
            text='Entry for other trip'
        )

        self.client.force_login(self.user)
        # Try to auto-save entry from other_trip using self.trip
        wrong_trip_url = reverse('notebook_autosave', kwargs={
            'trip_id': self.trip.pk,
            'entry_pk': entry_other_trip.pk
        })
        response = self.client.post(
            wrong_trip_url,
            json.dumps({'text': 'Should fail'}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 404)

    def test_autosave_invalid_json(self):
        """Test that auto-save handles invalid JSON gracefully."""
        entry = NotebookEntry.objects.create(
            user=self.user,
            trip=self.trip,
            date=date(2024, 1, 15),
            text='Test'
        )
        autosave_url = reverse('notebook_autosave', kwargs={
            'trip_id': self.trip.pk,
            'entry_pk': entry.pk
        })

        self.client.force_login(self.user)
        response = self.client.post(
            autosave_url,
            'invalid json{',
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['status'], 'error')
        self.assertIn('Invalid JSON', data['message'])

    def test_autosave_invalid_date_format(self):
        """Test that auto-save handles invalid date format."""
        entry = NotebookEntry.objects.create(
            user=self.user,
            trip=self.trip,
            date=date(2024, 1, 15),
            text='Test'
        )
        autosave_url = reverse('notebook_autosave', kwargs={
            'trip_id': self.trip.pk,
            'entry_pk': entry.pk
        })

        self.client.force_login(self.user)
        response = self.client.post(
            autosave_url,
            json.dumps({
                'date': 'not-a-date',
                'text': 'Test'
            }),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['status'], 'error')
        self.assertIn('Invalid date format', data['message'])


class NotebookEntryModelTests(TestCase):
    """Tests for NotebookEntry model constraints."""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.trip = Trip.objects.create(
            user=self.user,
            title='Test Trip',
            trip_status=TripStatus.UPCOMING
        )

    def test_unique_together_constraint(self):
        """Test that one entry per trip per date is enforced."""
        test_date = date(2024, 1, 15)

        # Create first entry
        NotebookEntry.objects.create(
            user=self.user,
            trip=self.trip,
            date=test_date,
            text='First entry'
        )

        # Attempt to create duplicate
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            NotebookEntry.objects.create(
                user=self.user,
                trip=self.trip,
                date=test_date,
                text='Duplicate entry'
            )

    def test_cascade_delete_with_trip(self):
        """Test that entries are deleted when trip is deleted."""
        entry = NotebookEntry.objects.create(
            user=self.user,
            trip=self.trip,
            date=date(2024, 1, 15),
            text='Test entry'
        )

        entry_id = entry.pk
        self.trip.delete()

        # Verify entry was deleted
        self.assertFalse(NotebookEntry.objects.filter(pk=entry_id).exists())

    def test_cascade_delete_with_user(self):
        """Test that entries are deleted when user is deleted."""
        entry = NotebookEntry.objects.create(
            user=self.user,
            trip=self.trip,
            date=date(2024, 1, 15),
            text='Test entry'
        )

        entry_id = entry.pk
        self.user.delete()

        # Verify entry was deleted
        self.assertFalse(NotebookEntry.objects.filter(pk=entry_id).exists())

    def test_entries_ordered_by_date(self):
        """Test that entries are ordered by date by default."""
        # Create entries out of order
        entry3 = NotebookEntry.objects.create(
            user=self.user,
            trip=self.trip,
            date=date(2024, 1, 20),
            text='Third'
        )
        entry1 = NotebookEntry.objects.create(
            user=self.user,
            trip=self.trip,
            date=date(2024, 1, 10),
            text='First'
        )
        entry2 = NotebookEntry.objects.create(
            user=self.user,
            trip=self.trip,
            date=date(2024, 1, 15),
            text='Second'
        )

        # Retrieve entries (should be ordered by date)
        entries = list(NotebookEntry.objects.filter(trip=self.trip))

        self.assertEqual(len(entries), 3)
        self.assertEqual(entries[0].pk, entry1.pk)
        self.assertEqual(entries[1].pk, entry2.pk)
        self.assertEqual(entries[2].pk, entry3.pk)

    def test_entry_string_representation(self):
        """Test the string representation of a notebook entry."""
        entry = NotebookEntry.objects.create(
            user=self.user,
            trip=self.trip,
            date=date(2024, 1, 15),
            text='Test entry content'
        )

        # Test that str() returns something reasonable
        str_repr = str(entry)
        self.assertIn('2024-01-15', str_repr)


class NotebookEntryManagerTests(TestCase):
    """Tests for NotebookEntryManager custom methods."""

    def setUp(self):
        self.user1 = User.objects.create_user(
            email='user1@example.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            email='user2@example.com',
            password='testpass123'
        )
        self.trip1 = Trip.objects.create(
            user=self.user1,
            title='Trip 1',
            trip_status=TripStatus.UPCOMING
        )
        self.trip2 = Trip.objects.create(
            user=self.user2,
            title='Trip 2',
            trip_status=TripStatus.UPCOMING
        )

    def test_for_user_filters_correctly(self):
        """Test that for_user returns only entries for specified user."""
        entry1 = NotebookEntry.objects.create(
            user=self.user1,
            trip=self.trip1,
            date=date(2024, 1, 15),
            text='User 1 entry'
        )
        entry2 = NotebookEntry.objects.create(
            user=self.user2,
            trip=self.trip2,
            date=date(2024, 1, 15),
            text='User 2 entry'
        )

        user1_entries = list(NotebookEntry.objects.for_user(self.user1))
        user2_entries = list(NotebookEntry.objects.for_user(self.user2))

        self.assertEqual(len(user1_entries), 1)
        self.assertEqual(user1_entries[0].pk, entry1.pk)
        self.assertEqual(len(user2_entries), 1)
        self.assertEqual(user2_entries[0].pk, entry2.pk)

    def test_for_trip_filters_correctly(self):
        """Test that for_trip returns only entries for specified trip."""
        entry1 = NotebookEntry.objects.create(
            user=self.user1,
            trip=self.trip1,
            date=date(2024, 1, 15),
            text='Trip 1 entry'
        )
        entry2 = NotebookEntry.objects.create(
            user=self.user2,
            trip=self.trip2,
            date=date(2024, 1, 15),
            text='Trip 2 entry'
        )

        trip1_entries = list(NotebookEntry.objects.for_trip(self.trip1))
        trip2_entries = list(NotebookEntry.objects.for_trip(self.trip2))

        self.assertEqual(len(trip1_entries), 1)
        self.assertEqual(trip1_entries[0].pk, entry1.pk)
        self.assertEqual(len(trip2_entries), 1)
        self.assertEqual(trip2_entries[0].pk, entry2.pk)

    def test_for_date_returns_entry(self):
        """Test that for_date returns the entry for a specific date."""
        test_date = date(2024, 1, 15)
        entry = NotebookEntry.objects.create(
            user=self.user1,
            trip=self.trip1,
            date=test_date,
            text='Test entry'
        )

        result = NotebookEntry.objects.for_date(self.trip1, test_date)

        self.assertIsNotNone(result)
        self.assertEqual(result.pk, entry.pk)

    def test_for_date_returns_none_when_not_found(self):
        """Test that for_date returns None when entry doesn't exist."""
        test_date = date(2024, 1, 15)

        result = NotebookEntry.objects.for_date(self.trip1, test_date)

        self.assertIsNone(result)

    def test_for_date_with_multiple_trips(self):
        """Test that for_date correctly filters by trip."""
        test_date = date(2024, 1, 15)
        entry1 = NotebookEntry.objects.create(
            user=self.user1,
            trip=self.trip1,
            date=test_date,
            text='Trip 1 entry'
        )
        entry2 = NotebookEntry.objects.create(
            user=self.user2,
            trip=self.trip2,
            date=test_date,
            text='Trip 2 entry'
        )

        result1 = NotebookEntry.objects.for_date(self.trip1, test_date)
        result2 = NotebookEntry.objects.for_date(self.trip2, test_date)

        self.assertEqual(result1.pk, entry1.pk)
        self.assertEqual(result2.pk, entry2.pk)
