import logging
from typing import Dict

from django.shortcuts import render
from django.template.loader import get_template
from django.views.generic import View

import tt.apps.common.antinode as antinode
from tt.apps.common.utils import is_ajax

from tt.exceptions import MethodNotAllowedError

logger = logging.getLogger(__name__)


class AsyncView( View ):
    """
    Use this when async calls always populate the same <div> Id.
    """
    
    def get_target_div_id( self ) -> str:
        raise NotImplementedError('Subclasses must override this method.')

    def get_template_name( self ) -> str:
        raise NotImplementedError('Subclasses must override this method.')

    def get_template_context( self, request, *args, **kwargs ) -> Dict[ str, str ]:
        """ Can raise exceptions like BadRequest, Http404, etc. """
        raise NotImplementedError('Subclasses must override this method.')

    def get_content( self, request, *args, **kwargs ) -> str:
        template_name = self.get_template_name()
        template = get_template( template_name )
        context = self.get_template_context( request, *args, **kwargs )
        return template.render( context, request = request )

    def get( self, request, *args, **kwargs ):
        div_id = self.get_target_div_id()
        content = self.get_content( request, *args, **kwargs )
        return antinode.response(
            insert_map = { div_id: content },
        )

    def post_template_context( self, request, *args, **kwargs ) -> Dict[ str, str ]:
        """ Can raise exceptions like BadRequest, Http404, etc. """
        raise MethodNotAllowedError()

    def post_content( self, request, *args, **kwargs ) -> str:
        template_name = self.get_template_name()
        template = get_template( template_name )
        context = self.post_template_context( request, *args, **kwargs )
        return template.render( context, request = request )

    def post( self, request, *args, **kwargs ):
        div_id = self.get_target_div_id()
        content = self.post_content( request, *args, **kwargs )
        return antinode.response(
            insert_map = { div_id: content },
        )

    
class ModalView( View ):

    DEFAULT_PAGE_TEMPLATE_NAME = 'pages/main_default.html'
    
    def get_template_name( self ) -> str:
        raise NotImplementedError('Subclasses must override this method.')

    def get( self, request, *args, **kwargs ):
        return self.modal_response( request )
    
    def modal_response( self, request, context = None, template_name = None, status = 200 ):
        
        if context is None:
            context = dict()
        if template_name is None:
            template_name = self.get_template_name()
        if is_ajax( request ):
            modal_response = antinode.modal_from_template(
                request = request,
                template_name = template_name,
                context = context,
                status = status,
            )
            return modal_response

        context['initial_modal_template_name'] = template_name
        template_name = self.DEFAULT_PAGE_TEMPLATE_NAME
        return render( request,
                       template_name,
                       context,
                       status = status )

    def redirect_response( self, request, redirect_url ):
        return antinode.redirect_response( redirect_url )

    def refresh_response( self, request ):
        return antinode.refresh_response()
