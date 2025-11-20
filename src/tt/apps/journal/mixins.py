from django.shortcuts import render

from tt.apps.members.models import TripMember
from tt.apps.trips.context import TripPageContext
from tt.apps.trips.enums import TripPage

from .context import JournalPageContext
from .models import Journal


class JournalViewMixin:
    
    def journal_permission_denied_response( self,
                                            request,
                                            request_member  : TripMember,
                                            journal         : Journal ):
        trip_page_context = TripPageContext(
            active_page = TripPage.JOURNAL,
            request_member = request_member,
        )
        journal_entries = journal.entries.all()
        journal_page_context = JournalPageContext(
            journal = journal,
            journal_entries = journal_entries,
        )
        context = {
            'trip_page': trip_page_context,
            'journal_page': journal_page_context,
            'journal': journal,
        }
        return render(request, 'journal/pages/journal_permission_denied.html', context)
