import json
from typing import Dict

from django.conf import settings
from django.http import (
    Http404,
    HttpRequest,
    HttpResponse,
    HttpResponseRedirect,
    HttpResponseNotFound,
    JsonResponse,
)
from django.shortcuts import render
from django.template import TemplateDoesNotExist
from django.template.loader import get_template
from django.urls import reverse
from django.views.generic import View

import tt.apps.common.antinode as antinode
from tt.apps.common.healthcheck import do_healthcheck
from tt.apps.common.utils import is_ajax
from tt.apps.trips.forms import TripForm
from tt.apps.trips.models import Trip

from tt.async_view import ModalView


def error_response( request             : HttpRequest,
                    sync_template_name  : str,
                    async_template_name : str,
                    status_code         : int,
                    force_json          : bool              = False,
                    context             : Dict[ str, str ]  = None ):
    """
    Helper routine for the similar error response functions.
    """
    if context is None:
        context = {}

    if 'error_message' not in context:
        context['error_message'] = 'Error (details missing).'
    if 'message' in context:
        context['error_message'] = context['message']
        
    if force_json or ( request.META.get('HTTP_ACCEPT', '') == 'application/json' ):
        return HttpResponse( json.dumps( context ),
                             content_type = "application/json",
                             status = status_code )
    
    if is_ajax( request ):
        response = antinode.modal_from_template( request,
                                                 async_template_name,
                                                 context )
    else:
        response = render( request, sync_template_name, context )
        
    response.status_code = status_code
    return response


def bad_request_response( request, message : str = None, force_json : bool = False ):
    if not message:
        message = 'Bad request.'
    context = { 'message': message }
    return error_response( request = request,
                           sync_template_name = "pages/bad_request.html",
                           async_template_name = "modals/bad_request.html",
                           status_code = 400,
                           force_json = force_json,
                           context = context )


def improperly_configured_response( request, message : str = None, force_json : bool = False ):
    if not message:
        message = 'Improperly configured.'
    context = { 'message': message }
    return error_response( request = request,
                           sync_template_name = "pages/improperly_configured.html",
                           async_template_name = "modals/improperly_configured.html",
                           status_code = 501,
                           force_json = force_json,
                           context = context )


def not_authorized_response( request, message : str = None, force_json : bool = False ):
    if not message:
        message = 'Not authorized.'
    context = { 'message': message }
    return error_response( request = request,
                           sync_template_name = "pages/not_authorized.html",
                           async_template_name = "modals/not_authorized.html",
                           status_code = 403,
                           force_json = force_json,
                           context = context )


def method_not_allowed_response( request, message : str = None, force_json : bool = False ):
    if not message:
        message = 'Method not allowed.'
    context = { 'message': message }
    return error_response( request = request,
                           sync_template_name = "pages/method_not_allowed.html",
                           async_template_name = "modals/method_not_allowed.html",
                           status_code = 405,
                           force_json = force_json,
                           context = context )


def page_not_found_response( request, message : str = None, force_json : bool = False ):
    if not message:
        message = 'Page not found.'
    context = { 'message': message }
    return error_response( request = request,
                           sync_template_name = "pages/page_not_found.html",
                           async_template_name = "modals/page_not_found.html",
                           status_code = 404,
                           force_json = force_json,
                           context = context )


def internal_error_response( request, message : str = None, force_json : bool = False ):
    if not message:
        message = 'Internal error.'
    context = { 'message': message }
    return error_response( request = request,
                           sync_template_name = "pages/internal_error.html",
                           async_template_name = "modals/internal_error.html",
                           status_code = 500,
                           force_json = force_json,
                           context = context )


def transient_error_response( request, message : str = None, force_json : bool = False ):
    if not message:
        message = 'Transient error.'
    context = { 'message': message }
    return error_response( request = request,
                           sync_template_name = "pages/transient_error.html",
                           async_template_name = "modals/transient_error.html",
                           status_code = 503,
                           force_json = force_json,
                           context = context )


def custom_404_handler( request, exception):
    return HttpResponseNotFound( page_not_found_response( request ))     


def edit_required_response( request, message : str = None, force_json : bool = False ):
    if not message:
        message = 'Edit mode is required for this request.'
    context = { 'message': message }
    return error_response( request = request,
                           sync_template_name = "pages/edit_required.html",
                           async_template_name = "modals/edit_required.html",
                           status_code = 200,  # Needed for PWA (not 403)
                           force_json = force_json,
                           context = context )


def home_javascript_files( request, filename ):
    return render(request, filename, {}, content_type = "text/javascript")

    
class HealthView( View ):
    
    def get(self, request, *args, **kwargs):
        status_dict = do_healthcheck()
        response_status = 200 if status_dict['is_healthy'] else 500
        status_dict['version'] = settings.ENV.VERSION
        return JsonResponse( {'status': status_dict }, status = response_status)


class HomeView( View ):

    def get(self, request, *args, **kwargs):
        return render( request, 'pages/home.html' )

    
class StartView( View ):

    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return not_authorized_response( request, message = 'You must be logged in to create a trip.' )

        user_trips = Trip.objects.for_user( request.user )

        if user_trips.exists():
            redirect_url = reverse( 'home' )
            return HttpResponseRedirect( redirect_url )

        form = TripForm()
        context = {
            'form': form,
        }
        return render( request, 'pages/start.html', context )

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return not_authorized_response( request, message = 'You must be logged in to create a trip.' )

        form = TripForm( request.POST )

        if form.is_valid():
            Trip.objects.create_with_owner(
                owner = request.user,
                **form.cleaned_data
            )

            redirect_url = reverse( 'home' )
            return HttpResponseRedirect( redirect_url )

        context = {
            'form': form,
        }
        return render( request, 'pages/start.html', context )


class ManifestView( View ):

    def get(self, request, *args, **kwargs):
        """
        Serves the PWA manifest.json for full screen mode support.
        Configured for landscape orientation (tablet primary use case).
        """
        return render(request, 'manifest.json', {}, content_type="application/json")

    
class FutureFeatureModalView( ModalView ):

    def get_template_name( self ) -> str:
        return 'modals/future_feature.html'
    
    def get(self, request, *args, **kwargs):

        feature_name = kwargs.get('feature_name')
        if not feature_name:
            raise Http404()
        
        feature_template_name = f'components/future/{feature_name}.html'
        try:
            get_template( feature_template_name )
        except TemplateDoesNotExist:
            raise Http404()

        feature_label = feature_name

        context = {
            'feature_label': feature_label,
            'feature_template_name': feature_template_name,
        }
        return self.modal_response( request, context = context )
