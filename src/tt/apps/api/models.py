import uuid

from datetime import timedelta

from django.conf import settings
from django.db import models

from tt.apps.common import datetimeproxy
from tt.apps.common.model_fields import LabeledEnumField

from .enums import SyncObjectType, TokenType


class APIToken( models.Model ):
    """
    API tokens for authenticating API requests.

    Token format: "tt_{lookup_key}_{secret_key}"
    - tt_: Fixed app identifier for trip-tools tokens
    - lookup_key: 8 random chars for fast DB lookup (stored in plain text)
    - secret_key: 40 random chars for authentication (only hash stored)

    The lookup_key and secret_key are generated independently, so the stored
    lookup_key reveals nothing about the secret portion.

    Use APITokenService (in services.py) for token creation and authentication.
    """
    USAGE_UPDATE_INTERVAL = timedelta( minutes = 15 )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete = models.CASCADE,
        related_name = 'api_tokens',
    )
    name = models.CharField(
        max_length = 100,
        help_text = 'Human-readable name for this token (e.g., "Chrome Extension", "Mobile App")',
    )
    lookup_key = models.CharField(
        max_length = 8,
        db_index = True,
        help_text = 'Random key for DB lookup (independent of secret_key)',
    )
    api_token_hash = models.CharField(
        max_length = 64,
        help_text = 'SHA256 hash of full api_token string',
    )
    created_at = models.DateTimeField(auto_now_add = True)
    last_used_at = models.DateTimeField(
        null = True,
        blank = True,
        help_text = 'Last time this token was used for authentication',
    )
    token_type = LabeledEnumField(
        TokenType,
        'Token Type',
    )

    class Meta:
        unique_together = [['user', 'name']]
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f"{self.name} ({self.lookup_key}...)"

    def record_usage(self) -> None:
        """Update the last_used_at timestamp, throttled to avoid excessive writes."""
        now = datetimeproxy.now()
        if ( self.last_used_at is None
             or (( now - self.last_used_at ) > self.USAGE_UPDATE_INTERVAL )):
            self.last_used_at = now
            self.save( update_fields = ['last_used_at'] )
        return


class SyncableModel( models.Model ):
    """
    Abstract base for models that participate in client-server sync.

    Provides common fields used by the sync infrastructure:
    - uuid: External identifier (never expose database IDs)
    - version: Auto-incremented on save for change detection
    - created_datetime: Record creation timestamp
    - modified_datetime: Last modification timestamp

    The version increment uses F() expressions to avoid race conditions
    on concurrent saves.
    """
    uuid = models.UUIDField(
        default = uuid.uuid4,
        unique = True,
        editable = False,
    )
    version = models.PositiveIntegerField( default = 1 )
    created_datetime = models.DateTimeField( auto_now_add = True )
    modified_datetime = models.DateTimeField( auto_now = True )

    class Meta:
        abstract = True

    def save( self, *args, **kwargs ):
        if self.pk:
            # Get the current version from DB (in case of concurrent modifications)
            current_version = self.__class__.objects.filter(
                pk = self.pk
            ).values_list( 'version', flat = True ).first()
            if current_version is not None:
                self.version = current_version + 1
        super().save( *args, **kwargs )
        return


class SyncDeletionLog( models.Model ):
    """
    Tracks deletions for sync purposes.

    Only needed for Location deletions - Trip deletions are detected
    by absence from the sync envelope's trip versions list.

    The extension uses this log to know which locations were deleted
    since the last sync, enabling proper cleanup of local data.
    """
    uuid = models.UUIDField( db_index = True )
    object_type = LabeledEnumField(
        SyncObjectType,
        'Object Type',
    )
    trip_uuid = models.UUIDField( db_index = True )
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete = models.SET_NULL,
        null = True,
        blank = True,
        related_name = 'sync_deletions',
    )
    deleted_at = models.DateTimeField( auto_now_add = True, db_index = True )

    class Meta:
        indexes = [
            models.Index( fields = ['trip_uuid', 'deleted_at'] ),
        ]
