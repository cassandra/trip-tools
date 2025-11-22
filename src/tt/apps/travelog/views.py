from uuid import UUID

from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.views.generic import View

from tt.apps.journal.models import Journal
from tt.apps.journal.enums import JournalVisibility

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

    Content type determined by ?version= query parameter:
    - No parameter or ?version=view: Current published version
    - ?version=draft: Draft version (requires trip membership)
    - ?version=N: Historical version N

    TODO: Implement public journal TOC functionality.
    - Display journal metadata and list of entries with dates
    - Navigation to individual days
    - Link to image gallery
    """

    def get( self,
             request       : HttpRequest,
             journal_uuid  : UUID,
             *args, **kwargs             ) -> HttpResponse:
        try:
            travelog_context = self.get_travelog_page_context(request, journal_uuid)
        except PasswordRequiredException:
            return self.password_redirect_response( request = request, journal_uuid = journal_uuid )

        # TODO: Resolve content based on travelog_context.content_type (DRAFT, VIEW, or VERSION)
        # TODO: If VERSION, use travelog_context.version_number to fetch specific version
        # TODO: Fetch entries
        # TODO: Render TOC template

        return HttpResponse(
            f"TODO: Implement TravelogTableOfContentsView for {travelog_context.content_type.name} "
            f"journal {journal_uuid}"
            f"{f' version {travelog_context.version_number}' if travelog_context.version_number else ''}"
        )


class TravelogDayView(TravelogViewMixin, View):
    """
    Public view for a single day's journal entry.
    No authentication required - access controlled by journal visibility and password.

    Content type determined by ?version= query parameter.

    TODO: Implement public journal day view functionality.
    - Fetch journal entry for specified date
    - Display entry text (rendered markdown), images, navigation
    - Previous/next day navigation
    - Back to TOC link
    """

    def get( self,
             request       : HttpRequest,
             journal_uuid  : UUID,
             date          : str,
             *args, **kwargs             ) -> HttpResponse:
        try:
            travelog_context = self.get_travelog_page_context(request, journal_uuid)
        except PasswordRequiredException:
            return self.password_redirect_response( request = request, journal_uuid = journal_uuid )

        # TODO: Resolve content based on travelog_context.content_type (DRAFT, VIEW, or VERSION)
        # TODO: Get entry for date (404 if not found)
        # TODO: Render markdown
        # TODO: Get previous/next entries for navigation
        # TODO: Render day template

        return HttpResponse(
            f"TODO: Implement TravelogDayView for {travelog_context.content_type.name} "
            f"journal {journal_uuid}, date {date}"
            f"{f' version {travelog_context.version_number}' if travelog_context.version_number else ''}"
        )


class TravelogImageGalleryView(TravelogViewMixin, View):
    """
    Public paginated image gallery for a journal.
    No authentication required - access controlled by journal visibility and password.

    Content type determined by ?version= query parameter.

    TODO: Implement public image gallery functionality.
    - Fetch images associated with journal entries
    - Paginate images (e.g., 20 per page)
    - Display thumbnail grid
    - Link to image browse view
    - Pagination controls
    """

    def get( self,
             request       : HttpRequest,
             journal_uuid  : UUID,
             page_num      : int         = 1,
             *args, **kwargs                 ) -> HttpResponse:
        try:
            travelog_context = self.get_travelog_page_context(request, journal_uuid)
        except PasswordRequiredException:
            return self.password_redirect_response( request = request, journal_uuid = journal_uuid )

        # TODO: Resolve content based on travelog_context.content_type (DRAFT, VIEW, or VERSION)
        # TODO: Fetch images for journal entries
        # TODO: Paginate
        # TODO: Render gallery template

        return HttpResponse(
            f"TODO: Implement TravelogImageGalleryView for {travelog_context.content_type.name} "
            f"journal {journal_uuid}, page {page_num}"
            f"{f' version {travelog_context.version_number}' if travelog_context.version_number else ''}"
        )


class TravelogImageBrowseView(TravelogViewMixin, View):
    """
    Public image browser view (single image with navigation).
    No authentication required - access controlled by journal visibility and password.

    Content type determined by ?version= query parameter.

    TODO: Implement public image browse functionality.
    - Display single image (web size)
    - Show image metadata (caption, date, location)
    - Previous/next image navigation
    - Back to gallery link
    - Link to journal entry for this image's date
    """

    def get( self,
             request       : HttpRequest,
             journal_uuid  : UUID,
             image_uuid    : UUID,
             *args, **kwargs             ) -> HttpResponse:
        try:
            travelog_context = self.get_travelog_page_context(request, journal_uuid)
        except PasswordRequiredException:
            return self.password_redirect_response( request = request, journal_uuid = journal_uuid )

        # TODO: Resolve content based on travelog_context.content_type (DRAFT, VIEW, or VERSION)
        # TODO: If VERSION, use travelog_context.version_number to fetch specific version
        # TODO: Get image by UUID
        # TODO: Get previous/next images
        # TODO: Render browse template

        return HttpResponse(
            f"TODO: Implement TravelogImageBrowseView for {travelog_context.content_type.name} "
            f"journal {journal_uuid}, image {image_uuid}"
            f"{f' version {travelog_context.version_number}' if travelog_context.version_number else ''}"
        )


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
                self.set_journal_password_verified(request, journal)

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
