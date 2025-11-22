from uuid import UUID

from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404

from tt.apps.journal.models import Journal
from tt.apps.journal.enums import JournalVisibility
from tt.apps.members.models import TripMember

from .enums import ContentType


class TravelogViewMixin:

    def get_journal( self, request, journal_uuid: UUID, content_type: ContentType ) -> Journal:
        """
        Get journal and assert access based on content type and visibility.

        Raises Http404 if journal not found or PermissionDenied if access denied.
        """
        journal = get_object_or_404( Journal, uuid = journal_uuid )
        self.assert_has_journal_access(request, journal, content_type)
        return journal

    def assert_has_journal_access(self, request, journal: Journal, content_type: ContentType) -> None:
        """
        Assert that the request has access to the journal based on content type and visibility.

        For DRAFT content type: Always requires trip membership (private working copy).
        For VIEW/VERSION: Respects journal visibility settings.

        Raises Http404 or PermissionDenied if access is denied.
        """
        if content_type == ContentType.DRAFT:
            # DRAFT content type is only accessible to trip members (always PRIVATE)
            if not request.user.is_authenticated:
                raise Http404()
            try:
                TripMember.objects.get(trip=journal.trip, user=request.user)
            except TripMember.DoesNotExist:
                raise Http404()
        else:
            # VIEW and VERSION respect journal visibility settings
            self.check_journal_access(request, journal)

    def check_journal_access( self, request, journal: Journal ) -> None:
        """
        Raises PermissionDenied or Http404 if access is denied.
        """
        if journal.visibility == JournalVisibility.PUBLIC:
            # Anyone can access public journals
            return

        elif journal.visibility == JournalVisibility.PROTECTED:
            # Check if password has been verified in session
            session_key = f'journal_password_verified_{journal.uuid}'
            if request.session.get(session_key):
                return
            # TODO: Redirect to password entry form instead of 403
            raise PermissionDenied('Password required to access this journal')

        elif journal.visibility == JournalVisibility.PRIVATE:
            # Must be authenticated and a trip member
            if not request.user.is_authenticated:
                raise Http404()  # Don't reveal existence of private journals

            try:
                TripMember.objects.get(trip=journal.trip, user=request.user)
            except TripMember.DoesNotExist:
                raise Http404()  # Don't reveal existence of private journals

        else:
            # This should never happen - all enum values are handled above
            raise PermissionDenied('Invalid journal visibility setting')
