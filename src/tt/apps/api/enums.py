from tt.apps.common.enums import LabeledEnum


class TokenType( LabeledEnum ):
    """Types of API tokens."""
    STANDARD  = ( 'Standard', 'Standard API token for programmatic access' )
    EXTENSION = ( 'Extension', 'Browser extension token' )


class SyncObjectType( LabeledEnum ):
    """
    Types of objects tracked in the sync deletion log.

    Trip deletions are not tracked here - the extension detects Trip
    deletions/revocations by their absence from the sync envelope's
    trip versions list.
    """
    LOCATION = ( 'Location', 'A location within a trip' )
