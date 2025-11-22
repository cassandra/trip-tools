from uuid import UUID

from django.http import Http404, HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.views.generic import View

from tt.apps.journal.models import Journal
from tt.apps.journal.enums import JournalVisibility

from .enums import ContentType
from .exceptions import PasswordRequiredException
from .forms import TravelogPasswordForm
from .mixins import TravelogViewMixin


class TravelogUserListView(View):
    """
    Index page of all travelogs for a given user.  Filter by request user's permissions.
    """
    def get(self, request: HttpRequest, user_uuid: UUID, *args, **kwargs) -> HttpResponse:
        # TODO: Implement view logic
        # - Get user's journal by user UUID (404 if not found)
        # - Filter out private/unpublished journals
        # - Render page of trips

        return HttpResponse(f"TODO: Implement TravelogTableOfContentsView for journal {user_uuid}")


class TravelogTableOfContentsView(TravelogViewMixin, View):
    """
    Public table of contents view for a journal.
    No authentication required - access controlled by journal visibility and password.

    TODO: Implement public journal TOC functionality.
    - Lookup journal by UUID
    - Check visibility (PRIVATE/PROTECTED/PUBLIC)
    - Handle password protection (session-based password check)
    - Display journal metadata and list of entries with dates
    - Navigation to individual days
    - Link to image gallery
    """

    def get( self,
             request       : HttpRequest,
             content_type  : ContentType,
             journal_uuid  : UUID,
             *args, **kwargs             ) -> HttpResponse:
        try:
            journal = self.get_journal(request, journal_uuid, content_type)
        except PasswordRequiredException:
            return self.password_redirect_response( request = request, journal_uuid = journal_uuid )

        # TODO: Resolve content based on content_type (DRAFT, VIEW, or VERSION)
        # TODO: Fetch entries
        # TODO: Render TOC template

        return HttpResponse(f"TODO: Implement TravelogTableOfContentsView for {content_type.name} journal {journal_uuid}")


class TravelogDayView(TravelogViewMixin, View):
    """
    Public view for a single day's journal entry.
    No authentication required - access controlled by journal visibility and password.

    TODO: Implement public journal day view functionality.
    - Lookup journal by UUID
    - Check visibility/password (from session)
    - Fetch journal entry for specified date
    - Display entry text (rendered markdown), images, navigation
    - Previous/next day navigation
    - Back to TOC link
    """

    def get( self,
             request       : HttpRequest,
             content_type  : ContentType,
             journal_uuid  : UUID,
             date          : str,
             *args, **kwargs             ) -> HttpResponse:
        try:
            journal = self.get_journal(request, journal_uuid, content_type)
        except PasswordRequiredException:
            return self.password_redirect_response( request = request, journal_uuid = journal_uuid )

        # TODO: Resolve content based on content_type (DRAFT, VIEW, or VERSION)
        # TODO: Get entry for date (404 if not found)
        # TODO: Render markdown
        # TODO: Get previous/next entries for navigation
        # TODO: Render day template

        return HttpResponse(f"TODO: Implement TravelogDayView for {content_type.name} journal {journal_uuid}, date {date}")


class TravelogImageGalleryView(TravelogViewMixin, View):
    """
    Public paginated image gallery for a journal.
    No authentication required - access controlled by journal visibility and password.

    TODO: Implement public image gallery functionality.
    - Lookup journal by UUID
    - Check visibility/password
    - Fetch images associated with journal entries
    - Paginate images (e.g., 20 per page)
    - Display thumbnail grid
    - Link to image browse view
    - Pagination controls
    """

    def get( self,
             request       : HttpRequest,
             content_type  : ContentType,
             journal_uuid  : UUID,
             page_num      : int         = 1,
             *args, **kwargs                 ) -> HttpResponse:
        try:
            journal = self.get_journal(request, journal_uuid, content_type)
        except PasswordRequiredException:
            return self.password_redirect_response( request = request, journal_uuid = journal_uuid )

        # TODO: Resolve content based on content_type (DRAFT, VIEW, or VERSION)
        # TODO: Fetch images for journal entries
        # TODO: Paginate
        # TODO: Render gallery template

        return HttpResponse(f"TODO: Implement TravelogImageGalleryView for {content_type.name} journal {journal_uuid}, page {page_num}")


