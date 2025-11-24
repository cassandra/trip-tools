from tt.apps.members.schemas import TripMemberData
from tt.apps.trips.enums import TripPermissionLevel
from tt.apps.members.models import TripMember


class TripHelpers:

    @classmethod
    def create_trip_member_data( cls,
                                 request_member  : TripMember,
                                 target_member   : TripMember ) -> TripMemberData:
        can_modify_member = request_member.can_modify_member( other_member = target_member )
        can_remove = bool( request_member.can_manage_members
                           and ( request_member.permission_level >= target_member.permission_level ))
        
        if can_modify_member:
            permission_level_options = [ x for x in TripPermissionLevel
                                         if (( request_member.permission_level >= x )
                                             and ( target_member.permission_level != x ))]
        else:
            permission_level_options = list()

        return TripMemberData(
            trip_member = target_member,
            is_user = bool( target_member.user == request_member.user ),
            can_remove = can_remove,
            permission_level_options = permission_level_options,
        )
