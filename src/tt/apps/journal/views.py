from datetime import date as date_class, timedelta
import logging
from uuid import UUID

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import DatabaseError, IntegrityError, transaction
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.generic import View

from tt.apps.common.antinode import http_response
from tt.apps.console.console_helper import ConsoleSettingsHelper
from tt.apps.members.models import TripMember
from tt.apps.trips.context import TripPageContext
from tt.apps.trips.enums import TripPage
from tt.apps.trips.mixins import TripViewMixin
from tt.async_view import ModalView

from .autosave_helpers import JournalAutoSaveHelper, JournalConflictHelper
from .context import JournalPageContext
from .enums import JournalVisibility, ImagePickerScope
from .forms import JournalForm, JournalEntryForm
from .mixins import JournalViewMixin
from .models import Journal, JournalEntry
from .services import JournalImagePickerService, JournalEntrySeederService

logger = logging.getLogger(__name__)


class JournalHomeView( LoginRequiredMixin, JournalViewMixin, TripViewMixin, View ):

    def get(self, request, trip_uuid: UUID, *args, **kwargs) -> HttpResponse:
        request_member = self.get_trip_member( request, trip_uuid = trip_uuid )
        self.assert_is_viewer(request_member)
        trip = request_member.trip

        # Fetch journal for trip (MVP: get_primary_for_trip)
        journal = Journal.objects.get_primary_for_trip( trip )
        if journal:
            redirect_url = reverse( 'journal', kwargs = { 'journal_uuid': journal.uuid })
            return HttpResponseRedirect( redirect_url )

        if not request_member.can_edit_trip:
            return self.journal_permission_denied_response(
                request = request,
                request_member = request_member,
                journal = None,
            )
        
        trip_page_context = TripPageContext(
            active_page = TripPage.JOURNAL,
            request_member = request_member,
        )
        journal_page_context = JournalPageContext(
            journal = None,
            journal_entries = list(),
        )
        context = {
            'trip_page': trip_page_context,
            'journal_page': journal_page_context,
        }
         
        return render(request, 'journal/pages/journal_start.html', context)


class JournalCreateView( LoginRequiredMixin, TripViewMixin, ModalView ):

    def get_template_name(self) -> str:
        return 'journal/modals/journal_create.html'

    def get(self, request, trip_uuid: UUID, *args, **kwargs) -> HttpResponse:
        request_member = self.get_trip_member( request, trip_uuid = trip_uuid )
        self.assert_is_editor(request_member)
        trip = request_member.trip

        tz_name = ConsoleSettingsHelper().get_tz_name(request.user)

        initial = {
            'title': trip.title,
            'description': trip.description,
            'timezone': tz_name,
        }
        form = JournalForm(initial=initial)

        context = {
            'form': form,
            'trip': trip,
        }
        return self.modal_response(request, context=context)

    def post(self, request, trip_uuid: UUID, *args, **kwargs) -> HttpResponse:
        request_member = self.get_trip_member( request, trip_uuid = trip_uuid )
        self.assert_is_editor(request_member)
        trip = request_member.trip

        form = JournalForm(request.POST)

        if form.is_valid():
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
            'trip': trip,
        }
        return self.modal_response(request, context=context, status=400)


class JournalEditView( LoginRequiredMixin, TripViewMixin, ModalView ):

    def get_template_name(self) -> str:
        return 'journal/modals/journal_edit.html'

    def get(self, request, journal_uuid: UUID, *args, **kwargs) -> HttpResponse:
        journal = get_object_or_404(
            Journal,
            uuid = journal_uuid,
        )
        request_member = get_object_or_404(
            TripMember,
            trip = journal.trip,
            user = request.user,
        )
        self.assert_is_editor(request_member)

        form = JournalForm(instance=journal)

        context = {
            'form': form,
            'journal': journal,
            'trip': journal.trip,
        }
        return self.modal_response(request, context=context)

    def post(self, request, journal_uuid: UUID, *args, **kwargs) -> HttpResponse:
        journal = get_object_or_404(
            Journal,
            uuid = journal_uuid,
        )
        request_member = get_object_or_404(
            TripMember,
            trip = journal.trip,
            user = request.user,
        )
        self.assert_is_editor(request_member)

        form = JournalForm(request.POST, instance=journal)

        if form.is_valid():
            journal = form.save(commit=False)
            journal.modified_by = request.user
            journal.save()

            return self.refresh_response(request)

        context = {
            'form': form,
            'journal': journal,
            'trip': journal.trip,
        }
        return self.modal_response(request, context=context, status=400)


