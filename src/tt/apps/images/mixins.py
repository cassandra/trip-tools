from typing import Optional
from uuid import UUID

from django.http import HttpRequest

from tt.environment.constants import TtConst


class ImagesViewMixin:
    """Mixin providing common image upload functionality."""

    def get_upload_session_uuid(self, request: HttpRequest) -> Optional[UUID]:
        upload_session_uuid_str = request.POST.get(TtConst.UPLOAD_SESSION_UUID_FIELD)
        if upload_session_uuid_str:
            try:
                return UUID(upload_session_uuid_str)
            except ValueError:
                pass
        return None
