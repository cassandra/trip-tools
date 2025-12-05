from typing import Optional

from django.core.exceptions import BadRequest

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


def exception_handler(exc: Exception, context: dict) -> Optional[Response]:
    """
    Custom exception handler that extends DRF's default handler.

    Handles Django exceptions that DRF doesn't handle by default:
    - BadRequest -> 400
    """
    # Let DRF handle its known exceptions first
    response = drf_exception_handler(exc, context)

    if response is not None:
        return response

    # Handle Django's BadRequest
    if isinstance(exc, BadRequest):
        return Response(
            {'error': str(exc) or 'Bad request'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Let other exceptions propagate (will result in 500)
    return None
