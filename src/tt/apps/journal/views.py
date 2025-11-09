from datetime import date as date_class, timedelta
import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import DatabaseError, IntegrityError, transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.views.generic import View

from tt.apps.common.antinode import http_response
from tt.apps.console.console_helper import ConsoleSettingsHelper
from tt.apps.trips.context import TripPageContext
from tt.apps.trips.enums import TripPage
from tt.apps.trips.mixins import TripViewMixin
from tt.async_view import ModalView

from .autosave_helpers import JournalAutoSaveHelper, JournalConflictHelper
from .context import JournalPageContext
from .enums import JournalVisibility, ImagePickerScope
from .forms import JournalForm, JournalEntryForm
from .models import Journal, JournalEntry
from .services import JournalImagePickerService, JournalEntrySeederService

logger = logging.getLogger(__name__)


class JournalHomeView(LoginRequiredMixin, TripViewMixin, View):
    """
    Home view for journal management - lists journals for a trip.

    TODO: Implement journal listing and management functionality.
    - Display list of journals for trip (MVP: single journal)
    - Show journal metadata (title, description, visibility)
    - Create new journal button (modal)
    - Link to journal entries
    - Link to public journal view
    """

    def get(self, request, trip_id: int, *args, **kwargs) -> HttpResponse:
        request_member = self.get_trip_member(request, trip_id=trip_id)
        self.assert_is_viewer(request_member)
        trip = request_member.trip

        # Fetch journal for trip (MVP: get_primary_for_trip)
        journal = Journal.objects.get_primary_for_trip(trip)
        journal_entries = journal.entries.all() if journal else []

        trip_page_context = TripPageContext(
            active_page = TripPage.JOURNAL,
            request_member = request_member,
        )
        journal_page_context = JournalPageContext(
            journal = journal,
            journal_entries = journal_entries
        )
        context = {
            'trip_page': trip_page_context,
            'journal_page': journal_page_context,
            'journal': journal,
            'journal_entries': journal_entries,
        }

        # Check permissions for editing
        if not request_member.can_edit_trip:
            # Non-editors cannot edit journal entries - show permission denied
            return render(request, 'journal/pages/journal_permission_denied.html', context)
        
        return render(request, 'journal/pages/journal_home.html', context)


class CreateJournalView(LoginRequiredMixin, TripViewMixin, ModalView):
    """
    Modal view for creating a new journal.

    TODO: Implement journal creation functionality.
    - Show form with title, description, timezone, visibility
    - Optionally seed from notebook entries
    - Create journal and initial journal entries
    - Redirect to journal home or first entry
    """

    def get_template_name(self) -> str:
        return 'journal/modals/journal_create.html'

    def get(self, request, trip_id: int, *args, **kwargs) -> HttpResponse:
        request_member = self.get_trip_member(request, trip_id=trip_id)
        self.assert_is_editor(request_member)
        trip = request_member.trip

        # Get user's timezone setting
        tz_name = ConsoleSettingsHelper().get_tz_name(request.user)

        # Create form with initial values from trip and user
        initial = {
            'title': trip.title,
            'description': trip.description,
            'timezone': tz_name,
        }
        form = JournalForm(initial=initial)

        context = {
            'form': form,
            'trip_id': trip_id,
        }
        return self.modal_response(request, context=context)

    def post(self, request, trip_id: int, *args, **kwargs) -> HttpResponse:
        request_member = self.get_trip_member(request, trip_id=trip_id)
        self.assert_is_editor(request_member)
        trip = request_member.trip

        form = JournalForm(request.POST)

        if form.is_valid():
            # Create journal with form data
            journal = form.save(commit=False)
            journal.trip = trip
            journal.visibility = JournalVisibility.PRIVATE
            journal.modified_by = request.user
            journal.save()

            # Seed journal entries from notebook entries
            notebook_entries = trip.notebook_entries.all()
            for notebook_entry in notebook_entries:
                JournalEntrySeederService.create_from_notebook_entry(
                    notebook_entry=notebook_entry,
                    journal=journal,
                    user=request.user,
                )

            return self.refresh_response(request)

        context = {
            'form': form,
            'trip_id': trip_id,
        }
        return self.modal_response(request, context=context, status=400)


