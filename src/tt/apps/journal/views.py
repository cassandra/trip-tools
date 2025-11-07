from datetime import date as date_class, timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.views.generic import View

from tt.apps.common.antinode import http_response
from tt.apps.console.console_helper import ConsoleSettingsHelper
from tt.apps.images.models import TripImage
from tt.apps.trips.context import TripPageContext
from tt.apps.trips.enums import TripPage
from tt.apps.trips.mixins import TripViewMixin
from tt.async_view import ModalView

from .context import JournalPageContext
from .enums import JournalVisibility
from .forms import JournalForm
from .models import Journal, JournalEntry
from .utils import get_entry_date_boundaries


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
                JournalEntry.objects.create(
                    journal = journal,
                    date = notebook_entry.date,
                    timezone = journal.timezone,
                    text = notebook_entry.text,
                    source_notebook_entry = notebook_entry,
                    source_notebook_version = notebook_entry.edit_version,
                    modified_by = request.user,
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

            # Generate default title: journal title + date
            default_title = f"{journal.title} - {default_date.strftime('%B %d, %Y')}"

            # Create new entry
            entry = JournalEntry.objects.create(
                journal = journal,
                date = default_date,
                timezone = default_timezone,
                title = default_title,
                text = '',
                modified_by = request.user,
            )

            # Redirect to the edit view for the new entry
            return redirect('journal_entry', trip_id=trip.pk, entry_pk=entry.pk)

        # Fetch accessible images for the entry's date
        start_dt, end_dt = get_entry_date_boundaries(entry.date, entry.timezone)
        accessible_images = TripImage.objects.accessible_to_user_in_trip_for_date_range(
            user = request.user,
            trip = trip,
            start_datetime = start_dt,
            end_datetime = end_dt,
        )

        journal_entries = journal.entries.all()
        journal_page_context = JournalPageContext(
            journal = journal,
            journal_entries = journal_entries,
            journal_entry_pk = entry_pk,
        )
        context = {
            'trip_page': trip_page_context,
            'journal_page': journal_page_context,
            'journal': journal,
            'entry': entry,
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

    TODO: Implement autosave functionality similar to NotebookEntry.
    - Accept JSON request body with date, title, text, reference_image_id, version
    - Validate and save atomically
    - Handle version conflicts
    - Return JSON response with version and timestamp
    """

    def post(self, request, trip_id: int, entry_pk: int, *args, **kwargs) -> JsonResponse:
        request_member = self.get_trip_member(request, trip_id=trip_id)
        self.assert_is_editor(request_member)

        # TODO: Implement autosave logic
        # - Parse JSON request
        # - Lock entry with select_for_update()
        # - Check version conflict
        # - Update entry atomically
        # - Return success JSON with new version

        return JsonResponse({
            'status': 'error',
            'message': 'TODO: Implement JournalEntryAutosaveView',
        }, status=501)


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

        # Get scope filter (stub for now - will implement filtering logic later)
        scope = request.GET.get('scope', 'all')  # noqa: F841
        # Valid values: 'all', 'unused', 'in-use'
        # For now, we ignore this and always show all images
        # TODO: Apply scope filtering when text editing is implemented

        # Get timezone from entry
        timezone = entry.timezone

        # Calculate date boundaries for the selected date
        start_dt, end_dt = get_entry_date_boundaries(selected_date, timezone)

        # Fetch accessible images for the selected date
        accessible_images = TripImage.objects.accessible_to_user_in_trip_for_date_range(
            user = request.user,
            trip = trip,
            start_datetime = start_dt,
            end_datetime = end_dt,
        )

        # TODO: Apply scope filtering when text editing is implemented
        # if scope == 'unused':
        #     # Filter to images not used in this entry
        #     pass
        # elif scope == 'in-use':
        #     # Filter to images used in this entry
        #     pass

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
