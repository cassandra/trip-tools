import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User as UserType
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.exceptions import BadRequest, ValidationError
from django.core.validators import validate_email
from django.http import Http404, HttpRequest, HttpResponseRedirect
from django.shortcuts import render
from django.template.loader import get_template
from django.urls import reverse
from django.views.generic import View

from tt.apps.api.enums import TokenType
from tt.apps.api.services import APITokenService
from tt.apps.common.rate_limit import rate_limit
import tt.apps.common.antinode as antinode
from tt.environment.constants import TtConst
from tt.apps.notify.email_sender import EmailSender
from tt.async_view import ModalView

from . import forms
from .context import AccountPageContext
from .enums import AccountPageType, SigninErrorType
from .extension_service import ExtensionTokenService
from .magic_code_generator import MagicCodeStatus, MagicCodeGenerator
from .signin_manager import SigninManager
from .schemas import UserAuthenticationData

logger = logging.getLogger(__name__)


class UserSigninView( View ):

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            url = reverse( 'dashboard_home' )
            return HttpResponseRedirect( url )
            
        error_message = None
        error_param = request.GET.get( 'error' )

        if error_param:
            try:
                error_type = SigninErrorType.from_name( error_param )
                error_message = error_type.description
            except ValueError:
                # Unknown error type, ignore
                pass

        context = {
            'email_not_configured': not EmailSender.is_email_configured(),
            'error_message': error_message,
        }
        return render( request, 'user/pages/signin.html', context )

    def post(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            raise BadRequest( 'You are already logged in.' )

        email_address = request.POST.get('email')
        if not email_address:
            raise BadRequest( 'No email provided' )

        try:
            validate_email( email_address )
        except ValidationError:
            raise BadRequest( 'Invalid email provided' )

        User = get_user_model()
        try:
            existing_user = User.objects.get( email = email_address )
            logger.debug( f'Found existing user with email: {email_address}' )
            return SendMagicLinkEmailView().send_signin_magic_link(
                request = request,
                override_user = existing_user,
            )
        except User.DoesNotExist:
            # Show the same message so as not to give away whether account exists or not.
            logger.debug( f'No user exists with email: {email_address}' )
            return SigninMagicCodeView().get_response(
                request = request,
                magic_code_form = forms.SigninMagicCodeForm(
                    initial = { 'email_address': email_address }
                )
            )


class SendMagicLinkEmailView( View ):

    def send_signin_magic_link( self,
                                request        : HttpRequest,
                                override_user  : UserType      = None ):

        user_auth_data = UserAuthenticationData(
            request = request,
            override_user = override_user,
        )
        SigninManager().send_signin_magic_link_email(
            request = request,
            user_auth_data = user_auth_data,
        )
        return SigninMagicCodeView().get_response(
            request = request,
            magic_code_form = user_auth_data.magic_code_form,
        )

    
class SigninMagicCodeView( View ):

    TEMPLATE_NAME = 'user/pages/magic_code_signin.html'

    def get_response( self,
                      request          : HttpRequest,
                      magic_code_form  : forms.SigninMagicCodeForm,
                      status           : int                           = 200 ):
        context = {
            'magic_code_form': magic_code_form,
        }
        response = render( request, self.TEMPLATE_NAME, context )
        response.status_code = status
        return response
    
    def post( self, request, *args, **kwargs ):
        
        magic_code_form = forms.SigninMagicCodeForm( request.POST )
        if not magic_code_form.is_valid():
            return self.get_response( request, magic_code_form = magic_code_form, status = 400 )        

        email_address = magic_code_form.cleaned_data.get('email_address')
        magic_code = magic_code_form.cleaned_data.get('magic_code')
        
        User = get_user_model()
        try:
            existing_user = User.objects.get( email = email_address )
        except User.DoesNotExist:
            raise BadRequest( 'Email is invalid.' )

        magic_code_generator = MagicCodeGenerator()
        magic_code_status = magic_code_generator.check_magic_code( request, magic_code = magic_code )

        if magic_code_status == MagicCodeStatus.INVALID:
            error_message = 'Invalid access code.'
        elif magic_code_status == MagicCodeStatus.EXPIRED:
            error_message = 'Access code has expired.'
        elif magic_code_status == MagicCodeStatus.VALID:
            error_message = None
        else:
            error_message = 'Access code generated an unexpected error.'

        logger.debug( f'Signin Magic: Email={email_address}, Code={magic_code}, Status={magic_code_status}' )

        if error_message:
            magic_code_form.add_error( 'magic_code', error_message )
            return self.get_response( request, magic_code_form = magic_code_form, status = 400 )
        
        logger.debug( f'Signin Magic: Email={email_address}, Code={magic_code}, Status={magic_code_status}' )

        request.user = existing_user
        SigninManager().do_login( request = request, verified_email = True )
        magic_code_generator.expire_magic_code( request )

        url = reverse( 'dashboard_home' )
        return HttpResponseRedirect( url )

    
class SigninMagicLinkView( View ):
    """ This is the view for the links we include in emails for logging in. """

    def get( self, request, *args, **kwargs ):

        token = kwargs.get('token')
        email_address = kwargs.get('email')

        if not token or not email_address:
            raise BadRequest( 'Malformed request.' )

        User = get_user_model()
        try:
            existing_user = User.objects.get( email = email_address )
        except User.DoesNotExist:
            raise BadRequest( 'Email is not valid.' )

        # We re-purpose the clever way tokens are used for password resets in Django
        token_generator = PasswordResetTokenGenerator()
        is_valid = token_generator.check_token( user = existing_user, token = token )

        logger.debug( f'Signin Magic: EMAIL = {email_address}, TOKEN = {token}, VALID = {is_valid}' )

        if not is_valid:
            return render( request, 'user/pages/signin_magic_bad_link.html' )

        request.user = existing_user
        SigninManager().do_login( request = request, verified_email = True )

        url = reverse( 'dashboard_home' )
        return HttpResponseRedirect( url )


class UserSignoutView(LoginRequiredMixin, ModalView):
    """Signout with confirmation modal on GET, actual signout on POST."""

    def get_template_name(self) -> str:
        return 'user/modals/signout.html'

    def get(self, request, *args, **kwargs):
        return self.modal_response(request, context={})

    def post(self, request, *args, **kwargs):
        from django.contrib.auth import logout
        logout(request)
        redirect_url = reverse('user_signin')
        return self.redirect_response(request, redirect_url)


class AccountHomeView(LoginRequiredMixin, View):

    def get(self, request, *args, **kwargs):
        account_page_context = AccountPageContext(
            active_page = AccountPageType.PROFILE,
        )
        form = forms.ProfileEditForm(initial={
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
        })
        profile_updated = request.GET.get('updated') == '1'
        context = {
            'account_page': account_page_context,
            'user': request.user,
            'form': form,
            'profile_updated': profile_updated,
        }
        return render(request, 'user/pages/account_home.html', context)

    def post(self, request, *args, **kwargs):
        form = forms.ProfileEditForm(request.POST)

        if form.is_valid():
            request.user.first_name = form.cleaned_data['first_name']
            request.user.last_name = form.cleaned_data['last_name']
            request.user.save()
            return HttpResponseRedirect(reverse('user_account_home') + '?updated=1')

        account_page_context = AccountPageContext(
            active_page = AccountPageType.PROFILE,
        )
        context = {
            'account_page': account_page_context,
            'user': request.user,
            'form': form,
        }
        return render(request, 'user/pages/account_home.html', context)


class APITokenManagementView( LoginRequiredMixin, View ):

    def get( self, request, *args, **kwargs ):
        account_page_context = AccountPageContext(
            active_page = AccountPageType.API_TOKENS,
        )
        api_token_list = APITokenService.list_tokens( request.user, TokenType.STANDARD )
        context = {
            'account_page': account_page_context,
            'user': request.user,
            'api_token_list': api_token_list,
        }
        return render( request, 'user/pages/api_tokens.html', context )


class APITokenCreateModalView(LoginRequiredMixin, ModalView):

    def get_template_name(self) -> str:
        return 'user/modals/api_token_create.html'

    def get(self, request, *args, **kwargs):
        form = forms.APITokenCreateForm()
        context = {
            'form': form,
        }
        return self.modal_response( request, context = context )

    @rate_limit( 'api_token_ops', limit = 100, period_secs = 3600 )
    def post(self, request, *args, **kwargs):
        from tt.apps.api.messages import APIMessages

        form = forms.APITokenCreateForm( request.POST )

        # Check token limit before processing form
        if not APITokenService.can_create_token( request.user ):
            form.add_error( None, APIMessages.TOKEN_LIMIT_REACHED )
            context = {
                'form': form,
            }
            return self.modal_response( request, context = context, status = 400 )

        if form.is_valid():
            api_token_data = APITokenService.create_token(
                user = request.user,
                api_token_name = form.cleaned_data['name'],
            )
            context = {
                'new_api_token_str': api_token_data.api_token_str,
            }
            return self.modal_response(
                request,
                context = context,
                template_name = 'user/modals/api_token_created.html',
            )

        context = {
            'form': form,
        }
        return self.modal_response(request, context=context, status=400)


class APITokenDeleteModalView( LoginRequiredMixin, ModalView ):

    def get_template_name( self ) -> str:
        return 'user/modals/api_token_delete.html'

    def get( self, request, lookup_key: str, *args, **kwargs ):
        api_token, error = APITokenService.get_token_by_lookup_key( request.user, lookup_key )
        if error:
            if error == 'Token not found':
                raise Http404( error )
            context = { 'error_message': error }
            return self.modal_response( request, context = context, status = 400 )

        context = { 'api_token': api_token }
        return self.modal_response( request, context = context )

    @rate_limit( 'api_token_ops', limit = 100, period_secs = 3600 )
    def post( self, request, lookup_key: str, *args, **kwargs ):
        success, error = APITokenService.delete_token( request.user, lookup_key )
        if not success:
            if error == 'Token not found':
                raise Http404( error )
            context = { 'error_message': error }
            return self.modal_response( request, context = context, status = 400 )

        return self.refresh_response( request )


class APITokenExtensionDisconnectModalView( APITokenDeleteModalView ):

    def get_template_name( self ) -> str:
        return 'user/modals/api_token_extension_disconnect.html'


class ExtensionsHomeView( LoginRequiredMixin, View ):
    """
    Extensions management page - shows extension tokens and authorization options.

    GET: Displays the extensions page with current status.
    POST: Creates a new extension token (via antinode.js async form).
    """

    def get(self, request, *args, **kwargs):
        context = self._get_template_context( request )
        return render( request, 'user/pages/extensions.html', context )

    def post(self, request, *args, **kwargs):
        # Get platform from form data (optional, for token naming)
        platform = request.POST.get( 'platform', None ) or None

        # Create the extension token
        token_data = ExtensionTokenService.create_extension_token(
            user = request.user,
            platform = platform,
        )
        context = self._get_template_context( request )        
        context.update({
            'token_str': token_data.api_token_str,
            'token_name': token_data.api_token.name,
        })

        auth_result_template = get_template( 'user/components/extension_authorize_result.html' )
        auth_result_html = auth_result_template.render( context, request = request )
        token_table_template = get_template( 'user/components/api_token_table_extension.html' )
        token_table_html = token_table_template.render( context, request = request )
        
        return antinode.response(
            insert_map = {
                TtConst.EXT_AUTH_RESULT_ID:auth_result_html,
                TtConst.EXT_API_TOKEN_TABLE_ID: token_table_html,
            },
        )

    def _get_template_context( self, request ):
        account_page_context = AccountPageContext(
            active_page = AccountPageType.EXTENSIONS,
        )
        api_token_list = ExtensionTokenService.get_extension_tokens( request.user )
        return {
            'account_page': account_page_context,
            'user': request.user,
            'api_token_list': api_token_list,
        }
 
