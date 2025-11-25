from django.shortcuts import render

from tt.apps.members.models import TripMember
from tt.apps.trips.context import TripPageContext
from tt.apps.trips.enums import TripPage

from .context import JournalPageContext
from .models import Journal, JournalEntry
from .schemas import PublishingStatusHelper


class JournalViewMixin:

    def journal_view_only_response( self,
                                    request,
                                    request_member  : TripMember,
                                    journal         : Journal ):
        trip_page_context = TripPageContext(
            active_page = TripPage.JOURNAL,
            request_member = request_member,
        )
        if journal:
            journal_entries = journal.entries.all()
            publishing_status = PublishingStatusHelper.get_publishing_status(journal)
        else:
            journal_entries = JournalEntry.objects.none()
            publishing_status = None
        journal_page_context = JournalPageContext(
            journal = journal,
            journal_entries = journal_entries,
        )
        context = {
            'trip_page': trip_page_context,
            'journal_page': journal_page_context,
            'journal': journal,
            'publishing_status': publishing_status,
        }
        return render(request, 'journal/pages/journal_view_only.html', context)