class JournalView(LoginRequiredMixin, JournalViewMixin, TripViewMixin, View):

    def get(self, request, journal_uuid: UUID, *args, **kwargs) -> HttpResponse:
        journal = get_object_or_404(
            Journal,
            uuid = journal_uuid,
        )
        request_member = get_object_or_404(
            TripMember,
            trip = journal.trip,
            user = request.user,
        )
        self.assert_is_viewer(request_member)

        if not request_member.can_edit_trip:
            return self.journal_permission_denied_response(
                request = request,
                request_member = request_member,
                journal = journal,
            )
        
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

        return render(request, 'journal/pages/journal.html', context)


class JournalEntryNewView( LoginRequiredMixin, JournalViewMixin, TripViewMixin, View ):

    def get(self, request, journal_uuid : UUID, *args, **kwargs) -> HttpResponse:
        journal = get_object_or_404(
            Journal,
            uuid = journal_uuid,
        )
        request_member = get_object_or_404(
            TripMember,
            trip = journal.trip,
            user = request.user,
        )
        self.assert_is_viewer(request_member)

        if not request_member.can_edit_trip:
            return self.journal_permission_denied_response(
                request = request,
                request_member = request_member,
                journal = journal,
            )
        
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
        return redirect( 'journal_entry', entry_uuid = entry.uuid )


class JournalEntryView( LoginRequiredMixin, JournalViewMixin, TripViewMixin, View ):

    def get(self, request, entry_uuid: UUID, *args, **kwargs) -> HttpResponse:
        entry = get_object_or_404(
            JournalEntry,
            uuid = entry_uuid,
        )
        request_member = get_object_or_404(
            TripMember,
            trip = entry.journal.trip,
            user = request.user,
        )
        self.assert_is_viewer(request_member)

        if not request_member.can_edit_trip:
            return self.journal_permission_denied_response(
                request = request,
                request_member = request_member,
                journal = entry.journal,
            )

        accessible_images = JournalImagePickerService.get_accessible_images_for_image_picker(
            trip = entry.journal.trip,
            user = request.user,
            date = entry.date,
            timezone = entry.timezone,
            scope = ImagePickerScope.DEFAULT,
        )

        trip_page_context = TripPageContext(
            active_page = TripPage.JOURNAL,
            request_member = request_member,
        )
        
        journal_entries = entry.journal.entries.all()
        journal_page_context = JournalPageContext(
            journal = entry.journal,
            journal_entries = journal_entries,
            journal_entry_uuid = entry.uuid,
        )

        # Create form for entry metadata fields
        journal_entry_form = JournalEntryForm(instance=entry)

        context = {
            'trip_page': trip_page_context,
            'journal_page': journal_page_context,
            'journal': entry.journal,
            'entry': entry,
            'journal_entry_form': journal_entry_form,
            'accessible_images': accessible_images,
            'trip': entry.journal.trip,
            'show_source_changed_warning': entry.has_source_notebook_changed,
        }
        return render(request, 'journal/pages/journal_entry.html', context)


