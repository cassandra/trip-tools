from datetime import date as date_type
from uuid import UUID

from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.views.generic import View

from tt.apps.common.pagination import compute_pagination
from tt.apps.images.models import TripImage
from tt.apps.journal.models import Journal
from tt.apps.journal.enums import JournalVisibility

from .exceptions import PasswordRequiredException
from .forms import TravelogPasswordForm
from .mixins import TravelogViewMixin
from .services import ContentResolutionService, TravelogImageCacheService


class TravelogUserListView(TravelogViewMixin, View):
    """
    Index page of all published travelogs for a given user.

    Shows journals owned by the target user, filtered by visibility and request user's permissions.
    Leverages TravelogViewMixin._check_journal_access() to determine which journals are accessible.

    Only journals with published travelogs (is_current=True) are displayed.
    PROTECTED journals appear in list with lock icon when password not verified.
    """
    def get(self, request: HttpRequest, user_uuid: UUID, *args, **kwargs) -> HttpResponse:
        from django.contrib.auth import get_user_model
        from tt.apps.trips.models import Trip
        from .schemas import TravelogListItemData

        User = get_user_model()

        # Get target user (404 if not found)
        target_user = get_object_or_404( User, uuid = user_uuid )

        # Get trips owned by target user
        trips = Trip.objects.owned_by( target_user )

        # Get journals for these trips that have published travelogs
        journals = Journal.objects.filter(
            trip__in = trips,
            travelogs__is_current = True
        ).distinct().select_related('trip').prefetch_related('entries', 'entries__reference_image')

        # Build list items with access metadata
        travelog_items = []
        for journal in journals:
            requires_password = False

            try:
                # Check access using existing mixin logic
                self._check_journal_access( request, journal )
            except PasswordRequiredException:
                # PROTECTED journal without password verification - show with lock icon
                requires_password = True
            except ( Http404, PermissionDenied ):
                # User doesn't have access - exclude from list
                continue

            # Get date range from entries
            entries = journal.entries.order_by('date')
            earliest_date = entries.first().date.strftime('%Y-%m-%d') if entries.exists() else None
            latest_date = entries.last().date.strftime('%Y-%m-%d') if entries.exists() else None

            display_image = journal.reference_image
            # Use first entry reference image for display if none explicitly set
            if not display_image:
                for entry in entries:
                    if entry.reference_image:
                        display_image = entry.reference_image
                        break

            travelog_items.append( TravelogListItemData(
                journal = journal,
                requires_password = requires_password,
                earliest_entry_date = earliest_date,
                latest_entry_date = latest_date,
                display_image = display_image
            ))

        # Sort by latest entry date (reverse chronological)
        travelog_items.sort(
            key = lambda item: item.latest_entry_date or '',
            reverse = True
        )

        context = {
            'target_user': target_user,
            'travelog_items': travelog_items,
        }

        return render(request, 'travelog/pages/travelog_user_list.html', context)


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
            travelog_page_context = self.get_travelog_page_context(request, journal_uuid)
        except PasswordRequiredException:
            return self.password_redirect_response( request = request, journal_uuid = journal_uuid )

        content = ContentResolutionService.resolve_content(
            travelog_page_context = travelog_page_context,
        )

        # Get entries (works for both Journal and Travelog)
        entries = content.get_entries().order_by('date')

        context = {
            'content': content,
            'entries': entries,
            'travelog_page': travelog_page_context,
            'journal': travelog_page_context.journal,
        }
        return render(request, 'travelog/pages/travelog_toc.html', context)


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
             date          : date_type,
             *args, **kwargs             ) -> HttpResponse:
        try:
            travelog_page_context = self.get_travelog_page_context(request, journal_uuid)
        except PasswordRequiredException:
            return self.password_redirect_response( request = request, journal_uuid = journal_uuid )

        content = ContentResolutionService.resolve_content(
            travelog_page_context = travelog_page_context,
        )

        # Get all entries ordered by date
        entries = content.get_entries().order_by('date')

        entry = entries.filter( date = date ).first()
        if not entry:
            raise Http404()

        prev_entry = entries.filter( date__lt = date ).order_by('-date').first()
        next_entry = entries.filter( date__gt = date ).order_by('date').first()

        context = {
            'content': content,
            'entry': entry,
            'prev_entry': prev_entry,
            'next_entry': next_entry,
            'travelog_page': travelog_page_context,
            'journal': travelog_page_context.journal,
        }

        return render(request, 'travelog/pages/travelog_day.html', context)


