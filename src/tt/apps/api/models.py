from datetime import timedelta

from django.conf import settings
from django.db import models

from tt.apps.common import datetimeproxy


class APIToken(models.Model):
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
