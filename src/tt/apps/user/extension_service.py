"""
Service for managing browser extension API tokens.

Handles auto-generation of descriptive token names and collision handling.
"""
from datetime import datetime
from typing import Optional

from tt.apps.api.models import APIToken
from tt.apps.api.services import APITokenData, APITokenService


class ExtensionTokenService:
    """Service for creating browser extension API tokens."""

    TOKEN_NAME_PREFIX = 'Chrome Extension'

    @classmethod
    def create_extension_token(
        cls,
        user,
        platform: Optional[str] = None,
    ) -> APITokenData:
        """
        Create a token for a browser extension with auto-generated name.

        Args:
            user: The user to create the token for.
            platform: Optional platform info (e.g., 'Windows', 'macOS').

        Returns:
            APITokenData with the token and full token string.
        """
        token_name = cls.generate_token_name( user, platform )
        return APITokenService.create_token(
            user = user,
            api_token_name = token_name,
        )

    @classmethod
    def generate_token_name(
        cls,
        user,
        platform: Optional[str] = None,
    ) -> str:
        """
        Generate a descriptive token name with collision handling.

        Format: "Chrome Extension - {Platform} - {Month Year}"
        If collision: "Chrome Extension - {Platform} - {Month Year} (2)"

        Args:
            user: The user to check for existing tokens.
            platform: Optional platform info (e.g., 'Windows', 'macOS').

        Returns:
            A unique token name for this user.
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
    def _get_unique_name( cls, user, base_name: str ) -> str:
        """
        Find a unique token name by appending (2), (3), etc. if needed.

        Args:
            user: The user to check for existing tokens.
            base_name: The base name to make unique.

        Returns:
            A unique token name.
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
    def _name_exists( cls, user, name: str ) -> bool:
        """Check if a token with the given name exists for this user."""
        return APIToken.objects.filter( user = user, name = name ).exists()

    @classmethod
    def get_extension_tokens( cls, user ) -> list:
        """
        Get all extension tokens for a user.

        Returns tokens whose names start with the extension prefix.
        """
        return list(
            APIToken.objects.filter(
                user = user,
                name__startswith = cls.TOKEN_NAME_PREFIX,
            ).order_by( '-created_at' )
        )
