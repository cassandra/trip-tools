from django.contrib.auth import get_user_model
from django.core.exceptions import BadRequest, PermissionDenied
from django.http import Http404, HttpRequest

from tt.apps.members.models import TripMember

from .enums import TripPermissionLevel
from .models import Trip

User = get_user_model()


class TripViewMixin:

    def get_trip_member( self,
                         request  : HttpRequest,
                         trip_id  : int = None,
                         *args, **kwargs ) -> TripMember:
        if not trip_id:
            for arg_name in [ 'trip_id', 'trip_pk', 'trip' ]:
                try:
                    trip_id = int( request.kwargs.get( arg_name ))
                    break
                except ( TypeError, ValueError):
                    pass
                continue

        if not trip_id:
            raise BadRequest()
        try:
            trip = Trip.objects.get( pk = trip_id )
            return TripMember.objects.get( trip = trip, user = request.user )
        except Trip.DoesNotExist:
            raise Http404()
        except TripMember.DoesNotExist:
            raise Http404()

    def assert_has_permission( self,
                               trip_member     : TripMember,
                               required_level  : TripPermissionLevel ) -> None:
        if not trip_member.has_trip_permission( required_level ):
            raise PermissionDenied( 'Insufficient permission for this action' )

    def assert_is_viewer( self, trip_member : TripMember ) -> None:
        self.assert_has_permission(
            trip_member = trip_member,
            required_level = TripPermissionLevel.VIEWER,
        )

    def assert_is_editor( self, trip_member : TripMember ) -> None:
        self.assert_has_permission(
            trip_member = trip_member,
            required_level = TripPermissionLevel.EDITOR,
        )

    def assert_is_admin( self, trip_member : TripMember ) -> None:
        self.assert_has_permission(
            trip_member = trip_member,
            required_level = TripPermissionLevel.ADMIN,
        )    
