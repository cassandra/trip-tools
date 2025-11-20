from datetime import date as date_class, timedelta
import logging
from uuid import UUID

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import DatabaseError, IntegrityError, transaction
from django.db.models import Max
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import View

from tt.apps.members.models import TripMember
from tt.apps.trips.context import TripPageContext
from tt.apps.trips.enums import TripPage
from tt.apps.trips.mixins import TripViewMixin

from .autosave_helpers import NotebookAutoSaveHelper, NotebookConflictHelper
from .context import NotebookPageContext
from .forms import NotebookEntryForm
from .models import NotebookEntry

logger = logging.getLogger(__name__)


class NotebookListView( LoginRequiredMixin, TripViewMixin, View ):
    """Show all notebook entries for a trip (chronological order)."""

    def get(self, request, trip_uuid: UUID, *args, **kwargs) -> HttpResponse:
        request_member = self.get_trip_member( request, trip_uuid = trip_uuid )
        self.assert_is_viewer( request_member )
        trip = request_member.trip

        notebook_entries = trip.notebook_entries.all()

        trip_page_context = TripPageContext(
            active_page = TripPage.NOTES,
            request_member = request_member,
        )
        notebook_page_context = NotebookPageContext(
            notebook_entries = notebook_entries
        )
        context = {
            'trip_page': trip_page_context,
            'notebook_page': notebook_page_context,
            'notebook_entries': notebook_entries,
        }
        return render(request, 'notebook/pages/notebook_entry_list.html', context)


class NotebookEntryNewView( LoginRequiredMixin, TripViewMixin, View ):

    def get(self, request, trip_uuid: UUID, *args, **kwargs) -> HttpResponse:
        request_member = self.get_trip_member( request, trip_uuid = trip_uuid )
        self.assert_is_viewer( request_member )
        trip = request_member.trip

        # Only editors can create new entries
        self.assert_is_editor( request_member )

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
        return redirect( 'notebook_entry', entry_uuid = entry.uuid )

        
class NotebookEntryView( LoginRequiredMixin, TripViewMixin, View ):

    def get(self, request, entry_uuid: UUID, *args, **kwargs) -> HttpResponse:
        entry = get_object_or_404(
            NotebookEntry,
            uuid = entry_uuid,
        )
        request_member = get_object_or_404(
            TripMember,
            trip = entry.trip,
            user = request.user,
        )
        self.assert_is_viewer( request_member )
        trip = request_member.trip

        notebook_entries = trip.notebook_entries.all()

        trip_page_context = TripPageContext(
            active_page = TripPage.NOTES,
            request_member = request_member,
        )
        notebook_page_context = NotebookPageContext(
            notebook_entries = notebook_entries,
            notebook_entry_uuid = entry.uuid
        )

        if request_member.can_edit_trip:
            # Render editable template
            form = NotebookEntryForm(instance=entry, trip=trip)
            context = {
                'trip_page': trip_page_context,
                'notebook_page': notebook_page_context,
                'form': form,
                'entry': entry,
            }
            return render(request, 'notebook/pages/notebook_entry.html', context)
        else:
            # Render read-only template
            context = {
                'trip_page': trip_page_context,
                'notebook_page': notebook_page_context,
                'entry': entry,
            }
            return render(request, 'notebook/pages/notebook_entry_readonly.html', context)

    def post(self, request, entry_uuid: UUID, *args, **kwargs) -> HttpResponse:
        """
        Non-JavaScript fallback for saving notebook entries.

        NOTE: In normal usage, notebook entries are saved via auto-save AJAX
        (see NotebookAutoSaveView below), which provides optimistic locking,
        version conflict detection, and real-time status updates.

        This POST method serves as a fallback for environments where JavaScript
        is disabled or for manual form submission. It handles basic save
        functionality but lacks the collaborative editing features of auto-save.
        """
        entry = get_object_or_404(
            NotebookEntry,
            uuid = entry_uuid,
        )
        request_member = get_object_or_404(
            TripMember,
            trip = entry.trip,
            user = request.user,
        )
        self.assert_is_editor( request_member )
        trip = request_member.trip

        entry = get_object_or_404(
            NotebookEntry,
            pk = entry.pk,
            trip = trip,
        )

        form = NotebookEntryForm( request.POST, instance = entry, trip = trip )

        if form.is_valid():
            with transaction.atomic():
                entry = form.save(commit=False)
                entry.modified_by = request.user
                entry.save()

            return redirect( 'notebook_entry', entry_uuid = entry.uuid )

        notebook_entries = trip.notebook_entries.all()

        trip_page_context = TripPageContext(
            active_page = TripPage.NOTES,
            request_member = request_member,
        )
        notebook_page_context = NotebookPageContext(
            notebook_entries = notebook_entries,
            notebook_entry_uuid = entry.uuid
        )

        context = {
            'trip_page': trip_page_context,
            'notebook_page': notebook_page_context,
            'form': form,
            'entry': entry,
        }

        return render(request, 'notebook/pages/notebook_entry.html', context, status=400)


class NotebookAutoSaveView( LoginRequiredMixin, TripViewMixin, View ):
    """AJAX endpoint for auto-saving notebook entries."""

    def post(self, request, entry_uuid: UUID, *args, **kwargs) -> JsonResponse:
        entry = get_object_or_404(
            NotebookEntry,
            uuid = entry_uuid,
        )
        request_member = get_object_or_404(
            TripMember,
            trip = entry.trip,
            user = request.user,
        )
        self.assert_is_editor( request_member )
        trip = request_member.trip

        entry = get_object_or_404(
            NotebookEntry,
            pk = entry.pk,
            trip = trip,
        )

        # Parse and validate request
        autosave_request, error_response = NotebookAutoSaveHelper.parse_autosave_request(
            request_body = request.body
        )
        if error_response:
            return error_response

        try:
            with transaction.atomic():
                # Use select_for_update to lock the row for the duration of the transaction
                locked_entry = NotebookEntry.objects.select_for_update().get(pk=entry.pk)
                
                # Check version conflict - backward compatible (treat missing version as no check)
                if autosave_request.client_version is not None:
                    if locked_entry.edit_version != autosave_request.client_version:
                        return NotebookConflictHelper.build_conflict_response(
                            request = request,
                            entry = locked_entry,
                            client_text = autosave_request.text
                        )

                # Check for date conflicts if date is changing (inside transaction for atomicity)
                date_error = NotebookAutoSaveHelper.validate_date_uniqueness(
                    entry = locked_entry,
                    new_date = autosave_request.new_date
                )
                if date_error:
                    return date_error

                # Update fields and increment version atomically
                updated_entry = NotebookAutoSaveHelper.update_entry_atomically(
                    entry = locked_entry,
                    text = autosave_request.text,
                    user = request.user,
                    new_date = autosave_request.new_date
                )

            return JsonResponse({
                'status': 'success',
                'version': updated_entry.edit_version,
                'modified_datetime': updated_entry.modified_datetime.isoformat(),
            })

        except NotebookEntry.DoesNotExist:
            logger.error(f'Entry {entry.pk} not found during atomic update')
            return JsonResponse(
                {'status': 'error', 'message': 'Entry not found'},
                status=404
            )
        except IntegrityError as e:
            logger.warning(f'Integrity constraint violation for entry {entry.pk}: {e}')
            return JsonResponse(
                {'status': 'error', 'message': 'Unable to save - entry date conflicts with another entry'},
                status=409
            )
        except DatabaseError as e:
            logger.error(f'Database error auto-saving notebook entry {entry.pk}: {e}')
            return JsonResponse(
                {'status': 'error', 'message': 'Database error occurred'},
                status=500
            )
