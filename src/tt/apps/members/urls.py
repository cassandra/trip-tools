from django.urls import re_path

from . import views


urlpatterns = [
    re_path(
        r'^trip/(?P<trip_id>\d+)/members$',
        views.MemberListView.as_view(),
        name = 'members_list'
    ),
    re_path(
        r'^trip/(?P<trip_id>\d+)/members/invite$',
        views.MemberInviteModalView.as_view(),
        name = 'members_invite'
    ),
    re_path(
        r'^trip/(?P<trip_id>\d+)/members/(?P<member_id>\d+)/permission$',
        views.MemberPermissionModalView.as_view(),
        name = 'members_change_permission'
    ),
    re_path(
        r'^trip/(?P<trip_id>\d+)/members/(?P<member_id>\d+)/remove$',
        views.MemberRemoveModalView.as_view(),
        name = 'members_remove'
    ),
    re_path(
        r'^trip/(?P<trip_id>\d+)/members/accept/(?P<email>[^/]+)/(?P<token>[^/]+)$',
        views.MemberAcceptInvitationView.as_view(),
        name = 'members_accept_invitation'
    ),
    re_path(
        r'^trip/(?P<trip_id>\d+)/members/signup/(?P<email>[^/]+)/(?P<token>[^/]+)$',
        views.MemberSignupAndAcceptView.as_view(),
        name = 'members_signup_and_accept'
    ),
]
