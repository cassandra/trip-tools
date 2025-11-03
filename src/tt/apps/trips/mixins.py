from django.contrib.auth import get_user_model
from django.core.exceptions import BadRequest
from django.http import Http404, HttpRequest

from .enums import TripPermissionLevel
from .models import Trip, TripMember

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
        except TripMember.DoesNotExist:
            raise Http404()

    def assert_has_permission( self, 
                               trip_member     : TripMember,
                               required_level  : TripPermissionLevel ):
        if not trip_member.has_trip_permission( required_level ):
            raise Http404( 'Trip not found' )
        return
        
    def assert_is_viewer( self, trip_member : TripMember ):
        self.assert_has_permission( 
            trip_member = trip_member,
            required_level = TripPermissionLevel.VIEWER,
        )
        return    
        
    def assert_is_editor( self, trip_member : TripMember ):
        self.assert_has_permission( 
            trip_member = trip_member,
            required_level = TripPermissionLevel.EDITOR,
        )
        return    
        
    def assert_is_admin( self, trip_member : TripMember ):
        self.assert_has_permission( 
            trip_member = trip_member,
            required_level = TripPermissionLevel.ADMIN,
        )
        return    
