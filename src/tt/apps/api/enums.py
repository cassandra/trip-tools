from tt.apps.common.enums import LabeledEnum


class TokenType( LabeledEnum ):
    """Types of API tokens."""
    STANDARD  = ( 'Standard', 'Standard API token for programmatic access' )
    EXTENSION = ( 'Extension', 'Browser extension token' )
