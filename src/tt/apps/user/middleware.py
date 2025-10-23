from django.http import HttpResponseRedirect
from django.urls import resolve, reverse

import tt.apps.common.antinode as antinode
from tt.apps.common.utils import is_ajax


class AuthenticationMiddleware(object):

    EXEMPT_VIEW_URL_NAMES = {
        'admin',
        'manifest',
        'user_signin',
        'user_signin_magic_code',
        'user_signin_magic_link',
        'notify_email_unsubscribe',
    }

    def __init__(self, get_response):
        self.get_response = get_response
        return

    def __call__(self, request):
        
        if request.user.is_authenticated:
            return self.get_response( request )

        resolver_match = resolve( request.path )
        view_url_name = resolver_match.url_name
        app_name = resolver_match.app_name
        
        if (( app_name == 'admin' )
            or ( view_url_name in self.EXEMPT_VIEW_URL_NAMES )):
            return self.get_response(request)

        redirect_url = reverse( 'user_signin' )
        if is_ajax( request ):
            return antinode.redirect_response( redirect_url )
        return HttpResponseRedirect( redirect_url )
