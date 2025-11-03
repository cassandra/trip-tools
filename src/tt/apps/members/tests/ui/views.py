from typing import Dict

from django.shortcuts import render
from django.views.generic import View

from tt.testing.ui.email_test_views import EmailTestViewView


class TestUiMembersHomeView( View ):

    def get(self, request, *args, **kwargs):
        context = {
        }
        return render(request, "members/tests/ui/home.html", context )


class TestUiViewInvitationEmailView( EmailTestViewView ):

    @property
    def app_name(self):
        return 'members'

    def get_extra_context( self, email_type : str ) -> Dict[ str, object ]:
        context = {
            'invited_by_name': 'John Smith',
            'trip_title': 'Summer Road Trip 2025',
            'trip_description': 'A two-week adventure through the Pacific Northwest, visiting national parks and scenic coastal towns.',
        }

        if email_type == 'invitation':
            context['acceptance_url'] = 'https://example.com/members/accept/123/user@example.com/abc123token'
        elif email_type == 'signup_invitation':
            context['signup_url'] = 'https://example.com/members/signup/123/user@example.com/abc123token'

        return context


class TestUiWelcomePageView( View ):
    """Visual testing for the welcome page shown to new users after accepting invitation."""

    def get(self, request, *args, **kwargs):
        # Mock trip and user data for visual testing
        class MockTrip:
            pk = 123
            title = 'Summer Road Trip 2025'
            description = 'A two-week adventure through the Pacific Northwest, visiting national parks and scenic coastal towns.'

        class MockUser:
            email = 'user@example.com'

        context = {
            'trip': MockTrip(),
            'user': MockUser(),
        }
        return render(request, 'members/pages/welcome.html', context)
