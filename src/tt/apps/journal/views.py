from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.generic import View

from tt.apps.trips.context import TripPageContext
from tt.apps.trips.enums import TripPage
from tt.apps.trips.mixins import TripViewMixin
from tt.async_view import ModalView

from .context import JournalPageContext


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

        # TODO: Fetch journal for trip (MVP: get_primary_for_trip)
        # For now, create empty contexts to support template structure
        journal = None  # Will be: Journal.objects.get_primary_for_trip(trip)
        journal_entries = []  # Will be: journal.entries.all() if journal else []

        trip_page_context = TripPageContext(
            active_page = TripPage.JOURNAL,
            request_member = request_member,
        )
        journal_page_context = JournalPageContext(
            journal_entries = journal_entries
        )
        context = {
            'trip_page': trip_page_context,
            'journal_page': journal_page_context,
        }
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

        # TODO: Build context with form
        context = {
            'trip_id': trip_id,
        }
        return self.modal_response(request, context=context)

    def post(self, request, trip_id: int, *args, **kwargs) -> HttpResponse:
        request_member = self.get_trip_member(request, trip_id=trip_id)
        self.assert_is_editor(request_member)

        # TODO: Process form
        # - Create Journal
        # - Create JournalEntry objects (seeded from NotebookEntry if requested)
        # - Return refresh or redirect

        return HttpResponse("TODO: Implement CreateJournalView POST")


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

    def get(self, request, trip_id: int, entry_pk: int, *args, **kwargs) -> HttpResponse:
        request_member = self.get_trip_member(request, trip_id=trip_id)
        self.assert_is_viewer(request_member)
        trip = request_member.trip

        # TODO: Implement view logic
        # - Fetch JournalEntry (via get_object_or_404)
        # - Fetch Journal (via entry.journal)
        # - Fetch all journal entries for sidebar
        # For now, create empty contexts to support template structure
        journal = None  # Will be: Journal.objects.get_primary_for_trip(trip)
        journal_entries = []  # Will be: journal.entries.all() if journal else []

        trip_page_context = TripPageContext(
            active_page = TripPage.JOURNAL,
            request_member = request_member,
        )
        journal_page_context = JournalPageContext(
            journal_entries = journal_entries,
            journal_entry_pk = entry_pk
        )
        context = {
            'trip_page': trip_page_context,
            'journal_page': journal_page_context,
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
