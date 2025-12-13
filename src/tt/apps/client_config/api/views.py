"""
API views for client config.
"""

from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from tt.apps.api.views import TtApiView

from ..services import ClientConfigService


class ClientConfigView(TtApiView):
    """
    Returns full client configuration with version hash.

    The config includes location categories and subcategories needed by
    browser extensions. Version hash enables efficient sync - clients can
    compare versions to detect changes without fetching full payload.

    Response wrapped in {"data": {...}} envelope by TtApiView.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        """Return full client config with version."""
        return Response(ClientConfigService.get_config_serialized())
