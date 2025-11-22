from datetime import datetime, timedelta
from uuid import UUID

from django.core.exceptions import BadRequest, PermissionDenied
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from tt.apps.journal.models import Journal
from tt.apps.journal.enums import JournalVisibility
from tt.apps.members.models import TripMember

from .enums import ContentType
from .exceptions import PasswordRequiredException
from .transient_models import TravelogPageContext


class TravelogViewMixin:

    def get_travelog_page_context( self,
                                   request       : HttpRequest,
                                   journal_uuid  : UUID ) -> TravelogPageContext:
        """
        Parse request to determine content type and get authorized journal.

        Parses the 'version' query parameter to determine content type:
        - version=draft -> DRAFT content
        - version=view or version=current or no param -> VIEW content (current published)
        - version={number} -> VERSION content with specific version number

        Returns TravelogPageContext with journal, content_type, and version_number.
        Raises PasswordRequiredException, Http404, or PermissionDenied if access denied.
        """
        journal = get_object_or_404( Journal, uuid = journal_uuid )

        version_param = request.GET.get('version', '')

        if version_param == 'draft':
            content_type = ContentType.DRAFT
            version_number = None
        elif version_param == 'view' or version_param == 'current' or not version_param:
            # Default to current published version
            content_type = ContentType.VIEW
            version_number = None
        else:
            try:
                version_number = int(version_param)
                content_type = ContentType.VERSION
            except ValueError:
                # Invalid version param - default to VIEW
                content_type = ContentType.VIEW
                version_number = None

        self.assert_has_journal_access(
            request = request,
            journal = journal,
            content_type = content_type,
        )
        return TravelogPageContext(
            journal = journal,
            content_type = content_type,
            version_number = version_number
        )

    def assert_has_journal_access( self,
                                   request       : HttpRequest,
                                   journal       : Journal,
                                   content_type  : ContentType) -> None:
        """
        Assert that the request has access to the journal based on content type and visibility.

        For DRAFT content type: Always requires trip membership (private working copy).
        For VIEW/VERSION: Respects journal visibility settings.

        Raises Http404 or PermissionDenied if access is denied.
        """

        # Trip members can access all travelog variations (content types)
        # and also do not need a password for PROTECTED ones.
        if request.user.is_authenticated:
            try:
                TripMember.objects.get( trip = journal.trip, user = request.user )
                return
            except TripMember.DoesNotExist:
                pass
 
        if content_type == ContentType.DRAFT:
            # Drafts not visible unless logged in and a trip member.
            raise Http404()
        
        else:
            # VIEW and VERSION respect journal visibility settings
            self._check_journal_access( request, journal )

    def _check_journal_access( self,
                               request  : HttpRequest,
                               journal  : Journal ) -> None:
        """
        Raises PermissionDenied or Http404 if access is denied.
        """
        if journal.visibility == JournalVisibility.PUBLIC:
            # Anyone can access public journals
            return

        elif journal.visibility == JournalVisibility.PROTECTED:
            if self.check_journal_password_verified( request, journal ):
                return
            # Raise exception to trigger redirect to password entry
            raise PasswordRequiredException( journal.uuid )

        elif journal.visibility == JournalVisibility.PRIVATE:
            # Must be authenticated and a trip member
            if not request.user.is_authenticated:
                raise Http404()  # Don't reveal existence of private journals

            try:
                TripMember.objects.get( trip = journal.trip, user = request.user )
            except TripMember.DoesNotExist:
                raise Http404()  # Don't reveal existence of private journals

        else:
            # This should never happen - all enum values are handled above
            raise PermissionDenied('Invalid journal visibility setting')
        
    def check_journal_password_verified( self,
                                         request        : HttpRequest,
                                         journal        : Journal,
                                         timeout_hours  : int = 720 ) -> bool:
        """
        Returns True if verified within timeout window and password version matches.

        Session data format: {'timestamp': '2025-11-22T...', 'version': 3}
        """
        session_key = self._get_session_key( journal.uuid )
        session_data = request.session.get( session_key )

        if not session_data:
            return False

        if (( not isinstance(session_data, dict))
            or ( 'timestamp' not in session_data )
            or ( 'version' not in session_data )):
            return False

        try:
            verified_at = datetime.fromisoformat( session_data['timestamp'] )
            timeout = timedelta( hours = timeout_hours )
            if datetime.now() - verified_at >= timeout:
                return False

            return session_data['version'] == journal.password_version

        except ( ValueError, TypeError, KeyError ):
            return False
        
    def set_journal_password_verified( self, request: HttpRequest, journal: 'Journal' ) -> None:
        """
        Store password verification in session with timestamp and password version.

        Args:
            request: HTTP request with session
            journal: Journal object (not UUID) - needed to get current password_version
        """
        session_key = self._get_session_key( journal.uuid )
        request.session[session_key] = {
            'timestamp': datetime.now().isoformat(),
            'version': journal.password_version,
        }
        return
    
    def clear_journal_password_verified( self, request: HttpRequest, journal_uuid: UUID ) -> None:
        session_key = self._get_session_key( journal_uuid )
        request.session.pop(session_key, None)
        return

    def _get_session_key( self, journal_uuid: UUID ) -> str:
        return f'journal_password_verified_{journal_uuid}'

    def assert_journal_is_protected( self, journal: Journal ) -> None:
        """
        Assert that journal is PROTECTED visibility.

        Raises Http404 for PRIVATE journals (hide existence).
        Redirects to target URL for PUBLIC journals (no password needed).
        Raises Http404 for unknown visibility settings.
        """
        if journal.visibility == JournalVisibility.PROTECTED:
            return
        
        if journal.visibility == JournalVisibility.PUBLIC:
            # This should not happen in normal flow, but handle gracefully
            # The caller should redirect, but we raise to signal improper use
            raise BadRequest('PUBLIC journals do not require password')

        elif journal.visibility == JournalVisibility.PRIVATE:
            # PRIVATE journals require trip membership, not password
            raise Http404()

        # Unknown visibility setting
        raise Http404()

    def password_redirect_response( self,
                                    request       : HttpRequest,
                                    journal_uuid  : UUID ) -> HttpResponse:
        """
        Redirect to password entry page with current URL as 'next' parameter.

        The current URL is already validated as it comes from request.get_full_path()
        which returns the path portion of the URL (not an arbitrary user input).
        """
        password_url = reverse('travelog_password_entry', kwargs = { 'journal_uuid': journal_uuid })
        next_url = request.get_full_path()
        # URL-encode the next parameter to handle special characters
        from urllib.parse import urlencode
        query_string = urlencode({'next': next_url})
        return HttpResponseRedirect( f'{password_url}?{query_string}' )

    def get_password_redirect_url( self, request: HttpRequest, journal: Journal, next_url: str ) -> str:
        """
        Get appropriate redirect URL after password validation.

        Returns validated next_url if provided and safe, otherwise default TOC URL.
        """
        fallback_url = reverse('travelog_toc', kwargs={
            'content_type': 'view',
            'journal_uuid': journal.uuid
        })

        return self.get_safe_redirect_url(request, next_url, fallback_url)

    def get_safe_redirect_url( self, request: HttpRequest, next_url: str, fallback_url: str ) -> str:
        """
        Validate and sanitize redirect URL to prevent open redirect vulnerabilities.

        Args:
            request: The HTTP request object
            next_url: The user-provided next URL
            fallback_url: Fallback URL if next_url is invalid or empty

        Returns:
            Safe redirect URL (either validated next_url or fallback_url)
        """
        if not next_url:
            return fallback_url

        # Validate that URL is safe (relative URL or same-origin)
        # url_has_allowed_host_and_scheme() returns True for:
        # - Relative URLs (/path/to/page)
        # - Same-host URLs (http://example.com/path when request is to example.com)
        # Returns False for external URLs (http://evil.com)
        is_safe = url_has_allowed_host_and_scheme(
            url = next_url,
            allowed_hosts = { request.get_host() },
            require_https = request.is_secure()
        )
        if is_safe:
            return next_url
        else:
            # Unsafe URL - use fallback
            return fallback_url


