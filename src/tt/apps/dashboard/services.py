from typing import List

from django.contrib.auth.models import User as UserType

from tt.apps.members.models import TripMember
from tt.apps.trips.enums import TripStatus
from tt.apps.trips.models import Trip


class DashboardDisplayService:

    MAX_DASHBOARD_TRIPS = 5

    @classmethod
    def get_dashboard_trips_for_user( cls, user: UserType ) -> List[Trip]:
        memberships = (
            TripMember.objects
            .filter( user = user )
            .select_related('trip')
        )

        editable_current_trips = []
        editable_upcoming_trips = []
        shared_trip_memberships = []

        for membership in memberships:
            trip = membership.trip
            is_editable = membership.permission_level.is_editor

            if is_editable:
                if trip.trip_status == TripStatus.CURRENT:
                    editable_current_trips.append( trip )
                elif trip.trip_status == TripStatus.UPCOMING:
                    editable_upcoming_trips.append( trip )
                # PAST editable trips are excluded
            else:
                # All shared (view-only) trips regardless of status
                shared_trip_memberships.append( membership )
            continue

        # Order each category
        editable_current_trips = cls._order_by_creation_date(
            trips = editable_current_trips,
        )
        editable_upcoming_trips = cls._order_by_creation_date(
            trips = editable_upcoming_trips,
        )
        shared_trips = cls._order_shared_trips(
            shared_trip_memberships = shared_trip_memberships,
        )

        # Build result with priority, truncating to max
        result = []
        for trip in editable_current_trips:
            if len( result ) >= cls.MAX_DASHBOARD_TRIPS:
                break
            result.append( trip )
            continue

        for trip in editable_upcoming_trips:
            if len( result ) >= cls.MAX_DASHBOARD_TRIPS:
                break
            result.append( trip )
            continue

        for trip in shared_trips:
            if len( result ) >= cls.MAX_DASHBOARD_TRIPS:
                break
            result.append( trip )
            continue

        return result

    @classmethod
    def _order_by_creation_date( cls, trips: List[Trip] ) -> List[Trip]:
        return sorted(
            trips,
            key = lambda trip: trip.created_datetime,
            reverse = True,
        )

    @classmethod
    def _order_shared_trips( cls, shared_trip_memberships: List[TripMember] ) -> List[Trip]:
        sorted_memberships = sorted(
            shared_trip_memberships,
            key = lambda membership: membership.added_datetime,
            reverse = True,
        )
        return [ membership.trip for membership in sorted_memberships ]
