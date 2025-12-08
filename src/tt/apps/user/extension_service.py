"""
Service for managing browser extension API tokens.

Handles auto-generation of descriptive token names and collision handling.
"""
from datetime import datetime
from typing import Optional

from django.contrib.auth import get_user_model
from django.db import transaction

from tt.apps.api.enums import TokenType
from tt.apps.api.models import APIToken
from tt.apps.api.services import APITokenData, APITokenService

User = get_user_model()


class ExtensionTokenService:
    """Service for creating browser extension API tokens."""

    TOKEN_NAME_PREFIX = 'Chrome Extension'

    @classmethod
    def create_extension_token( cls,
                                user      : User,
                                platform  : Optional[str] = None ) -> APITokenData:
        """
        Args:
            platform: Optional platform info (e.g., 'Windows', 'macOS').

        Uses a transaction with select_for_update to prevent race conditions
        when multiple requests try to create tokens simultaneously.
        """
        with transaction.atomic():
            token_name = cls._generate_token_name_locked( user, platform )
            return APITokenService.create_token(
                user = user,
                api_token_name = token_name,
                token_type = TokenType.EXTENSION,
            )

    @classmethod
    def _generate_token_name_locked( cls,
                                     user      : User,
                                     platform  : Optional[str] = None ) -> str:
        """
        Generate a unique token name while holding a lock on user's tokens.

        Must be called within a transaction.atomic() block.
        Uses select_for_update to prevent race conditions.
        """
        # Lock all tokens for this user to prevent concurrent name conflicts
        list( APIToken.objects.filter( user=user ).select_for_update() )

        return cls.generate_token_name( user, platform )

    @classmethod
    def generate_token_name( cls,
                             user      : User,
                             platform  : Optional[str] = None ) -> str:
        """
        Generate a descriptive token name with collision handling.

        Format: "Chrome Extension - {Platform} - {Month Year}"
        If collision: "Chrome Extension - {Platform} - {Month Year} (2)"

        Args:
            platform: Optional platform info (e.g., 'Windows', 'macOS').

        Note: For race-condition-safe token creation, use create_extension_token()
        which wraps this in a transaction with row locking.
        """
        # Build base name components
        parts = [cls.TOKEN_NAME_PREFIX]

        if platform:
            parts.append( platform )

        # Add current month and year
        now = datetime.now()
        date_str = now.strftime( '%b %Y' )  # e.g., "Dec 2025"
        parts.append( date_str )

        base_name = ' - '.join( parts )

        # Check for collisions and find unique name
        return cls._get_unique_name( user, base_name )

    @classmethod
    def _get_unique_name( cls, user : User, base_name: str ) -> str:
        """
        Find a unique token name by appending (2), (3), etc. if needed.

        Args:
            base_name: The base name to make unique.
        """
        # Check if base name is available
        if not cls._name_exists( user, base_name ):
            return base_name

        # Try numbered suffixes
        suffix = 2
        while True:
            candidate = f'{base_name} ({suffix})'
            if not cls._name_exists( user, candidate ):
                return candidate
            suffix += 1
            # Safety limit to prevent infinite loop
            if suffix > 100:
                # Fallback: append timestamp
                timestamp = datetime.now().strftime( '%H%M%S' )
                return f'{base_name} ({timestamp})'

    @classmethod
    def _name_exists( cls, user : User, name: str ) -> bool:
        return APIToken.objects.filter( user = user, name = name ).exists()

    @classmethod
    def get_extension_tokens( cls, user : User ) -> list:
        """
        Returns tokens with token_type = EXTENSION.
        """
        return list(
            APIToken.objects.filter(
                user = user,
                token_type = TokenType.EXTENSION,
            ).order_by( '-created_at' )
        )
