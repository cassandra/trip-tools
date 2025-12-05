from dataclasses import dataclass

from .models import APIToken

@dataclass
class APITokenGenerationData:
    """
    Data returned when generating data for a new API token.
    """
    lookup_key     : str
    api_token_str  : str

    
@dataclass
class APITokenData:
    """
    Data returned when creating a new API token.

    Contains both the database record and the full api_token_str string.
    The api_token_str is only available at creation time - it cannot be retrieved later.
    """
    api_token      : APIToken
    api_token_str  : str