class JournalEntryAutosaveView(LoginRequiredMixin, TripViewMixin, View):

    def post(self, request, entry_uuid: UUID, *args, **kwargs) -> JsonResponse:
        entry = get_object_or_404(
            JournalEntry,
            uuid = entry_uuid,
        )
        request_member = get_object_or_404(
            TripMember,
            trip = entry.journal.trip,
            user = request.user,
        )
        self.assert_is_editor(request_member)

        autosave_request, error_response = JournalAutoSaveHelper.parse_autosave_request(
            request_body = request.body
        )
        if error_response:
            return error_response

        sanitized_text = JournalAutoSaveHelper.sanitize_html_content(autosave_request.text)

        try:
            with transaction.atomic():
                # Use select_for_update to lock the row for the duration of the transaction
                locked_entry = JournalEntry.objects.select_for_update().get(pk=entry.pk)

                # Check version conflict - backward compatible (treat missing version as no check)
                if autosave_request.client_version is not None:
                    if locked_entry.edit_version != autosave_request.client_version:
                        return JournalConflictHelper.build_conflict_response(
                            request = request,
                            entry = locked_entry,
                            client_text = autosave_request.text  # Show unsanitized version in diff
                        )

                # Check for date conflicts if date is changing (inside transaction for atomicity)
                if autosave_request.new_date:
                    date_error = JournalAutoSaveHelper.validate_date_uniqueness(
                        entry = locked_entry,
                        new_date = autosave_request.new_date
                    )
                    if date_error:
                        return date_error

                # Update fields and increment version atomically
                updated_entry = JournalAutoSaveHelper.update_entry_atomically(
                    entry = locked_entry,
                    text = sanitized_text,  # Use sanitized HTML
                    user = request.user,
                    new_date = autosave_request.new_date,
                    new_title = autosave_request.new_title,
                    new_timezone = autosave_request.new_timezone,
                    new_reference_image_uuid = autosave_request.new_reference_image_uuid
                )

            return JsonResponse({
                'status': 'success',
                'version': updated_entry.edit_version,
                'modified_datetime': updated_entry.modified_datetime.isoformat(),
            })

        except JournalEntry.DoesNotExist:
            logger.error(f'Entry {entry.pk} not found during atomic update')
            return JsonResponse(
                {'status': 'error', 'message': 'Entry not found'},
                status = 404
            )
        except IntegrityError as e:
            logger.warning(f'Integrity constraint violation for entry {entry.pk}: {e}')
            return JsonResponse(
                {'status': 'error', 'message': 'Unable to save - entry date conflicts with another entry'},
                status = 409
            )
        except DatabaseError as e:
            logger.error(f'Database error auto-saving journal entry {entry.pk}: {e}')
            return JsonResponse(
                {'status': 'error', 'message': 'Database error occurred'},
                status = 500
            )


class JournalEntryDeleteModalView( LoginRequiredMixin, TripViewMixin, ModalView ):

    def get_template_name(self) -> str:
        return 'journal/modals/journal_entry_delete.html'

    def get(self, request, entry_uuid: UUID, *args, **kwargs) -> HttpResponse:
        entry = get_object_or_404(
            JournalEntry,
            uuid = entry_uuid,
        )
        request_member = get_object_or_404(
            TripMember,
            trip = entry.journal.trip,
            user = request.user,
        )
        self.assert_is_editor(request_member)
        trip = request_member.trip
        context = {
            'trip': trip,
            'journal': entry.journal,
            'journal_entry': entry,
        }
        return self.modal_response(request, context=context)

    def post(self, request, entry_uuid: UUID, *args, **kwargs) -> HttpResponse:
        entry = get_object_or_404(
            JournalEntry,
            uuid = entry_uuid,
        )
        request_member = get_object_or_404(
            TripMember,
            trip = entry.journal.trip,
            user = request.user,
        )
        self.assert_is_editor(request_member)

        with transaction.atomic():
            entry.delete()

        redirect_url = reverse( 'journal', kwargs = { 'journal_uuid': entry.journal.uuid })
        return self.redirect_response( request, redirect_url )


class JournalEntryImagePickerView( LoginRequiredMixin, TripViewMixin, View ):

    def get(self, request, entry_uuid: UUID, *args, **kwargs) -> HttpResponse:
        entry = get_object_or_404(
            JournalEntry,
            uuid = entry_uuid,
        )
        request_member = get_object_or_404(
            TripMember,
            trip = entry.journal.trip,
            user = request.user,
        )
        self.assert_is_viewer(request_member)
        trip = request_member.trip

        selected_date_str = request.GET.get('date', None)
        if not selected_date_str:
            return http_response({'error': 'Date parameter required'}, status=400)

        try:
            selected_date = date_class.fromisoformat(selected_date_str)
        except ValueError:
            return http_response({'error': 'Invalid date format'}, status=400)

        accessible_images = JournalImagePickerService.get_accessible_images_for_image_picker(
            trip=trip,
            user=request.user,
            date=selected_date,
            timezone=entry.timezone,
            scope=ImagePickerScope.DEFAULT,
        )

        context = {
            'accessible_images': accessible_images,
            'trip': trip,
        }
        gallery_html = render_to_string(
            'journal/components/journal_image_gallery_grid.html',
            context,
            request=request
        )

        return http_response({'insert': {'journal-image-gallery': gallery_html}})


class JournalEditorHelpView(LoginRequiredMixin, ModalView):

    def get_template_name(self) -> str:
        return 'journal/modals/journal_editor_help.html'

    def get(self, request, *args, **kwargs) -> HttpResponse:
        # No context needed - help is generic
        context = {}
        return self.modal_response(request, context=context)
