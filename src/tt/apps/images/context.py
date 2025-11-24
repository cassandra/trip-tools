from dataclasses import dataclass
from typing import Optional

from django.contrib.auth.models import User as UserType

from tt.apps.trips.context import TripPageContext

from .enums import ImageAccessRole
from .models import TripImage


@dataclass
class ImagePageContext:

    user               : UserType
    trip_image         : TripImage
    image_access_role  : ImageAccessRole
    trip_page_context  : Optional[TripPageContext]  = None

    @property
    def trip(self):
        if self.trip_page_context:
            return self.trip_page_context.trip
        return None
    
