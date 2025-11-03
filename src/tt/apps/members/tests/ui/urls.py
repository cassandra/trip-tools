from django.urls import re_path

from . import views


urlpatterns = [

    re_path( r'^$',
             views.TestUiMembersHomeView.as_view(),
             name='members_tests_ui'),

    re_path( r'^email/invitation/view/(?P<email_type>\w+)$',
             views.TestUiViewInvitationEmailView.as_view(),
             name='members_tests_ui_view_invitation_email'),

    re_path( r'^page/welcome$',
             views.TestUiWelcomePageView.as_view(),
             name='members_tests_ui_view_welcome_page'),
]
