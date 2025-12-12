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
    - Returns ALL accessible trips (including PAST) for GMM map index
    - Filtered by modified_datetime >= since for delta sync
    - Includes metadata: gmm_map_id, title, status
    - Uses SyncDeletionLog for explicit deletion tracking

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
        """
        Build and return the sync envelope.

        For anonymous users, returns only as_of timestamp.
        For authenticated users, includes trip and optionally location sync.
        """
        self.as_of = timezone.now()
        envelope = {
            'as_of': self.as_of.isoformat(),
        }

        # Sync data requires authentication
        if not self.user.is_authenticated:
            return envelope

        envelope['trip'] = self._build_trip_sync()

        if self.trip_uuid:
            envelope['location'] = self._build_location_sync()

        return envelope

    def _build_trip_sync( self ) -> dict:
        """
        Returns trip versions for delta sync.

        Includes ALL trips (including PAST) to support the GMM map index,
        which maps gmm_map_id to trip_uuid for routing GMM operations.

        Uses delta pattern: only returns trips modified since X-Sync-Since.
        Uses SyncDeletionLog for explicit deletion tracking.

        Each trip version includes metadata:
        - gmm_map_id: For building the GMM map index
        - title: For display in the extension UI
        - created: For working set ordering
        """
        queryset = Trip.objects.for_user( self.user )

        # If since provided, only return trips modified since then
        if self.since:
            queryset = queryset.filter( modified_datetime__gte = self.since )

        trips = queryset.values( 'uuid', 'version', 'gmm_map_id', 'title', 'created_datetime' )

        result = {
            'versions': {
                str( t['uuid'] ): {
                    'version': t['version'],
                    'gmm_map_id': t['gmm_map_id'],
                    'title': t['title'],
                    'created': t['created_datetime'].isoformat(),
                }
                for t in trips
            },
            'deleted': [],
        }

        # Query deletions - filter by since if provided, otherwise return all
        deletion_queryset = SyncDeletionLog.objects.filter(
            object_type = SyncObjectType.TRIP,
        )
        if self.since:
            deletion_queryset = deletion_queryset.filter( deleted_at__gte = self.since )

        result['deleted'] = [ str( u ) for u in deletion_queryset.values_list( 'uuid', flat = True ) ]

        return result

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

        # Query deletions - filter by since if provided, otherwise return all
        deletion_queryset = SyncDeletionLog.objects.filter(
            trip_uuid = self.trip_uuid,
            object_type = SyncObjectType.LOCATION,
        )
        if self.since:
            deletion_queryset = deletion_queryset.filter( deleted_at__gte = self.since )

        result['deleted'] = [ str( u ) for u in deletion_queryset.values_list( 'uuid', flat = True ) ]

        return result
