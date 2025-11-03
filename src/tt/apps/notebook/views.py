import json
import logging
from datetime import date as date_class, datetime, timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import DatabaseError, IntegrityError, transaction
from django.db.models import F, Max
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import View

from tt.apps.trips.context import TripPageContext
from tt.apps.trips.enums import TripPage
from tt.apps.trips.mixins import TripViewMixin

from .forms import NotebookEntryForm
from .models import NotebookEntry

logger = logging.getLogger(__name__)


class NotebookListView( LoginRequiredMixin, TripViewMixin, View ):
    """Show all notebook entries for a trip (chronological order)."""

    def get(self, request, trip_id: int, *args, **kwargs) -> HttpResponse:
        request_member = self.get_trip_member( request, trip_id = trip_id )
        self.assert_is_viewer( request_member )
        trip = request_member.trip

        notebook_entries = trip.notebook_entries.all()

        trip_page_context = TripPageContext(
            trip=trip,
            active_page=TripPage.NOTES,
            notebook_entries=notebook_entries
        )
        context = {
            'trip_page': trip_page_context,
            'notebook_entries': notebook_entries,
        }
        return render(request, 'notebook/pages/list.html', context)


class NotebookEditView( LoginRequiredMixin, TripViewMixin, View ):
    """Edit or create a notebook entry."""

    def get(self, request, trip_id: int, entry_pk: int = None, *args, **kwargs) -> HttpResponse:
        request_member = self.get_trip_member( request, trip_id = trip_id )
        self.assert_is_editor( request_member )
        trip = request_member.trip

        if entry_pk:
            entry = get_object_or_404(
                NotebookEntry,
                pk = entry_pk,
                trip = trip,
            )
        else:
            max_date = trip.notebook_entries.aggregate( Max( 'date' ) )['date__max']
            if max_date:
                default_date = max_date + timedelta( days = 1 )
            else:
                default_date = date_class.today()

            entry = NotebookEntry.objects.create(
                trip = trip,
                date = default_date,
                text = '',
            )
            return redirect( 'notebook_edit', trip_id = trip.pk, entry_pk = entry.pk )

        form = NotebookEntryForm(instance=entry, trip=trip)
        notebook_entries = trip.notebook_entries.all()

        trip_page_context = TripPageContext(
            trip=trip,
            active_page=TripPage.NOTES,
            notebook_entries=notebook_entries,
            notebook_entry_pk=entry_pk
        )

        context = {
            'trip_page': trip_page_context,
            'form': form,
            'entry': entry,
        }

        return render(request, 'notebook/pages/editor.html', context)

    def post(self, request, trip_id: int, entry_pk: int, *args, **kwargs) -> HttpResponse:
        request_member = self.get_trip_member( request, trip_id = trip_id )
        self.assert_is_editor( request_member )
        trip = request_member.trip

        entry = get_object_or_404(
            NotebookEntry,
            pk = entry_pk,
            trip = trip,
        )

        form = NotebookEntryForm(request.POST, instance=entry, trip=trip)

        if form.is_valid():
            with transaction.atomic():
                entry = form.save(commit=False)
                entry.modified_by = request.user
                entry.save()

            return redirect('notebook_edit', trip_id=trip.pk, entry_pk=entry.pk)

        notebook_entries = trip.notebook_entries.all()

        trip_page_context = TripPageContext(
            trip=trip,
            active_page=TripPage.NOTES,
            notebook_entries=notebook_entries,
            notebook_entry_pk=entry_pk
        )

        context = {
            'trip_page': trip_page_context,
            'form': form,
            'entry': entry,
        }

        return render(request, 'notebook/pages/editor.html', context, status=400)