class TravelogImageBrowseView(TravelogViewMixin, View):
    """
    Public image browser view (single image with navigation).
    No authentication required - access controlled by journal visibility and password.

    TODO: Implement public image browse functionality.
    - Lookup journal by UUID
    - Check visibility/password
    - Display single image (web size)
    - Show image metadata (caption, date, location)
    - Previous/next image navigation
    - Back to gallery link
    - Link to journal entry for this image's date
    """

    def get( self,
             request       : HttpRequest,
             content_type  : ContentType,
             journal_uuid  : UUID,
             image_uuid    : UUID,
             *args, **kwargs             ) -> HttpResponse:
        try:
            journal = self.get_journal(request, journal_uuid, content_type)
        except PasswordRequiredException:
            return self.password_redirect_response( request = request, journal_uuid = journal_uuid )

        # TODO: Resolve content based on content_type (DRAFT, VIEW, or VERSION)
        # TODO: Get image by UUID
        # TODO: Get previous/next images
        # TODO: Render browse template

        return HttpResponse(f"TODO: Implement TravelogImageBrowseView for {content_type.name} journal {journal_uuid}, image {image_uuid}")


class TravelogPasswordEntryView(TravelogViewMixin, View):
    """
    Password entry view for password-protected travelogs.

    Allows anonymous users to enter a password to access PROTECTED journals.
    Stores verification in session with 24-hour timeout.
    """

    def get( self, request: HttpRequest, journal_uuid: UUID, *args, **kwargs ) -> HttpResponse:
        journal = get_object_or_404(Journal, uuid=journal_uuid)
        next_url = request.GET.get('next', '')

        # Handle PUBLIC journals - redirect without password
        if journal.visibility == JournalVisibility.PUBLIC:
            redirect_url = self.get_password_redirect_url( request, journal, next_url )
            return HttpResponseRedirect( redirect_url )

        # Validate journal is PROTECTED (raises Http404 for PRIVATE/invalid)
        self.assert_journal_is_protected(journal)

        # PROTECTED journal - show password form
        form = TravelogPasswordForm()

        context = {
            'journal': journal,
            'form': form,
            'next_url': next_url,
        }
        return render(request, 'travelog/password_entry.html', context)

    def post( self, request: HttpRequest, journal_uuid: UUID, *args, **kwargs ) -> HttpResponse:
        journal = get_object_or_404(Journal, uuid=journal_uuid)
        next_url = request.POST.get('next', request.GET.get('next', ''))

        # Handle PUBLIC journals - redirect without password
        if journal.visibility == JournalVisibility.PUBLIC:
            redirect_url = self.get_password_redirect_url( request, journal, next_url )
            return HttpResponseRedirect( redirect_url )

        # Validate journal is PROTECTED (raises Http404 for PRIVATE/invalid)
        self.assert_journal_is_protected(journal)

        # PROTECTED journal - process password form
        form = TravelogPasswordForm(request.POST)

        if form.is_valid():
            password = form.cleaned_data['password']

            # Validate password against journal
            if journal.check_password(password):
                # Store verification in session
                self.set_journal_password_verified(request, journal.uuid)

                # Redirect to next URL or default to journal TOC
                redirect_url = self.get_password_redirect_url( request, journal, next_url )
                return HttpResponseRedirect(redirect_url)
            else:
                # Password incorrect
                form.add_error('password', 'Incorrect password. Please try again.')

        context = {
            'journal': journal,
            'form': form,
            'next_url': next_url,
        }
        return render(request, 'travelog/password_entry.html', context)
