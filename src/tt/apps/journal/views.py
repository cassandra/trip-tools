from datetime import date as date_class, timedelta
import logging
import pytz
from uuid import UUID

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import BadRequest
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
from .forms import JournalForm, JournalEntryForm, JournalVisibilityForm
from .mixins import JournalViewMixin
from .models import Journal, JournalEntry
from .transient_models import PublishingStatusHelper
from .services import (
    JournalImagePickerService,
    JournalRestoreService,
)

from tt.apps.images.models import TripImage
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

            return self.refresh_response(request)

        context = {
            'form': form,
            'trip': trip,
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

        # Get publishing status
        publishing_status = PublishingStatusHelper.get_publishing_status(journal)

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


class JournalPublishModalView( LoginRequiredMixin, TripViewMixin, ModalView ):

    def get_template_name(self) -> str:
        return 'journal/modals/journal_publish.html'

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

        # Get publishing status for display
        publishing_status = PublishingStatusHelper.get_publishing_status(journal)

        # Create visibility form for optional visibility changes during publish
        visibility_form = JournalVisibilityForm(journal=journal)

        context = {
            'journal': journal,
            'trip': journal.trip,
            'publishing_status': publishing_status,
            'visibility_form': visibility_form,
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

        # Get publishing status to check for edge cases
        publishing_status = PublishingStatusHelper.get_publishing_status(journal)

        # Validate visibility form (if visibility changes are included)
        visibility_form = JournalVisibilityForm(request.POST, journal=journal)

        if not visibility_form.is_valid():
            context = {
                'journal': journal,
                'trip': journal.trip,
                'publishing_status': publishing_status,
                'visibility_form': visibility_form,
            }
            return self.modal_response(request, context=context, status=400)

        try:
            with transaction.atomic():
                # Publish the journal
                travelog = PublishingService.publish_journal(
                    journal=journal,
                    user=request.user
                )

                # Apply visibility changes if form was submitted
                visibility_name = visibility_form.cleaned_data['visibility']
                visibility = JournalVisibility[visibility_name]

                journal.visibility = visibility

                # Handle password setting based on form state
                if visibility_form.should_update_password():
                    password = visibility_form.cleaned_data.get('password')
                    journal.set_password(password)

                journal.modified_by = request.user
                journal.save()

            logger.info(
                f"Journal {journal.uuid} published as Travelog v{travelog.version_number} "
                f"by user {request.user}"
            )

            return self.refresh_response(request)

        except ValueError as e:
            # Handle validation errors (e.g., no entries to publish)
            logger.warning(f"Failed to publish journal {journal.uuid}: {e}")

            # Re-display modal with error message
            visibility_form.add_error(None, str(e))
            context = {
                'journal': journal,
                'trip': journal.trip,
                'publishing_status': publishing_status,
                'visibility_form': visibility_form,
            }
            return self.modal_response(request, context=context, status=400)

        except Exception as e:
            # Handle unexpected errors
            logger.error(f"Error publishing journal {journal.uuid}: {e}", exc_info=True)

            visibility_form.add_error(None, "An unexpected error occurred while publishing.")
            context = {
                'journal': journal,
                'trip': journal.trip,
                'publishing_status': publishing_status,
                'visibility_form': visibility_form,
            }
            return self.modal_response(request, context=context, status=500)


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


class JournalReferenceImagePickerView(LoginRequiredMixin, TripViewMixin, ModalView):
    """Modal for selecting and setting a reference image for the Journal."""

    def get_template_name(self) -> str:
        return 'journal/modals/journal_reference_image_picker.html'

    def get(self, request, journal_uuid: UUID, *args, **kwargs) -> HttpResponse:
        journal = get_object_or_404(
            Journal,
            uuid=journal_uuid,
        )
        request_member = get_object_or_404(
            TripMember,
            trip=journal.trip,
            user=request.user,
        )
        self.assert_is_editor(request_member)
        trip = request_member.trip

        selected_date, selected_timezone = self._get_accessible_images_date_and_timezone(
            journal = journal,
            request_date_str = request.GET.get('date'),
        )
        # Get accessible images for the selected date/timezone
        accessible_images = JournalImagePickerService.get_accessible_images_for_image_picker(
            trip = trip,
            user = request.user,
            date = selected_date,
            timezone = selected_timezone,
            scope = ImagePickerScope.DEFAULT,
        )

        context = {
            'journal': journal,
            'accessible_images': accessible_images,
            'trip': trip,
            'selected_date': selected_date,
        }
        return self.modal_response(request, context)

    def post(self, request, journal_uuid: UUID, *args, **kwargs) -> HttpResponse:
        journal = get_object_or_404(
            Journal,
            uuid=journal_uuid,
        )
        request_member = get_object_or_404(
            TripMember,
            trip=journal.trip,
            user=request.user,
        )
        self.assert_is_editor(request_member)

        image_uuid_str = request.POST.get('image_uuid')
        if not image_uuid_str:
            return http_response({'error': 'Image UUID required'}, status=400)

        try:
            image_uuid = UUID(image_uuid_str)
        except ValueError:
            return http_response({'error': 'Invalid UUID format'}, status=400)

        # Get and validate image (verify it was uploaded by a trip member)
        trip_image = get_object_or_404(TripImage, uuid=image_uuid)

        # Security check: ensure image was uploaded by a current trip member
        member_user_ids = TripMember.objects.filter(
            trip=journal.trip
        ).values_list('user_id', flat=True)

        if trip_image.uploaded_by_id not in member_user_ids:
            return http_response({'error': 'Image not accessible'}, status=403)

        # Update journal reference image
        journal.reference_image = trip_image
        journal.save(update_fields=['reference_image'])

        return self.refresh_response( request )

    def _get_accessible_images_date_and_timezone( self, journal : Journal, request_date_str: str ):
        if request_date_str:
            try:
                selected_date = date_class.fromisoformat( request_date_str )
                return ( selected_date, journal.timezone )
            except ( TypeError, ValueError ):
                raise BadRequest('Invalid date format')

        if journal.reference_image and journal.reference_image.datetime_utc:
            ref_img = journal.reference_image
            # Use image's timezone if available, otherwise fall back to journal timezone
            selected_timezone = ref_img.timezone if ref_img.timezone else journal.timezone
            # Convert UTC datetime to the selected timezone to get the correct date
            tz = pytz.timezone(selected_timezone)
            selected_date = ref_img.datetime_utc.astimezone(tz).date()
            return ( selected_date, selected_timezone )

        for journal_entry in journal.entries.order_by('date'):
            if journal_entry.reference_image:
                selected_date = journal_entry.date if journal_entry else date_class.today()
                selected_timezone = journal_entry.timezone
                return ( selected_date, selected_timezone )
            continue
        
        selected_date = date_class.today()
        selected_timezone = journal.timezone
        return ( selected_date, selected_timezone )
