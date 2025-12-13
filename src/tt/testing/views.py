from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views.generic import View

from tt.apps.user.signin_manager import SigninManager


class TestingHomeView( View ):

    def get( self, request, *args, **kwargs ):
        return render( request, 'testing/pages/testing_home.html' )


class E2ESigninForm( forms.Form ):
    """Form for E2E test signin with email and password."""
    email = forms.EmailField()
    password = forms.CharField( widget=forms.PasswordInput )


class E2ESigninView( View ):
    """
    Test-only signin endpoint for E2E testing.

    This view only exists when DEBUG=True (tt.testing app installed).
    It allows logging in with email + a shared test password, bypassing
    the magic code email flow for automated testing.
    """

    TEMPLATE_NAME = 'testing/pages/e2e_signin.html'

    def get( self, request, *args, **kwargs ):
        form = E2ESigninForm()
        return render( request, self.TEMPLATE_NAME, { 'form': form } )

    def post( self, request, *args, **kwargs ):
        form = E2ESigninForm( request.POST )
        if not form.is_valid():
            return render( request, self.TEMPLATE_NAME, { 'form': form }, status=400 )

        email = form.cleaned_data['email']
        password = form.cleaned_data['password']

        # Verify the test password
        expected_password = getattr( settings, 'E2E_TEST_PASSWORD', None )
        if not expected_password or password != expected_password:
            form.add_error( 'password', 'Invalid test password' )
            return render( request, self.TEMPLATE_NAME, { 'form': form }, status=403 )

        # Get the user
        User = get_user_model()
        try:
            user = User.objects.get( email=email )
        except User.DoesNotExist:
            form.add_error( 'email', 'User not found' )
            return render( request, self.TEMPLATE_NAME, { 'form': form }, status=404 )

        # Log them in
        request.user = user
        SigninManager().do_login( request=request, verified_email=True )

        return HttpResponseRedirect( reverse( 'dashboard_home' ) )
