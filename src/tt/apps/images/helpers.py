from django.contrib.auth.models import User as UserType

from tt.apps.trips.context import TripPageContext

from .enums import ImageAccessRole
from .models import TripImage


class TripImageHelpers:

    @classmethod
    def get_image_access_mode( cls,
                               user               : UserType,
                               trip_image         : TripImage,
                               trip_page_context  : TripPageContext = None ) -> ImageAccessRole:
        
        if not user or not user.is_authenticated:
            return ImageAccessRole.NONE
        if trip_image.uploaded_by == user:
            return ImageAccessRole.OWNER
        if trip_page_context:
            if trip_page_context.request_member.can_edit_trip:
                return ImageAccessRole.EDITOR
            else:
                return ImageAccessRole.VIEWER
        return ImageAccessRole.NONE
