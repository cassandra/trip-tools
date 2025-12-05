import hashlib
import secrets
from typing import Optional

from django.contrib.auth import get_user_model

from .models import APIToken
from .schemas import APITokenData, APITokenGenerationData

User = get_user_model()


class APITokenService:
    """
    Service class for API token operations.

    Handles token creation and authentication, keeping business logic
    separate from the APIToken model.

    Glossary:
    - api_token_str: Full token string the user holds (tt_{lookup_key}_{secret_key})
    - APIToken: The database model/record
    - lookup_key: 8 random chars for fast DB lookup (stored in plain text)
    - secret_key: 40 random chars for authentication (never stored)
    - api_token_hash: SHA256 hash of api_token_str (stored for verification)
    """

    APP_PREFIX = 'tt_'

    @classmethod
    def _generate_api_token_str(cls) -> APITokenGenerationData:
        """
        Generate a secure random API token string with independent lookup key.

        Format: "tt_{lookup_key}_{secret_key}"
        The lookup_key and secret_key are generated independently for security.
        """
        lookup_key = secrets.token_urlsafe(6)[:8]
        secret_key = secrets.token_urlsafe(30)
        api_token_str = f"{cls.APP_PREFIX}{lookup_key}_{secret_key}"
        return APITokenGenerationData(
            lookup_key = lookup_key,
            api_token_str = api_token_str,
        )

    @classmethod
    def _hash_api_token_str(cls, api_token_str: str) -> str:
        """
        Hash an API token string using SHA256.

        Args:
            api_token_str: The full API token string to hash

        Returns:
            str: Hex-encoded SHA256 hash
        """
        return hashlib.sha256(api_token_str.encode()).hexdigest()

    @classmethod
    def create_token(cls, user: User, api_token_name: str) -> APITokenData:
        """
        Create a new API token for a user.
        The api_token_str is only available at creation - it cannot be retrieved later.
        """
        token_generation_data = cls._generate_api_token_str()
        api_token_hash = cls._hash_api_token_str( token_generation_data.api_token_str )

        api_token = APIToken.objects.create(
            user = user,
            name = api_token_name,
            lookup_key = token_generation_data.lookup_key,
            api_token_hash = api_token_hash,
        )
        return APITokenData(
            api_token = api_token,
            api_token_str = token_generation_data.api_token_str,
        )

    @classmethod
    def authenticate( cls, api_token_str: str ) -> Optional[User]:
        """
        Authenticate an API token string and return the associated user.

        Args:
            api_token_str: The API token string to authenticate (format: tt_{lookup_key}_{secret_key})

        Returns:
            User instance if token is valid, None otherwise
        """
        if ( not api_token_str
             or not api_token_str.startswith( cls.APP_PREFIX )):
            return None

        # Extract lookup_key from "tt_{lookup_key}_{secret_key}" format
        parts = api_token_str.split('_', 2)  # ['tt', lookup_key, secret_key]
        if len(parts) != 3:
            return None
        lookup_key = parts[1]

        # Hash the full token string
        api_token_hash = cls._hash_api_token_str( api_token_str )

        # Find tokens with matching lookup_key
        tokens = APIToken.objects.filter( lookup_key = lookup_key ).select_related('user')

        # Use constant-time comparison to prevent timing attacks
        for token in tokens:
            if secrets.compare_digest( token.api_token_hash, api_token_hash ):
                token.record_usage()
                return token.user

        return None
