import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User as UserType
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.exceptions import BadRequest, ValidationError
from django.core.validators import validate_email
from django.http import HttpRequest, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.generic import View

from tt.apps.api.models import APIToken
from tt.apps.api.services import APITokenService
from tt.apps.notify.email_sender import EmailSender
from tt.async_view import ModalView

from . import forms
from .context import AccountPageContext
from .enums import AccountPageType, SigninErrorType
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


class UserSignoutView(View):

    def get(self, request, *args, **kwargs):
        from django.contrib.auth import logout
        logout(request)
        return HttpResponseRedirect( reverse('user_signin') )


class AccountHomeView(LoginRequiredMixin, View):

    def get(self, request, *args, **kwargs):
        account_page_context = AccountPageContext(
            active_page = AccountPageType.PROFILE,
        )
        context = {
            'account_page': account_page_context,
            'user': request.user,
        }
        return render(request, 'user/pages/account_home.html', context)


class APIKeyManagementView(LoginRequiredMixin, View):

    def get(self, request, *args, **kwargs):
        account_page_context = AccountPageContext(
            active_page = AccountPageType.API_KEYS,
        )
        api_keys = APIToken.objects.filter(user=request.user).order_by('-created_at')

        # Check if we have a newly created key to display
        new_api_key_str = request.session.pop('new_api_key_str', None)

        context = {
            'account_page': account_page_context,
            'user': request.user,
            'api_keys': api_keys,
            'new_api_key_str': new_api_key_str,
        }
        return render(request, 'user/pages/api_keys.html', context)


class APIKeyCreateModalView(LoginRequiredMixin, ModalView):

    def get_template_name(self) -> str:
        return 'user/modals/api_key_create.html'

    def get(self, request, *args, **kwargs):
        form = forms.APIKeyCreateForm()
        context = {
            'form': form,
        }
        return self.modal_response(request, context=context)

    def post(self, request, *args, **kwargs):
        form = forms.APIKeyCreateForm(request.POST)

        if form.is_valid():
            api_token_data = APITokenService.create_token(
                user = request.user,
                api_token_name = form.cleaned_data['name'],
            )
            # Store the token string in session for one-time display
            request.session['new_api_key_str'] = api_token_data.api_token_str
            redirect_url = reverse('user_api_keys')
            return self.redirect_response(request, redirect_url)

        context = {
            'form': form,
        }
        return self.modal_response(request, context=context, status=400)


class APIKeyDeleteModalView(LoginRequiredMixin, ModalView):

    def get_template_name(self) -> str:
        return 'user/modals/api_key_delete.html'

    def get(self, request, api_key_id: int, *args, **kwargs):
        api_key = get_object_or_404(
            APIToken,
            id = api_key_id,
            user = request.user,
        )
        context = {
            'api_key': api_key,
        }
        return self.modal_response(request, context=context)

    def post(self, request, api_key_id: int, *args, **kwargs):
        api_key = get_object_or_404(
            APIToken,
            id = api_key_id,
            user = request.user,
        )
        api_key.delete()
        redirect_url = reverse('user_api_keys')
        return self.redirect_response(request, redirect_url)

