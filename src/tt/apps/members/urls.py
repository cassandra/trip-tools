from django.urls import path

from . import views


urlpatterns = [
    path(
        r'trip/<uuid:trip_uuid>',
        views.MemberListView.as_view(),
        name = 'members_list'
    ),
    path(
        r'trip/<uuid:trip_uuid>/invite',
        views.MemberInviteModalView.as_view(),
        name = 'members_invite'
    ),
    path(
        r'trip/<uuid:trip_uuid>/permission/<uuid:member_uuid>',
        views.MemberPermissionChangeView.as_view(),
        name = 'members_change_permission'
    ),
    path(
        r'trip/<uuid:trip_uuid>/remove/<uuid:member_uuid>',
        views.MemberRemoveModalView.as_view(),
        name = 'members_remove'
    ),
    path(
        r'trip/<uuid:trip_uuid>/accept/<str:email>/<str:token>',
        views.MemberAcceptInvitationView.as_view(),
        name = 'members_accept_invitation'
    ),
    path(
        r'trip/<uuid:trip_uuid>/signup/<str:email>/<str:token>',
        views.MemberSignupAndAcceptView.as_view(),
        name = 'members_signup_and_accept'
    ),
]
