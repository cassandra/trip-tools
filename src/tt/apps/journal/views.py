from datetime import date as date_class, timedelta
import logging
from typing import Optional, Tuple
from uuid import UUID

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User as UserType
from django.db import transaction
from django.http import HttpRequest, HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.generic import View


from tt.apps.common.antinode import http_response
from tt.apps.console.console_helper import ConsoleSettingsHelper
from tt.apps.images.enums import UploadStatus
from tt.apps.images.views import EntityImagePickerView, EntityImageUploadView
from tt.apps.images.services import ImageUploadService
from tt.apps.members.models import TripMember
from tt.apps.trips.context import TripPageContext
from tt.apps.trips.enums import TripPage
from tt.apps.trips.mixins import TripViewMixin
from tt.apps.trips.models import Trip
from tt.async_view import ModalView

from .autosave_helpers import (
    JournalAutoSaveHelper,
    JournalConflictHelper,
    DateChangeOrchestrator,
    AutosaveResponseBuilder,
    ExceptionResponseBuilder,
)
from .context import JournalPageContext
from .enums import JournalVisibility
from .forms import JournalForm, JournalEntryForm, JournalVisibilityForm
from .helpers import PublishingStatusHelper, JournalPublishContextBuilder
from .mixins import JournalViewMixin
from .models import Journal, JournalEntry, PROLOGUE_DATE, EPILOGUE_DATE
from .schemas import PublishingStatus
from .services import JournalRestoreService, JournalPublishingService

from tt.apps.images.helpers import TripImageHelpers
from tt.apps.images.services import ImagePickerService

from tt.environment.constants import TtConst

