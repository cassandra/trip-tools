from django.http import HttpResponse
from django.views.generic import View


class JournalTableOfContentsView(View):
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

    def get(self, request, journal_uuid: str, *args, **kwargs) -> HttpResponse:
        # TODO: Implement view logic
        # - Get journal by UUID (404 if not found)
        # - Check visibility/password
        # - Fetch entries
        # - Render TOC template

        return HttpResponse(f"TODO: Implement JournalTableOfContentsView for journal {journal_uuid}")

    def post(self, request, journal_uuid: str, *args, **kwargs) -> HttpResponse:
        # TODO: Handle password submission for PROTECTED journals
        # - Validate password
        # - Store in session
        # - Redirect to TOC

        return HttpResponse("TODO: Implement password submission")


class JournalDayView(View):
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

    def get(self, request, journal_uuid: str, date: str, *args, **kwargs) -> HttpResponse:
        # TODO: Implement view logic
        # - Get journal by UUID
        # - Check visibility/password
        # - Get entry for date (404 if not found)
        # - Render markdown
        # - Get previous/next entries for navigation
        # - Render day template

        return HttpResponse(f"TODO: Implement JournalDayView for journal {journal_uuid}, date {date}")


class JournalImageGalleryView(View):
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

    def get(self, request, journal_uuid: str, page_num: int, *args, **kwargs) -> HttpResponse:
        # TODO: Implement view logic
        # - Get journal by UUID
        # - Check visibility/password
        # - Fetch images for journal entries
        # - Paginate
        # - Render gallery template

        return HttpResponse(f"TODO: Implement JournalImageGalleryView for journal {journal_uuid}, page {page_num}")


class JournalImageBrowseView(View):
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

    def get(self, request, journal_uuid: str, image_uuid: str, *args, **kwargs) -> HttpResponse:
        # TODO: Implement view logic
        # - Get journal by UUID
        # - Check visibility/password
        # - Get image by UUID
        # - Get previous/next images
        # - Render browse template

        return HttpResponse(f"TODO: Implement JournalImageBrowseView for journal {journal_uuid}, image {image_uuid}")
