from tt.apps.common.enums import LabeledEnum


class TokenType( LabeledEnum ):
    """Types of API tokens."""
    STANDARD  = ( 'Standard', 'Standard API token for programmatic access' )
    EXTENSION = ( 'Extension', 'Browser extension token' )


class SyncObjectType( LabeledEnum ):
    """
    Types of objects tracked in the sync deletion log.

    Used by SyncDeletionLog to track deletions for delta sync.
    """
    LOCATION = ( 'Location', 'A location within a trip' )
    TRIP     = ( 'Trip', 'A trip' )