class JournalEntryView(LoginRequiredMixin, TripViewMixin, View):
    """
    View for editing a journal entry.

    TODO: Implement journal entry editing functionality.
    - Display entry edit form (date, title, text, reference_image)
    - Show suggested images for this date
    - Autosave functionality (similar to NotebookEntry)
    - Handle GET for both editor and viewer (readonly for viewer)
    - Handle POST for non-JS fallback
    """

    def get(self, request, trip_id: int, entry_pk: int = None, *args, **kwargs) -> HttpResponse:
        request_member = self.get_trip_member(request, trip_id=trip_id)
        self.assert_is_viewer(request_member)
        trip = request_member.trip

        # Get the primary journal for the trip
        journal = Journal.objects.get_primary_for_trip(trip)
        if not journal:
            # TODO: Handle case where no journal exists - redirect to journal home
            return redirect('journal_home', trip_id=trip.pk)

        trip_page_context = TripPageContext(
            active_page = TripPage.JOURNAL,
            request_member = request_member,
        )
        
        # Check permissions for editing
        if not request_member.can_edit_trip:
            # Non-editors cannot edit journal entries - show permission denied
            journal_entries = journal.entries.all() if journal else []
            journal_page_context = JournalPageContext(
                journal = journal,
                journal_entries = journal_entries,
            )
            context = {
                'trip_page': trip_page_context,
                'journal_page': journal_page_context,
                'journal': journal,
            }
            return render(request, 'journal/pages/journal_permission_denied.html', context)
        
        if entry_pk:
            # Existing entry - fetch it
            entry = get_object_or_404(
                JournalEntry,
                pk = entry_pk,
                journal = journal,
            )
        else:
            # New entry creation
            # Only editors can create new entries
            self.assert_is_editor(request_member)

            # Calculate default date and timezone
            latest_entry = journal.entries.order_by('-date').first()
            if latest_entry:
                # Subsequent entry: inherit from previous entry
                default_date = latest_entry.date + timedelta(days=1)
                default_timezone = latest_entry.timezone
            else:
                # First entry: use today and inherit from journal
                default_date = date_class.today()
                default_timezone = journal.timezone

            # Create new entry (title will be auto-generated from date in model.save())
            entry = JournalEntry.objects.create(
                journal = journal,
                date = default_date,
                timezone = default_timezone,
                text = '',
                modified_by = request.user,
            )

            # Redirect to the edit view for the new entry
            return redirect('journal_entry', trip_id=trip.pk, entry_pk=entry.pk)

        # Fetch accessible images for the entry's date
        accessible_images = JournalImagePickerService.get_accessible_images_for_image_picker(
            trip=trip,
            user=request.user,
            date=entry.date,
            timezone=entry.timezone,
            scope=ImagePickerScope.DEFAULT,
        )

        journal_entries = journal.entries.all()
        journal_page_context = JournalPageContext(
            journal = journal,
            journal_entries = journal_entries,
            journal_entry_pk = entry_pk,
        )

        # Create form for entry metadata fields
        journal_entry_form = JournalEntryForm(instance=entry)

        context = {
            'trip_page': trip_page_context,
            'journal_page': journal_page_context,
            'journal': journal,
            'entry': entry,
            'journal_entry_form': journal_entry_form,
            'accessible_images': accessible_images,
            'trip': trip,
        }
        return render(request, 'journal/pages/journal_entry.html', context)

    def post(self, request, trip_id: int, entry_pk: int, *args, **kwargs) -> HttpResponse:
        request_member = self.get_trip_member(request, trip_id=trip_id)
        self.assert_is_editor(request_member)

        # TODO: Non-JS fallback save
        # - Process form
        # - Save entry
        # - Redirect to entry

        return HttpResponse("TODO: Implement JournalEntryView POST")


