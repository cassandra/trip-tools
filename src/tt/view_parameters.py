from dataclasses import dataclass

from django.http import HttpRequest


@dataclass
class ViewParameters:
    """ For session state """
    
    trip_id         : int  = None

    def to_session( self, request : HttpRequest ):
        if not hasattr( request, 'session' ):
            return
        request.session['trip_id'] = str(self.trip_id)
        return

    @staticmethod
    def from_session( request : HttpRequest ):
        if not request:
            return ViewParameters()
        if not hasattr( request, 'session' ):
            return ViewParameters()
        try:
            trip_id = int( request.session.get( 'trip_id' ))
        except ( TypeError, ValueError ):
            trip_id = None

        return ViewParameters(
            trip_id = trip_id,
        )
    
