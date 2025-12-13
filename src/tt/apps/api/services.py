import hashlib
import logging
import secrets
from typing import Optional, Tuple

from django.contrib.auth import get_user_model
from django.db.models import QuerySet

from .enums import TokenType
from .models import APIToken
from .schemas import APITokenData, APITokenGenerationData
from .utils import clean_str

logger = logging.getLogger( __name__ )

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
    MAX_TOKENS_PER_USER = 100

    @classmethod
    def user_token_count(cls, user: User) -> int:
        return APIToken.objects.filter(user=user).count()

    @classmethod
    def can_create_token(cls, user: User) -> bool:
        return cls.user_token_count(user) < cls.MAX_TOKENS_PER_USER

    @classmethod
    def _generate_api_token_str(cls) -> APITokenGenerationData:
        """
        Generate a secure random API token string with independent lookup key.

        Format: "tt_{lookup_key}_{secret_key}"
        The lookup_key and secret_key are generated independently for security.
        """
        lookup_key = secrets.token_hex(4)  # Results in 8 hex characters
        secret_key = secrets.token_urlsafe(30)
        api_token_str = f"{cls.APP_PREFIX}{lookup_key}_{secret_key}"
        return APITokenGenerationData(
            lookup_key = lookup_key,
            api_token_str = api_token_str,
        )

    @classmethod
    def _hash_api_token_str(cls, api_token_str: str) -> str:
        return hashlib.sha256(api_token_str.encode()).hexdigest()

    @classmethod
    def create_token( cls,
                      user           : User,
                      api_token_name : str,
                      token_type     : TokenType = TokenType.STANDARD ) -> APITokenData:
        """
        The api_token_str is only available at creation - it cannot be retrieved later.
        """
        token_generation_data = cls._generate_api_token_str()
        api_token_hash = cls._hash_api_token_str( token_generation_data.api_token_str )

        api_token = APIToken.objects.create(
            user = user,
            name = api_token_name,
            lookup_key = token_generation_data.lookup_key,
            api_token_hash = api_token_hash,
            token_type = token_type,
        )
        return APITokenData(
            api_token = api_token,
            api_token_str = token_generation_data.api_token_str,
        )

    @classmethod
    def authenticate( cls, api_token_str: str ) -> Optional[User]:
        """
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

    # -------------------------------------------------------------------------
    # Token Lookup and Deletion
    # -------------------------------------------------------------------------

    @classmethod
    def name_exists( cls, user: User, name: str ) -> bool:
        return APIToken.objects.filter( user = user, name = name ).exists()

    @classmethod
    def get_token_by_lookup_key( cls,
                                 user       : User,
                                 lookup_key : str ) -> Tuple[Optional[APIToken], Optional[str]]:
        """
        Sanitizes the lookup_key input and checks for exactly one match.

        Returns:
            (token, None) if exactly one token found
            (None, error_message) if zero or multiple tokens found
        """
        tokens = APIToken.objects.filter(
            lookup_key = clean_str( lookup_key ),
            user = user,
        )
        count = tokens.count()

        if count == 0:
            return None, 'Token not found'
        if count > 1:
            logger.error(
                f'Multiple tokens found for lookup_key={lookup_key}, user={user.id}. '
                f'Refusing operation to prevent data loss.'
            )
            return None, 'Unable to process token. Please contact support.'

        return tokens.first(), None

    @classmethod
    def delete_token( cls,
                      user       : User,
                      lookup_key : str ) -> Tuple[bool, Optional[str]]:
        """
        Delete a token with safety checks.

        Returns:
            (True, None) if token was deleted
            (False, error_message) if token not found or deletion refused
        """
        token, error = cls.get_token_by_lookup_key( user, lookup_key )
        if error:
            return False, error

        token.delete()
        return True, None

    # -------------------------------------------------------------------------
    # Token Listing
    # -------------------------------------------------------------------------

    @classmethod
    def list_tokens( cls,
                     user       : User,
                     token_type : Optional[TokenType] = None ) -> QuerySet:
        """
        List tokens for user, optionally filtered by type.
        Returns queryset ordered by -created_at.
        """
        qs = APIToken.objects.filter( user = user )
        if token_type is not None:
            qs = qs.filter( token_type = token_type )
        return qs.order_by( '-created_at' )