class JournalEntryAutosaveView(LoginRequiredMixin, TripViewMixin, View):
    """
    AJAX endpoint for autosaving journal entries.

    Handles auto-save requests with HTML sanitization, version conflict detection,
    and atomic updates. Similar to NotebookEntry autosave but with HTML content.
    """

    def get(self, request, trip_id: int, entry_pk: int, *args, **kwargs) -> JsonResponse:
        return JsonResponse(
            {'status': 'error', 'message': 'Method not allowed'},
            status=405,
        )

    def post(self, request, trip_id: int, entry_pk: int, *args, **kwargs) -> JsonResponse:
        request_member = self.get_trip_member(request, trip_id=trip_id)
        self.assert_is_editor(request_member)
        trip = request_member.trip

        # Get the journal and entry
        journal = Journal.objects.get_primary_for_trip(trip)
        if not journal:
            return JsonResponse(
                {'status': 'error', 'message': 'No journal found for this trip'},
                status=404
            )

        entry = get_object_or_404(
            JournalEntry,
            pk=entry_pk,
            journal=journal,
        )

        # Parse and validate request
        autosave_request, error_response = JournalAutoSaveHelper.parse_autosave_request(
            request_body=request.body
        )
        if error_response:
            return error_response

        # Sanitize HTML content
        sanitized_text = JournalAutoSaveHelper.sanitize_html_content(autosave_request.text)

        try:
            with transaction.atomic():
                # Use select_for_update to lock the row for the duration of the transaction
                locked_entry = JournalEntry.objects.select_for_update().get(pk=entry.pk)

                # Check version conflict - backward compatible (treat missing version as no check)
                if autosave_request.client_version is not None:
                    if locked_entry.edit_version != autosave_request.client_version:
                        return JournalConflictHelper.build_conflict_response(
                            request=request,
                            entry=locked_entry,
                            client_text=autosave_request.text  # Show unsanitized version in diff
                        )

                # Check for date conflicts if date is changing (inside transaction for atomicity)
                if autosave_request.new_date:
                    date_error = JournalAutoSaveHelper.validate_date_uniqueness(
                        entry=locked_entry,
                        new_date=autosave_request.new_date
                    )
                    if date_error:
                        return date_error

                # Update fields and increment version atomically
                updated_entry = JournalAutoSaveHelper.update_entry_atomically(
                    entry=locked_entry,
                    text=sanitized_text,  # Use sanitized HTML
                    user=request.user,
                    new_date=autosave_request.new_date,
                    new_title=autosave_request.new_title,
                    new_timezone=autosave_request.new_timezone,
                    new_reference_image_id=autosave_request.new_reference_image_id
                )

            return JsonResponse({
                'status': 'success',
                'version': updated_entry.edit_version,
                'modified_datetime': updated_entry.modified_datetime.isoformat(),
            })

        except JournalEntry.DoesNotExist:
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
            logger.error(f'Database error auto-saving journal entry {entry_pk}: {e}')
            return JsonResponse(
                {'status': 'error', 'message': 'Database error occurred'},
                status=500
            )


class JournalEntryImagePickerView(LoginRequiredMixin, TripViewMixin, View):
    """
    AJAX endpoint for fetching images for a specific date.

    Used by the image picker to refresh the image gallery when the date is changed.
    Returns rendered HTML for the image gallery grid.
    """

    def get(self, request, trip_id: int, entry_pk: int, *args, **kwargs) -> HttpResponse:
        request_member = self.get_trip_member(request, trip_id=trip_id)
        self.assert_is_viewer(request_member)
        trip = request_member.trip

        # Get the journal entry
        journal = Journal.objects.get_primary_for_trip(trip)
        if not journal:
            return http_response({'error': 'No journal found'}, status=404)

        entry = get_object_or_404(
            JournalEntry,
            pk = entry_pk,
            journal = journal,
        )

        # Get the selected date from query parameter (YYYY-MM-DD format)
        selected_date_str = request.GET.get('date', None)
        if not selected_date_str:
            return http_response({'error': 'Date parameter required'}, status=400)

        try:
            selected_date = date_class.fromisoformat(selected_date_str)
        except ValueError:
            return http_response({'error': 'Invalid date format'}, status=400)

        # Fetch accessible images for the selected date
        # Phase 1: Always use DEFAULT scope - filtering done client-side
        accessible_images = JournalImagePickerService.get_accessible_images_for_image_picker(
            trip=trip,
            user=request.user,
            date=selected_date,
            timezone=entry.timezone,
            scope=ImagePickerScope.DEFAULT,
        )

        # Render the image gallery grid
        context = {
            'accessible_images': accessible_images,
            'trip': trip,
        }
        gallery_html = render_to_string(
            'journal/components/journal_image_gallery_grid.html',
            context,
            request=request
        )

        # Return antinode response with the gallery HTML
        return http_response({'insert': {'journal-image-gallery': gallery_html}})


class JournalEditorHelpView(LoginRequiredMixin, ModalView):
    """
    Modal view for displaying editing help for journal editor.

    Shows keyboard shortcuts and editor guidance.
    Accessible to all authenticated users (trip-independent).
    """

    def get_template_name(self) -> str:
        return 'journal/modals/journal_editor_help.html'

    def get(self, request, *args, **kwargs) -> HttpResponse:
        # No context needed - help is generic
        context = {}
        return self.modal_response(request, context=context)
