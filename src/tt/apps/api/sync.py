"""
Sync envelope generation for client-server data synchronization.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from django.utils import timezone

from tt.apps.locations.models import Location
from tt.apps.trips.api.serializers import TripSerializer
from tt.apps.trips.models import Trip

from .constants import APIFields as F
from .enums import SyncObjectType
from .models import SyncDeletionLog


class SyncEnvelopeBuilder:
    """
    Builds the sync payload for API responses.

    The sync envelope contains full trip data and location versions,
    allowing the extension to update its local data directly.

    Trip sync:
    - Returns full trip objects (not just versions) for direct updates
    - Returns ALL accessible trips (including PAST) for GMM map index
    - Filtered by modified_datetime >= since for delta sync
    - Uses SyncDeletionLog for explicit deletion tracking

    Location sync:
    - Scoped to a specific trip via X-Sync-Trip header
    - Filtered by modified_datetime >= since
    - Includes deletion log for explicit deletion tracking
    - Note: Locations still use version-only pattern (out of scope for now)
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
            F.SYNC_AS_OF: self.as_of.isoformat(),
        }

        # Sync data requires authentication
        if not self.user.is_authenticated:
            return envelope

        envelope[F.SYNC_TRIP] = self._build_trip_sync()

        if self.trip_uuid:
            envelope[F.SYNC_LOCATION] = self._build_location_sync()

        return envelope

    def _build_trip_sync( self ) -> dict:
        """
        Returns full trip data for delta sync.

        Includes ALL trips (including PAST) to support the GMM map index,
        which maps gmm_map_id to trip_uuid for routing GMM operations.

        Uses delta pattern: only returns trips modified since X-Sync-Since.
        Uses SyncDeletionLog for explicit deletion tracking.

        Returns full trip objects using TripSerializer so the extension
        can update its local data directly without additional API calls.
        """
        queryset = Trip.objects.for_user( self.user )

        # If since provided, only return trips modified since then
        if self.since:
            queryset = queryset.filter( modified_datetime__gte = self.since )

        serializer = TripSerializer( queryset, many = True )
        updates = { trip[F.UUID]: trip for trip in serializer.data }

        result = {
            F.SYNC_UPDATES: updates,
            F.SYNC_DELETED: [],
        }

        # Query deletions - filter by since if provided, otherwise return all
        deletion_queryset = SyncDeletionLog.objects.filter(
            object_type = SyncObjectType.TRIP,
        )
        if self.since:
            deletion_queryset = deletion_queryset.filter( deleted_at__gte = self.since )

        result[F.SYNC_DELETED] = [
            str( u ) for u in deletion_queryset.values_list( 'uuid', flat = True )
        ]

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
            F.SYNC_VERSIONS: { str( loc['uuid'] ): loc['version'] for loc in locations },
            F.SYNC_DELETED: [],
        }

        # Query deletions - filter by since if provided, otherwise return all
        deletion_queryset = SyncDeletionLog.objects.filter(
            trip_uuid = self.trip_uuid,
            object_type = SyncObjectType.LOCATION,
        )
        if self.since:
            deletion_queryset = deletion_queryset.filter( deleted_at__gte = self.since )

        result[F.SYNC_DELETED] = [
            str( u ) for u in deletion_queryset.values_list( 'uuid', flat = True )
        ]

        return result
