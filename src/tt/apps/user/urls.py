from django.urls import path, re_path

from . import views


urlpatterns = [

    path(
        'signin',
        views.UserSigninView.as_view(),
        name='user_signin'
    ),
    path(
        'signin/reviewer',
        views.PasswordSigninView.as_view(),
        name='user_signin_password'
    ),
    path(
        'signin/magic/code',
        views.SigninMagicCodeView.as_view(),
        name='user_signin_magic_code'
    ),
    # Magic link uses re_path because email can contain special characters
    re_path(
        r'^signin/magic/link/(?P<token>[\w\-]+)/(?P<email>.+)$',
        views.SigninMagicLinkView.as_view(),
        name='user_signin_magic_link'
    ),
    path(
        'signout',
        views.UserSignoutView.as_view(),
        name='user_signout'
    ),
    path(
        'account',
        views.AccountHomeView.as_view(),
        name='user_account_home'
    ),
    path(
        'api-keys',
        views.APITokenManagementView.as_view(),
        name='user_api_tokens'
    ),
    path(
        'api-keys/create',
        views.APITokenCreateModalView.as_view(),
        name='user_api_token_create'
    ),
    path(
        'api-keys/<str:lookup_key>/delete',
        views.APITokenDeleteModalView.as_view(),
        name='user_api_token_delete'
    ),
    path(
        'api-keys/<str:lookup_key>/extension-disconnect',
        views.APITokenExtensionDisconnectModalView.as_view(),
        name='user_api_token_extension_disconnect'
    ),
    path(
        'extensions/',
        views.ExtensionsHomeView.as_view(),
        name='user_extensions'
    ),
]
