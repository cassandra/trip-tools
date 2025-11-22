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


class TravelogViewMixin:

    def get_journal( self,
                     request       : HttpRequest,
                     journal_uuid  : UUID,
                     content_type  : ContentType ) -> Journal:
        """
        Get journal and assert access based on content type and visibility.

        Raises Http404 if journal not found or PermissionDenied if access denied.
        """
        journal = get_object_or_404( Journal, uuid = journal_uuid )
        self.assert_has_journal_access(request, journal, content_type)
        return journal

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
            if self.check_journal_password_verified( request, journal.uuid ):
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
                                         journal_uuid   : UUID,
                                         timeout_hours  : int = 24 ) -> bool:
        """
        Returns True if verified within timeout window, False otherwise.
        """
        session_key = self._get_session_key( journal_uuid )
        verification_timestamp = request.session.get( session_key )

        if not verification_timestamp:
            return False

        try:
            verified_at = datetime.fromisoformat( verification_timestamp )
            timeout = timedelta( hours = timeout_hours )
            return datetime.now() - verified_at < timeout
        except ( ValueError, TypeError ):
            # Invalid timestamp format, treat as not verified
            return False

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
        
    def set_journal_password_verified( self, request: HttpRequest, journal_uuid: UUID ) -> None:
        session_key = self._get_session_key( journal_uuid )
        request.session[session_key] = datetime.now().isoformat()
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


