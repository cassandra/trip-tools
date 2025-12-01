from typing import List
from django.contrib.auth import get_user_model

from tt.apps.members.models import TripMember

from .enums import TripStatus
from .models import Trip
from .schemas import TripCategorizedDisplayData

User = get_user_model()


class TripDisplayService:

    @staticmethod
    def get_categorized_trips_for_user( user: User ) -> TripCategorizedDisplayData:
        """
        Get trips categorized and ordered according to display requirements.

        Returns trips in three categories:
        - Current: Editable trips with UPCOMING or CURRENT status
        - Shared: Non-editable trips (viewer permission) with any status
        - Past: Editable trips with PAST status

        Each category uses ordering based on derived dates.
        """
        # Get all user memberships with optimized queries
        memberships = (
            TripMember.objects
            .filter( user = user )
            .select_related('trip')
            .prefetch_related(
                'trip__itineraries__items',
                'trip__journals__entries',
            )
        )

        current_trips = []
        past_trips = []
        shared_trip_memberships = []

        for membership in memberships:
            trip = membership.trip
            is_editable = membership.permission_level.is_editor

            # Categorize based on permission and status
            if trip.trip_status in [ TripStatus.UPCOMING, TripStatus.CURRENT ]:
                if is_editable:
                    current_trips.append( trip )
                else:
                    shared_trip_memberships.append( membership )
            elif trip.trip_status == TripStatus.PAST:
                if is_editable:
                    past_trips.append( trip )
                else:
                    shared_trip_memberships.append( membership )

        current_trips = TripDisplayService._order_editable_trips( trips = current_trips )
        past_trips = TripDisplayService._order_editable_trips( trips = past_trips )
        shared_trips = TripDisplayService._order_shared_trips(
            shared_trip_memberships = shared_trip_memberships,
        )
        return TripCategorizedDisplayData(
            current_trips = current_trips,
            shared_trips = shared_trips,
            past_trips = past_trips,
        )

    @staticmethod
    def _order_editable_trips(trips: List[Trip]) -> List[Trip]:
        """
        Order editable trips by derived date in reverse chronological order.

        Derived date priority:
        1. Earliest ItineraryItem.start_datetime
        2. Earliest JournalEntry.date
        3. Trip.created_datetime
        """
        def get_derived_date(trip: Trip):

            earliest_itinerary_date = None
            for itinerary in trip.itineraries.all():
                for item in itinerary.items.all():
                    if ( earliest_itinerary_date is None
                         or ( item.start_datetime.date() < earliest_itinerary_date )):
                        earliest_itinerary_date = item.start_datetime.date()
                    continue
                continue
            
            if earliest_itinerary_date:
                return earliest_itinerary_date

            earliest_journal_date = None
            for journal in trip.journals.all():
                for entry in journal.entries.all():
                    entry_date = entry.date
                    if ( earliest_journal_date is None
                         or ( entry_date < earliest_journal_date )):
                        earliest_journal_date = entry_date
                    continue
                continue

            if earliest_journal_date:
                return earliest_journal_date

            return trip.created_datetime.date()

        return sorted( trips, key = get_derived_date, reverse = True )

    @staticmethod
    def _order_shared_trips( shared_trip_memberships: List[TripMember] ) -> List[Trip]:

        sorted_trip_membership = sorted(
            shared_trip_memberships,
            key = lambda item: item.added_datetime,
            reverse = True,
        )
        return [ x.trip for x in sorted_trip_membership ]
