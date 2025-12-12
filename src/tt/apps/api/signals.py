"""
Signal handlers for sync infrastructure.
"""
from django.db.models.signals import pre_delete
from django.dispatch import receiver

from tt.apps.locations.models import Location
from tt.apps.trips.models import Trip

from .enums import SyncObjectType
from .models import SyncDeletionLog


@receiver( pre_delete, sender = Location )
def log_location_deletion( sender, instance, **kwargs ):
    """
    Log Location deletions to SyncDeletionLog for sync purposes.

    This allows the extension to detect deleted locations and clean up
    its local data accordingly.

    Note: deleted_by is currently None as we don't have request context
    in the signal. This can be enhanced later with middleware/context
    if auditing of who deleted is needed.
    """
    SyncDeletionLog.objects.create(
        uuid = instance.uuid,
        object_type = SyncObjectType.LOCATION,
        trip_uuid = instance.trip.uuid,
        deleted_by = None,
    )
    return


@receiver( pre_delete, sender = Trip )
def log_trip_deletion( sender, instance, **kwargs ):
    """
    Log Trip deletions to SyncDeletionLog for sync purposes.

    This allows the extension to detect deleted trips and clean up
    its local data accordingly.

    Note: For trips, trip_uuid is self-referential (the deleted trip's UUID).
    """
    SyncDeletionLog.objects.create(
        uuid = instance.uuid,
        object_type = SyncObjectType.TRIP,
        trip_uuid = instance.uuid,
        deleted_by = None,
    )
    return