from tt.apps.travelog.models import Travelog
from tt.apps.travelog.services import PublishingService

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
            return self.journal_view_only_response(
                request = request,
                request_member = request_member,
                journal = None,
            )
        
        trip_page_context = TripPageContext(
            active_page = TripPage.JOURNAL,
            request_member = request_member,
        )
        journal_page_context = JournalPageContext.create(
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

            redirect_url = reverse( 'journal', kwargs = { 'journal_uuid': journal.uuid } )
            return self.redirect_response( request, redirect_url )

        context = {
            'form': form,
            'trip': trip,
        }
        return self.modal_response( request, context = context, status = 400 )


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
            return self.journal_view_only_response(
                request = request,
                request_member = request_member,
                journal = journal,
            )

        journal_entries = list(journal.entries.all()) if journal else []

        # Get publishing status
        publishing_status = PublishingStatusHelper.get_publishing_status(journal)

        trip_page_context = TripPageContext(
            active_page = TripPage.JOURNAL,
            request_member = request_member,
        )
        journal_page_context = JournalPageContext.create(
            journal = journal,
            journal_entries = journal_entries,
        )
        context = {
            'trip_page': trip_page_context,
            'journal_page': journal_page_context,
            'journal': journal,
            'journal_entries': journal_entries,
            'journal_entry_count': len(journal_entries),
            'publishing_status': publishing_status,
        }

        return render(request, 'journal/pages/journal.html', context)


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


class JournalVisibilityChangeView( LoginRequiredMixin, TripViewMixin, ModalView ):

    def get_template_name(self) -> str:
        return 'journal/modals/journal_visibility.html'

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
        self.assert_is_admin(request_member)

        form = JournalVisibilityForm(journal=journal)

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
        self.assert_is_admin(request_member)

        form = JournalVisibilityForm(request.POST, journal=journal)

        if form.is_valid():
            # Get visibility enum value from string name
            visibility_name = form.cleaned_data['visibility']
            visibility = JournalVisibility[visibility_name]

            # Update journal visibility
            journal.visibility = visibility

            # Handle password setting based on form state
            if form.should_update_password():
                password = form.cleaned_data.get('password')
                journal.set_password(password)
            # If should_update_password() is False, existing password is preserved

            journal.modified_by = request.user
            journal.save()

            return self.refresh_response(request)

        context = {
            'form': form,
            'journal': journal,
            'trip': journal.trip,
        }
        return self.modal_response(request, context=context, status=400)


class JournalEntryNewView( LoginRequiredMixin, JournalViewMixin, TripViewMixin, View ):
    """
    Also used as base class for creating prologue and epilogue journal entries.

    Subclasses can override:
    - get_existing_entry(): Check for existing entry that should prevent creation
    - get_entry_date_and_timezone(): Provide date and timezone for new entry
    """

    def get_existing_entry( self, journal: Journal ) -> Optional[JournalEntry]:
        """
        Check for an existing entry that should prevent creation.
        Returns None by default (regular entries don't have this restriction).
        """
        return None

    def get_entry_date_and_timezone( self, journal: Journal ) -> Tuple[date_class, str]:
        """Get the date and timezone for the new entry."""
        latest_entry = journal.entries.order_by('-date').first()
        if latest_entry:
            return (latest_entry.date + timedelta(days=1), latest_entry.timezone)
        return (date_class.today(), journal.timezone)

    def get( self, request, journal_uuid: UUID, *args, **kwargs ) -> HttpResponse:
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
            return self.journal_view_only_response(
                request = request,
                request_member = request_member,
                journal = journal,
            )

        self.assert_is_editor(request_member)

        # Check if this type of entry already exists (for special entries)
        existing_entry = self.get_existing_entry(journal)
        if existing_entry:
            return redirect('journal_entry', entry_uuid=existing_entry.uuid)

        # Create new entry (title will be auto-generated from date in model.save())
        entry_date, entry_timezone = self.get_entry_date_and_timezone(journal)
        entry = JournalEntry.objects.create(
            journal = journal,
            date = entry_date,
            timezone = entry_timezone,
            text = '',
            modified_by = request.user,
        )
        return redirect('journal_entry', entry_uuid=entry.uuid)


class JournalPrologueNewView( JournalEntryNewView ):
    """Create a new prologue entry."""

    def get_existing_entry( self, journal: Journal ) -> Optional[JournalEntry]:
        return JournalEntry.objects.get_prologue( journal )

    def get_entry_date_and_timezone( self, journal: Journal ) -> Tuple[date_class, str]:
        return ( PROLOGUE_DATE, journal.timezone )


class JournalEpilogueNewView( JournalEntryNewView ):
    """Create a new epilogue entry."""

    def get_existing_entry( self, journal: Journal ) -> Optional[JournalEntry]:
        return JournalEntry.objects.get_epilogue(journal)

    def get_entry_date_and_timezone( self, journal: Journal ) -> Tuple[date_class, str]:
        return ( EPILOGUE_DATE, journal.timezone )


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
            return self.journal_view_only_response(
                request = request,
                request_member = request_member,
                journal = entry.journal,
            )

        # For prologue/epilogue entries, use recent images instead of date-based filtering
        # (date.min/date.max would cause overflow in date boundary calculations)
        is_recent_mode = entry.is_special_entry

        if is_recent_mode:
            accessible_images = TripImageHelpers.get_recent_images_for_trip_editors(
                trip = entry.journal.trip,
            )
            filter_date = None
        else:
            accessible_images = ImagePickerService.get_accessible_images_for_image_picker(
                trip = entry.journal.trip,
                user = request.user,
                date = entry.date,
                timezone = entry.timezone,
            )
            filter_date = entry.date

        trip_page_context = TripPageContext(
            active_page = TripPage.JOURNAL,
            request_member = request_member,
        )

        journal_entries = entry.journal.entries.all()
        journal_page_context = JournalPageContext.create(
            journal = entry.journal,
            journal_entries = list(journal_entries),
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
            'is_recent_mode': is_recent_mode,
            'filter_date': filter_date,
            'trip': entry.journal.trip,
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

                # Process date change and title auto-regeneration
                date_change_result = DateChangeOrchestrator.process_date_change(
                    entry = locked_entry,
                    new_date = autosave_request.new_date,
                    new_title = autosave_request.new_title,
                )

                # Update fields and increment version atomically
                updated_entry = JournalAutoSaveHelper.update_entry_atomically(
                    entry = locked_entry,
                    text = sanitized_text,
                    user = request.user,
                    new_date = date_change_result.final_date,
                    new_title = date_change_result.final_title,
                    new_timezone = autosave_request.new_timezone,
                    new_reference_image_uuid = autosave_request.new_reference_image_uuid,
                    new_include_in_publish = autosave_request.new_include_in_publish
                )

            return AutosaveResponseBuilder.build_success_response(
                request = request,
                updated_entry = updated_entry,
                date_changed = date_change_result.date_changed,
                title_updated = date_change_result.title_updated,
            )

        except Exception as e:
            return ExceptionResponseBuilder.handle_autosave_exception(
                exception = e,
                entry = entry,
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


class JournalEditorMultiImagePickerView( LoginRequiredMixin, TripViewMixin, View ):

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

        # Check if recent mode is requested
        is_recent_mode = request.GET.get('recent', '').lower() == 'true'

        if is_recent_mode:
            # Recent mode: Get recent images from trip editors
            accessible_images = TripImageHelpers.get_recent_images_for_trip_editors(
                trip=trip,
                limit=50
            )
        else:
            # Date-based mode: Use existing date-based filtering
            selected_date_str = request.GET.get('date', None)
            if not selected_date_str:
                return http_response({'error': 'Date parameter required'}, status=400)

            try:
                selected_date = date_class.fromisoformat(selected_date_str)
            except ValueError:
                return http_response({'error': 'Invalid date format'}, status=400)

            # Use entry timezone, fall back to journal timezone or UTC for special entries
            timezone = entry.timezone or entry.journal.timezone or 'UTC'
            accessible_images = ImagePickerService.get_accessible_images_for_image_picker(
                trip=trip,
                user=request.user,
                date=selected_date,
                timezone=timezone,
            )

        context = {
            'accessible_images': accessible_images,
            'trip': trip,
        }
        gallery_html = render_to_string(
            'journal/components/journal_editor_multi_image_gallery_grid.html',
            context,
            request=request
        )

        return http_response({'insert': {TtConst.JOURNAL_EDITOR_MULTI_IMAGE_GALLERY_ID: gallery_html}})


class JournalEditorHelpView(LoginRequiredMixin, ModalView):

    def get_template_name(self) -> str:
        return 'journal/modals/journal_editor_help.html'

    def get(self, request, *args, **kwargs) -> HttpResponse:
        # No context needed - help is generic
        context = {}
        return self.modal_response(request, context=context)


class JournalPublishModalView(LoginRequiredMixin, TripViewMixin, ModalView):

    def get_template_name(self) -> str:
        return 'journal/modals/journal_publish.html'

    def get( self, request, journal_uuid: UUID, *args, **kwargs ) -> HttpResponse:
        journal = self._get_journal_and_verify_access( journal_uuid, request.user )

        publishing_status = PublishingStatusHelper.get_publishing_status( journal = journal )
        visibility_form = JournalVisibilityForm( journal = journal )

        context = JournalPublishContextBuilder.build_modal_context(
            journal = journal,
            publishing_status = publishing_status,
            visibility_form = visibility_form
        )
        return self.modal_response( request, context = context )

    def post(self, request, journal_uuid: UUID, *args, **kwargs) -> HttpResponse:
        journal = self._get_journal_and_verify_access(journal_uuid, request.user)

        publishing_status = PublishingStatusHelper.get_publishing_status( journal= journal )
        visibility_form = JournalVisibilityForm( request.POST, journal = journal )

        if not visibility_form.is_valid():
            return self._build_error_response(
                request = request,
                journal = journal,
                publishing_status = publishing_status,
                visibility_form = visibility_form,
                status = 400
            )

        try:
            selected_entries = request.POST.getlist('selected_entries')
            travelog = JournalPublishingService.publish_with_selections_and_visibility(
                journal = journal,
                selected_entry_uuids = selected_entries,
                visibility_form = visibility_form,
                user = request.user
            )

            logger.info(
                f"Journal {journal.uuid} published as Travelog v{travelog.version_number} "
                f"by user {request.user}"
            )
            return self.refresh_response(request)

        except ValueError as e:
            logger.warning(f"Failed to publish journal {journal.uuid}: {e}")
            visibility_form.add_error( None, str(e) )
            return self._build_error_response(
                request = request,
                journal = journal,
                publishing_status = publishing_status,
                visibility_form = visibility_form,
                status = 400
            )

        except Exception as e:
            logger.error(f"Error publishing journal {journal.uuid}: {e}", exc_info=True)
            visibility_form.add_error(None, "An unexpected error occurred while publishing.")
            return self._build_error_response(
                request = request,
                journal = journal,
                publishing_status = publishing_status,
                visibility_form = visibility_form,
                status = 500
            )

    def _get_journal_and_verify_access( self, journal_uuid: UUID, user : UserType ) -> Journal:
        journal = get_object_or_404(Journal, uuid=journal_uuid)
        request_member = get_object_or_404(
            TripMember,
            trip = journal.trip,
            user = user,
        )
        self.assert_is_admin( request_member )
        return journal

    def _build_error_response( self,
                               request            : HttpRequest,
                               journal            : Journal,
                               publishing_status  : PublishingStatus,
                               visibility_form    : JournalVisibilityForm,
                               status             : int      ) -> HttpResponse:
        context = JournalPublishContextBuilder.build_modal_context(
            journal = journal,
            publishing_status = publishing_status,
            visibility_form = visibility_form
        )
        return self.modal_response(request, context=context, status=status)


class JournalVersionHistoryView( LoginRequiredMixin, TripViewMixin, ModalView ):

    def get_template_name(self) -> str:
        return 'journal/modals/version_history.html'

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

        # Get all published versions ordered by version number (newest first)
        travelogs = Travelog.objects.for_journal(journal).order_by('-version_number')

        context = {
            'request_member': request_member,
            'journal': journal,
            'travelogs': travelogs,
        }
        return self.modal_response(request, context=context)


class JournalSetCurrentVersionView( LoginRequiredMixin, TripViewMixin, ModalView ):

    def get_template_name(self) -> str:
        return 'journal/modals/journal_set_current_confirm.html'

    def get(self, request, journal_uuid: UUID, travelog_uuid: UUID, *args, **kwargs) -> HttpResponse:
        journal = get_object_or_404(
            Journal,
            uuid = journal_uuid,
        )
        request_member = get_object_or_404(
            TripMember,
            trip = journal.trip,
            user = request.user,
        )
        self.assert_is_admin(request_member)

        travelog = get_object_or_404(
            Travelog,
            uuid = travelog_uuid,
        )
        context = {
            'request_member': request_member,
            'journal': journal,
            'travelog': travelog,
        }
        return self.modal_response( request, context = context )

    def post(self, request, journal_uuid: UUID, travelog_uuid: UUID, *args, **kwargs) -> HttpResponse:
        """
        Set a travelog version as the current published version.

        This only changes which version is publicly visible.
        Does not affect the journal's working entries.
        """
        journal = get_object_or_404(
            Journal,
            uuid = journal_uuid,
        )
        request_member = get_object_or_404(
            TripMember,
            trip = journal.trip,
            user = request.user,
        )
        self.assert_is_admin(request_member)

        travelog = get_object_or_404(
            Travelog,
            uuid = travelog_uuid,
        )
        PublishingService.set_as_current(
            journal=journal,
            travelog=travelog
        )
        return self.refresh_response( request )


class JournalRestoreView( LoginRequiredMixin, TripViewMixin, ModalView ):

    def get_template_name(self) -> str:
        return 'journal/modals/journal_restore_confirm.html'

    def get(self, request, journal_uuid: UUID, travelog_uuid: UUID, *args, **kwargs) -> HttpResponse:
        journal = get_object_or_404(
            Journal,
            uuid = journal_uuid,
        )
        request_member = get_object_or_404(
            TripMember,
            trip = journal.trip,
            user = request.user,
        )
        self.assert_is_admin(request_member)

        travelog = get_object_or_404(
            Travelog,
            uuid = travelog_uuid,
        )
        context = {
            'request_member': request_member,
            'journal': journal,
            'travelog': travelog,
        }
        return self.modal_response( request, context = context )

    def post(self, request, journal_uuid: UUID, travelog_uuid: UUID, *args, **kwargs) -> HttpResponse:
        """
        Restore journal working copy from a published version.

        This DELETES all current journal entries and replaces them
        with entries from the selected version. DESTRUCTIVE operation.
        """
        journal = get_object_or_404(
            Journal,
            uuid = journal_uuid,
        )
        request_member = get_object_or_404(
            TripMember,
            trip = journal.trip,
            user = request.user,
        )
        self.assert_is_admin(request_member)

        travelog = get_object_or_404(
            Travelog,
            uuid = travelog_uuid,
        )
        _ = JournalRestoreService.restore_from_version(
            journal = journal,
            travelog = travelog,
            user = request.user
        )
        return self.refresh_response( request )


class JournalReferenceImagePickerView( EntityImagePickerView ):

    def get_template_name(self) -> str:
        return 'journal/modals/journal_reference_image_picker.html'

    def get_entity_model(self):
        return Journal

    def get_entity_uuid_param_name(self) -> str:
        return 'journal_uuid'

    def check_permission(self, request, entity: Journal) -> None:
        request_member = get_object_or_404(
            TripMember,
            trip=entity.trip,
            user=request.user,
        )
        self.assert_is_editor(request_member)

    def get_default_date_and_timezone(self, entity: Journal) -> Tuple[date_class, str]:
        """
        Priority:
        1. Date from first journal entry with a reference image
        2. Today's date with journal timezone
        """
        # Check journal entries for a reference image
        for journal_entry in entity.entries.order_by('date'):
            if journal_entry.reference_image:
                return (journal_entry.date, journal_entry.timezone)

        # Fallback to today with journal timezone
        return (date_class.today(), entity.timezone)

    def get_trip_from_entity(self, entity: Journal) -> Trip:
        return entity.trip

    def get_picker_url(self, entity: Journal) -> str:
        return reverse('journal_reference_image_picker', kwargs={'journal_uuid': entity.uuid})

    def get_upload_url(self, entity: Journal) -> str:
        return reverse('journal_image_upload', kwargs={'journal_uuid': entity.uuid})


class JournalImageUploadView(EntityImageUploadView):
    """
    Single-image upload mode - automatically sets uploaded image as
    Journal's reference image and triggers page refresh on success.
    """

    def get_template_name(self) -> str:
        return 'journal/modals/journal_image_upload.html'

    def get_max_files(self) -> int:
        return 1

    def check_permission(self, request, *args, **kwargs) -> None:
        """Verify user has editor permission for the journal's trip."""
        journal_uuid = kwargs.get('journal_uuid')
        journal = get_object_or_404(Journal, uuid=journal_uuid)
        request_member = get_object_or_404(
            TripMember,
            trip=journal.trip,
            user=request.user,
        )
        self.assert_is_editor(request_member)

    def get_upload_url(self, request, *args, **kwargs) -> str:
        """Return the URL for the Journal image upload endpoint."""
        journal_uuid = kwargs.get('journal_uuid')
        return reverse('journal_image_upload', kwargs={'journal_uuid': journal_uuid})

    def post(self, request, *args, **kwargs):
        """
        Handle upload and automatically set as Journal's reference image.

        On successful upload, sets the image as the Journal's reference image.
        JavaScript handles page refresh via onComplete callback.
        """
        
        journal_uuid = kwargs.get('journal_uuid')
        journal = get_object_or_404(Journal, uuid=journal_uuid)
        request_member = get_object_or_404(
            TripMember,
            trip=journal.trip,
            user=request.user,
        )
        self.assert_is_editor(request_member)

        uploaded_files = request.FILES.getlist('files')

        if not uploaded_files:
            return JsonResponse({'error': 'No file provided'}, status=400)

        if len(uploaded_files) > 1:
            return JsonResponse({'error': 'Only one image allowed'}, status=400)

        # Process the single file
        service = ImageUploadService()
        result = service.process_uploaded_image(
            uploaded_files[0],
            request.user,
            request=request,
        )

        if result.status == UploadStatus.SUCCESS:
            journal.reference_image = result.trip_image
            journal.save(update_fields=['reference_image'])

            # Return success - JS onComplete callback handles page refresh
            return JsonResponse({'files': [result.to_dict()]})

        return JsonResponse({
            'error': result.error_message or 'Upload failed'
        }, status=400)


class JournalEntryImagePickerView( EntityImagePickerView ):

    def get_template_name(self) -> str:
        return 'journal/modals/journal_entry_reference_image_picker.html'

    def get_entity_model(self):
        return JournalEntry

    def get_entity_uuid_param_name(self) -> str:
        return 'entry_uuid'

    def check_permission(self, request, entity: JournalEntry) -> None:
        request_member = get_object_or_404(
            TripMember,
            trip=entity.journal.trip,
            user=request.user,
        )
        self.assert_is_editor(request_member)

    def get_default_date_and_timezone(self, entity: JournalEntry) -> Tuple[date_class, str]:
        return (entity.date, entity.timezone)

    def get_trip_from_entity(self, entity: JournalEntry) -> Trip:
        return entity.journal.trip

    def get_picker_url(self, entity: JournalEntry) -> str:
        return reverse('journal_entry_reference_image_picker', kwargs={'entry_uuid': entity.uuid})

    def get_upload_url(self, entity: JournalEntry) -> str:
        return reverse('journal_entry_image_upload', kwargs={'entry_uuid': entity.uuid})

    def _should_use_recent_images_fallback(
        self,
        entity: JournalEntry,
        request_date_str: Optional[str]
    ) -> bool:
        """
        Override fallback logic for journal entries.

        For special entries (prologue/epilogue), always use fallback since they
        don't have meaningful dates for image filtering. For regular dated entries,
        disable fallback to show images from that specific date.
        """
        # Disable fallback if explicit date parameter provided (user browsing dates)
        if request_date_str:
            return False

        # Disable fallback if existing reference image with UTC date
        if entity.reference_image and entity.reference_image.datetime_utc:
            return False

        # Enable fallback for special entries (prologue/epilogue)
        if entity.is_special_entry:
            return True

        # Disable fallback for regular dated entries
        return False


class JournalEntryImageUploadView(EntityImageUploadView):
    """
    Single-image upload mode - automatically sets uploaded image as
    JournalEntry's reference image and triggers page refresh on success.
    """

    def get_template_name(self) -> str:
        return 'journal/modals/journal_entry_image_upload.html'

    def get_max_files(self) -> int:
        return 1

    def check_permission(self, request, *args, **kwargs) -> None:
        entry_uuid = kwargs.get('entry_uuid')
        entry = get_object_or_404(JournalEntry, uuid=entry_uuid)
        request_member = get_object_or_404(
            TripMember,
            trip=entry.journal.trip,
            user=request.user,
        )
        self.assert_is_editor(request_member)

    def get_upload_url(self, request, *args, **kwargs) -> str:
        entry_uuid = kwargs.get('entry_uuid')
        return reverse('journal_entry_image_upload', kwargs={'entry_uuid': entry_uuid})

    def post(self, request, *args, **kwargs):
        """
        Handle upload and automatically set as JournalEntry's reference image.

        On successful upload, sets the image as the entry's reference image.
        JavaScript handles page refresh via onComplete callback.
        """
        entry_uuid = kwargs.get('entry_uuid')
        entry = get_object_or_404(JournalEntry, uuid=entry_uuid)
        request_member = get_object_or_404(
            TripMember,
            trip=entry.journal.trip,
            user=request.user,
        )
        self.assert_is_editor(request_member)

        uploaded_files = request.FILES.getlist('files')

        if not uploaded_files:
            return JsonResponse({'error': 'No file provided'}, status=400)

        if len(uploaded_files) > 1:
            return JsonResponse({'error': 'Only one image allowed'}, status=400)

        # Process the single file
        service = ImageUploadService()
        result = service.process_uploaded_image(
            uploaded_files[0],
            request.user,
            request=request,
        )

        if result.status == UploadStatus.SUCCESS:
            entry.reference_image = result.trip_image
            entry.save(update_fields=['reference_image'])

            # Return success - JS onComplete callback handles page refresh
            return JsonResponse({'files': [result.to_dict()]})

        return JsonResponse({
            'error': result.error_message or 'Upload failed'
        }, status=400)


class JournalEditorMultiImageUploadView(EntityImageUploadView):
    """
    Multi-image upload mode for the Journal Editor sidebar.

    Allows uploading multiple images at once. Images are added to the
    trip's image collection and become available in the journal editor's
    multi-image picker panel.
    """

    def get_template_name(self) -> str:
        return 'journal/modals/journal_editor_multi_image_upload.html'

    def get_max_files(self) -> int:
        return 50

    def check_permission(self, request, *args, **kwargs) -> None:
        entry_uuid = kwargs.get('entry_uuid')
        entry = get_object_or_404(JournalEntry, uuid=entry_uuid)
        request_member = get_object_or_404(
            TripMember,
            trip=entry.journal.trip,
            user=request.user,
        )
        self.assert_is_editor(request_member)

    def get_upload_url(self, request, *args, **kwargs) -> str:
        entry_uuid = kwargs.get('entry_uuid')
        return reverse('journal_editor_multi_image_upload', kwargs={'entry_uuid': entry_uuid})