class TravelogImageGalleryView(TravelogViewMixin, View):
    """
    Public paginated image gallery for a journal.
    No authentication required - access controlled by journal visibility and password.

    Content type determined by ?version= query parameter.

    Displays paginated grid of images from journal entries with links to browse view.
    Supports cache refresh via ?refresh=true parameter (handled in mixin).
    """

    IMAGES_PER_PAGE = 60

    def get( self,
             request       : HttpRequest,
             journal_uuid  : UUID,
             page_num      : int         = 1,
             *args, **kwargs                 ) -> HttpResponse:
        try:
            travelog_page_context = self.get_travelog_page_context(request, journal_uuid)
        except PasswordRequiredException:
            return self.password_redirect_response( request = request, journal_uuid = journal_uuid )

        content = ContentResolutionService.resolve_content(
            travelog_page_context = travelog_page_context,
        )

        # Get cached images (cache already invalidated in mixin if refresh=true)
        all_images = TravelogImageCacheService.get_images(
            travelog_page_context = travelog_page_context
        )

        # Compute pagination
        pagination = compute_pagination(
            page_number = page_num,
            page_size = self.IMAGES_PER_PAGE,
            item_count = len(all_images)
        )

        # Get image metadata for current page
        page_image_metadata = all_images[pagination.start_offset:pagination.end_offset + 1]

        # Fetch TripImage objects for the page
        image_uuids = [ img.uuid for img in page_image_metadata ]
        trip_images_map = { str(img.uuid): img for img in TripImage.objects.filter(uuid__in=image_uuids) }

        # Pair metadata with TripImage objects
        page_images = [
            {
                'metadata': metadata,
                'trip_image': trip_images_map.get(metadata.uuid)
            }
            for metadata in page_image_metadata
        ]

        context = {
            'content': content,
            'images': page_images,
            'pagination': pagination,
            'travelog_page': travelog_page_context,
            'journal': travelog_page_context.journal,
        }

        return render(request, 'travelog/pages/travelog_image_gallery.html', context)


class TravelogImageBrowseView(TravelogViewMixin, View):
    """
    Public image browser view (single image with navigation).
    No authentication required - access controlled by journal visibility and password.

    Content type determined by ?version= query parameter.

    Displays single image with metadata and prev/next navigation.
    Image navigation order matches chronological appearance in journal entries.
    Supports cache refresh via ?refresh=true parameter (handled in mixin).
    """

    def get( self,
             request       : HttpRequest,
             journal_uuid  : UUID,
             image_uuid    : UUID,
             *args, **kwargs             ) -> HttpResponse:
        try:
            travelog_page_context = self.get_travelog_page_context(request, journal_uuid)
        except PasswordRequiredException:
            return self.password_redirect_response( request = request, journal_uuid = journal_uuid )

        content = ContentResolutionService.resolve_content(
            travelog_page_context = travelog_page_context,
        )

        # Get cached images (cache already invalidated in mixin if refresh=true)
        all_images = TravelogImageCacheService.get_images(
            travelog_page_context = travelog_page_context
        )

        # Find current image and calculate navigation
        current_image = None
        current_index = None
        prev_image = None
        next_image = None

        image_uuid_str = str(image_uuid)

        for idx, img in enumerate(all_images):
            if img.uuid == image_uuid_str:
                current_image = img
                current_index = idx
                if idx > 0:
                    prev_image = all_images[idx - 1]
                if idx < len(all_images) - 1:
                    next_image = all_images[idx + 1]
                break

        # If image not found in list, return 404
        if current_image is None:
            raise Http404(f"Image {image_uuid} not found in this journal")

        # Fetch the TripImage object
        trip_image = TripImage.objects.filter(uuid=current_image.uuid).first()

        context = {
            'content': content,
            'image_metadata': current_image,
            'trip_image': trip_image,
            'image_uuid': image_uuid,
            'current_index': current_index,
            'total_images': len(all_images),
            'prev_image': prev_image,
            'next_image': next_image,
            'travelog_page': travelog_page_context,
            'journal': travelog_page_context.journal,
        }

        return render(request, 'travelog/pages/travelog_image_browse.html', context)


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
        return render(request, 'travelog/pages/password_entry.html', context)

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
        return render(request, 'travelog/pages/password_entry.html', context)
