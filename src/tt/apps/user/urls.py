from django.urls import re_path

from . import views


urlpatterns = [

    re_path( r'^signin$',
             views.UserSigninView.as_view(),
             name='user_signin'),

    re_path( r"^signin/magic/code$",
             views.SigninMagicCodeView.as_view(),
             name="user_signin_magic_code"),

    re_path( r"^signin/magic/link/(?P<token>[\w\-]+)/(?P<email>.+)$",
             views.SigninMagicLinkView.as_view(),
             name="user_signin_magic_link"),

    re_path( r'^signout$',
             views.UserSignoutView.as_view(),
             name='user_signout'),

    re_path( r'^account$',
             views.AccountHomeView.as_view(),
             name='user_account_home'),

    re_path( r'^api-keys$',
             views.APIKeyManagementView.as_view(),
             name='user_api_keys'),

    re_path( r'^api-keys/create$',
             views.APIKeyCreateModalView.as_view(),
             name='user_api_key_create'),

    re_path( r'^api-keys/(?P<api_key_id>\d+)/delete$',
             views.APIKeyDeleteModalView.as_view(),
             name='user_api_key_delete'),
]
