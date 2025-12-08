from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .constants import APIFields as F
from .messages import APIMessages as M
from .services import APITokenService
from .utils import get_str


class TokenCollectionView(APIView):
    """
    List user's API tokens or create a new one.
    """
    permission_classes = [ IsAuthenticated ]

    def get( self, request: Request ) -> Response:
        """Returns list of user's tokens (without secret keys)."""
        api_tokens = APITokenService.list_tokens( request.user )
        data = [
            {
                F.NAME: api_token.name,
                F.LOOKUP_KEY: api_token.lookup_key,
                F.TOKEN_TYPE: str( api_token.token_type ),
                F.CREATED_AT: api_token.created_at.isoformat(),
                F.LAST_USED_AT: api_token.last_used_at.isoformat() if api_token.last_used_at else None,
            }
            for api_token in api_tokens
        ]
        return Response( data )

    def post( self, request: Request ) -> Response:
        """Creates a new token and returns the api_token_str (once only)."""
        api_token_name = get_str( request.data, F.NAME )

        if not api_token_name:
            return Response(
                { F.ERROR: M.is_required( 'Token name' ) },
                status = status.HTTP_400_BAD_REQUEST
            )

        # Check for duplicate name
        if APITokenService.name_exists( request.user, api_token_name ):
            return Response(
                { F.ERROR: M.already_exists( 'Token', 'name' ) },
                status = status.HTTP_400_BAD_REQUEST
            )

        # Create the token
        token_data = APITokenService.create_token(
            user = request.user,
            api_token_name = api_token_name,
        )

        return Response(
            {
                F.NAME: token_data.api_token.name,
                F.LOOKUP_KEY: token_data.api_token.lookup_key,
                F.TOKEN: token_data.api_token_str,  # Only returned once!
                F.CREATED_AT: token_data.api_token.created_at.isoformat(),
            },
            status = status.HTTP_201_CREATED
        )


class TokenItemView( APIView ):
    """
    Delete a specific API token.
    """
    permission_classes = [ IsAuthenticated ]

    def delete( self, request: Request, lookup_key: str ) -> Response:
        """
        Delete token. Always returns 204 to prevent enumeration attacks.
        """
        APITokenService.delete_token( request.user, lookup_key )
        return Response( status = status.HTTP_204_NO_CONTENT )


class CurrentUserView(APIView):
    """
    Get information about the currently authenticated user.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        """Returns basic user info: uuid, email."""
        user = request.user
        return Response({
            F.UUID: str( user.uuid ),
            F.EMAIL: user.email,
        })
