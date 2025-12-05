from typing import Optional, Tuple

from rest_framework import authentication
from rest_framework import exceptions

from .messages import APIMessages as M
from .services import APITokenService


class APITokenDRFAuthAdapter(authentication.BaseAuthentication):
    """
    DRF authentication adapter for API token authentication using Bearer scheme.

    Bridges DRF's authentication framework to APITokenService.
    Expected header format: "Authorization: Bearer tt_{lookup_key}_{secret_key}"
    """
    keyword = 'Bearer'

    def authenticate(self, request) -> Optional[Tuple]:
        """
        Authenticate the request using API token.

        Args:
            request: The HTTP request object

        Returns:
            tuple: (user, None) if authenticated, None otherwise

        Raises:
            AuthenticationFailed: If authentication credentials are invalid
        """
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')

        if not auth_header:
            return None

        try:
            parts = auth_header.split()

            if len(parts) != 2:
                return None

            if parts[0] != self.keyword:
                return None

            api_token_str = parts[1]

        except (IndexError, ValueError):
            raise exceptions.AuthenticationFailed('Invalid token header format.')

        return self.authenticate_credentials(api_token_str)

    def authenticate_credentials(self, api_token_str: str) -> Tuple:
        """
        Validate the API token and return the associated user.

        Args:
            api_token_str: The API token string to validate

        Returns:
            tuple: (user, None) if valid

        Raises:
            AuthenticationFailed: If the token is invalid
        """
        user = APITokenService.authenticate(api_token_str)

        if user is None:
            raise exceptions.AuthenticationFailed(M.INVALID_TOKEN)

        if not user.is_active:
            raise exceptions.AuthenticationFailed(M.USER_INACTIVE)

        return (user, None)

    def authenticate_header(self, request) -> str:
        """
        Return the WWW-Authenticate header value for 401 responses.

        Args:
            request: The HTTP request object

        Returns:
            str: The authentication header value
        """
        return self.keyword
