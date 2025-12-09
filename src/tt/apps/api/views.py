from datetime import datetime
from typing import Optional
from uuid import UUID

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .constants import APIFields as F
from .messages import APIMessages as M
from .services import APITokenService
from .sync import SyncEnvelopeBuilder
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


class SyncableAPIView( APIView ):
    """
    Base class for API views that include sync envelope in responses.

    Views inherit from this class to automatically get sync envelopes.
    The view implementation doesn't change - it still returns Response(data)
    as normal. The finalize_response() hook wraps the data with sync envelope.

    Example:
        class LocationListView(SyncableAPIView):
            def get(self, request):
                locations = [...]
                return Response(locations)  # Normal usage
                # Response automatically becomes {"data": locations, "sync": {...}}

    Sync headers:
        X-Sync-Since: ISO 8601 timestamp for incremental sync
        X-Sync-Trip: UUID of the current/active trip for location scoping
    """

    def finalize_response(
        self,
        request: Request,
        response: Response,
        *args,
        **kwargs
    ) -> Response:
        """DRF hook called before response is returned to client."""
        response = super().finalize_response( request, response, *args, **kwargs )

        # Only add sync envelope for authenticated requests with data
        if request.user.is_authenticated and hasattr( response, 'data' ):
            sync_envelope = self._build_sync_envelope( request )
            response.data = {
                'data': response.data,
                'sync': sync_envelope,
            }

        return response

    def _build_sync_envelope( self, request: Request ) -> dict:
        since = self._parse_sync_since( request )
        trip_uuid = self._parse_sync_trip( request )
        builder = SyncEnvelopeBuilder( request.user, since, trip_uuid )
        return builder.build()

    def _parse_sync_since( self, request: Request ) -> Optional[datetime]:
        header = request.headers.get( 'X-Sync-Since' )
        if header:
            try:
                # Handle 'Z' suffix for UTC
                return datetime.fromisoformat( header.replace( 'Z', '+00:00' ) )
            except ValueError:
                return None
        return None

    def _parse_sync_trip( self, request: Request ) -> Optional[UUID]:
        header = request.headers.get( 'X-Sync-Trip' )
        if header:
            try:
                return UUID( header )
            except ValueError:
                return None
        return None
