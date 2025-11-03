from dataclasses import dataclass
from typing import List

from tt.apps.trips.enums import TripPermissionLevel
from tt.apps.trips.models import TripMember


@dataclass
class TripMemberData:

    trip_member               : TripMember
    is_user                   : bool
    can_remove                : bool
    permission_level_options  : List[ TripPermissionLevel ]

    @property
    def pk(self):
        return self.trip_member.pk
    
    @property
    def trip(self):
        return self.trip_member.trip
    
    @property
    def user(self):
        return self.trip_member.user
     
    @property
    def permission_level(self):
        return self.trip_member.permission_level
   
