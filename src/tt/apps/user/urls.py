from django.urls import path, re_path

from . import views


urlpatterns = [

    path(
        'signin',
        views.UserSigninView.as_view(),
        name='user_signin'
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
        views.APIKeyManagementView.as_view(),
        name='user_api_keys'
    ),
    path(
        'api-keys/create',
        views.APIKeyCreateModalView.as_view(),
        name='user_api_key_create'
    ),
    path(
        'api-keys/<int:api_key_id>/delete',
        views.APIKeyDeleteModalView.as_view(),
        name='user_api_key_delete'
    ),
    path(
        'extensions/',
        views.ExtensionsHomeView.as_view(),
        name='user_extensions'
    ),
    path(
        'extensions/authorize/',
        views.ExtensionAuthorizeView.as_view(),
        name='user_extension_authorize'
    ),
]