class NotebookAutoSaveView( LoginRequiredMixin, TripViewMixin, View ):
    """AJAX endpoint for auto-saving notebook entries."""

    def get(self, request, trip_id: int, entry_pk: int, *args, **kwargs) -> JsonResponse:
        return JsonResponse(
            { 'status': 'error', 'message': 'Method not allowed' },
            status = 405,
        )

    def post(self, request, trip_id: int, entry_pk: int, *args, **kwargs) -> JsonResponse:
        request_member = self.get_trip_member( request, trip_id = trip_id )
        self.assert_is_editor( request_member )
        trip = request_member.trip

        entry = get_object_or_404(
            NotebookEntry,
            pk = entry_pk,
            trip = trip,
        )

        try:
            data = json.loads(request.body)
            text = data.get('text', '')
            date_str = data.get('date')
            client_version = data.get('version')
        except json.JSONDecodeError:
            logger.warning('Invalid JSON in auto-save request')
            return JsonResponse(
                {'status': 'error', 'message': 'Invalid JSON'},
                status=400
            )

        # Parse date if provided
        new_date = None
        if date_str:
            try:
                new_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                logger.warning(f'Invalid date format: {date_str}')
                return JsonResponse(
                    {'status': 'error', 'message': 'Invalid date format'},
                    status=400
                )

        try:
            with transaction.atomic():
                # Use select_for_update to lock the row for the duration of the transaction
                locked_entry = NotebookEntry.objects.select_for_update().get(pk=entry.pk)

                # Check version conflict - backward compatible (treat missing version as no check)
                if client_version is not None:
                    if locked_entry.edit_version != client_version:
                        # Version conflict detected
                        modified_by_name = locked_entry.modified_by.get_full_name() if locked_entry.modified_by else 'another user'
                        logger.info(
                            f'Version conflict for entry {entry.pk} (trip {trip_id}): '
                            f'client={client_version}, server={locked_entry.edit_version}, '
                            f'modified_by={modified_by_name}'
                        )
                        return JsonResponse(
                            {
                                'status': 'conflict',
                                'server_version': locked_entry.edit_version,
                                'server_text': locked_entry.text,
                                'server_modified_at': locked_entry.modified_datetime.isoformat(),
                                'modified_by_name': modified_by_name,
                                'message': f'Entry was modified by {modified_by_name}'
                            },
                            status=409
                        )

                # Check for date conflicts if date is changing (inside transaction for atomicity)
                if new_date and new_date != locked_entry.date:
                    existing = NotebookEntry.objects.filter(
                        trip=trip,
                        date=new_date
                    ).exclude(pk=locked_entry.pk).exists()

                    if existing:
                        return JsonResponse(
                            {
                                'status': 'error',
                                'message': f'An entry for {new_date.strftime("%B %d, %Y")} already exists.'
                            },
                            status=400
                        )

                # Update fields and increment version atomically
                locked_entry.text = text
                locked_entry.modified_by = request.user
                update_fields = ['text', 'edit_version', 'modified_by', 'modified_datetime']
                if new_date:
                    locked_entry.date = new_date
                    update_fields.append('date')

                # Use F() expression for atomic increment to prevent race conditions
                locked_entry.edit_version = F('edit_version') + 1
                locked_entry.save(update_fields=update_fields)

                # Refresh to get the actual version value (F() expressions don't update in-memory)
                locked_entry.refresh_from_db(fields=['edit_version', 'modified_datetime'])

            return JsonResponse({
                'status': 'success',
                'version': locked_entry.edit_version,
                'modified_datetime': locked_entry.modified_datetime.isoformat(),
            })

        except NotebookEntry.DoesNotExist:
            logger.error(f'Entry {entry_pk} not found during atomic update')
            return JsonResponse(
                {'status': 'error', 'message': 'Entry not found'},
                status=404
            )
        except IntegrityError as e:
            logger.warning(f'Integrity constraint violation for entry {entry_pk}: {e}')
            return JsonResponse(
                {'status': 'error', 'message': 'Unable to save - entry date conflicts with another entry'},
                status=409
            )
        except DatabaseError as e:
            logger.error(f'Database error auto-saving notebook entry {entry_pk}: {e}')
            return JsonResponse(
                {'status': 'error', 'message': 'Database error occurred'},
                status=500
            )
