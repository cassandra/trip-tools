"""
Sync envelope generation for client-server data synchronization.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from django.utils import timezone

from tt.apps.locations.models import Location
from tt.apps.trips.models import Trip

from .enums import SyncObjectType
from .models import SyncDeletionLog


class SyncEnvelopeBuilder:
    """
    Builds the sync payload for API responses.

    The sync envelope contains version information for trips and locations,
    allowing the extension to detect changes and sync its local data.

    Trip sync:
    - Returns ALL accessible trips (not filtered by since)
    - Absence from versions means deleted/revoked

    Location sync:
    - Scoped to a specific trip via X-Sync-Trip header
    - Filtered by modified_datetime >= since
    - Includes deletion log for explicit deletion tracking
    """

    def __init__(
        self,
        user,
        since: Optional[datetime] = None,
        trip_uuid: Optional[UUID] = None,
    ):
        self.user = user
        self.since = since
        self.trip_uuid = trip_uuid

    def build( self ) -> dict:
        """Build and return the sync envelope."""
        self.as_of = timezone.now()
        envelope = {
            'as_of': self.as_of.isoformat(),
            'trip': self._build_trip_sync(),
        }
        if self.trip_uuid:
            envelope['location'] = self._build_location_sync()
        return envelope

    def _build_trip_sync( self ) -> dict:
        """
        Returns ALL accessible trips - absence means deleted/revoked.

        Always returns all trips (not filtered by since) to enable
        presence-based deletion detection.
        """
        trips = Trip.objects.for_user( self.user ).values( 'uuid', 'version' )
        return {
            'versions': { str( t['uuid'] ): t['version'] for t in trips },
        }

    def _build_location_sync( self ) -> dict:
        """
        Returns location versions for specified trip + deletions since timestamp.

        Only returns locations modified since X-Sync-Since (if provided).
        Uses SyncDeletionLog to track deleted locations.
        """
        queryset = Location.objects.filter( trip__uuid = self.trip_uuid )

        # If since provided, only return locations modified since then
        if self.since:
            queryset = queryset.filter( modified_datetime__gte = self.since )

        locations = queryset.values( 'uuid', 'version' )

        result = {
            'versions': { str( loc['uuid'] ): loc['version'] for loc in locations },
            'deleted': [],
        }

        # Only query deletions if we have a since timestamp
        if self.since:
            deleted = SyncDeletionLog.objects.filter(
                trip_uuid = self.trip_uuid,
                object_type = SyncObjectType.LOCATION,
                deleted_at__gte = self.since,
            ).values_list( 'uuid', flat = True )
            result['deleted'] = [ str( u ) for u in deleted ]

        return result
