import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.db import transaction
from django.http import HttpRequest
from django.urls import reverse

from tt.apps.common.singleton import Singleton
from tt.apps.notify.email_sender import EmailData, EmailSender
from tt.apps.trips.enums import TripPermissionLevel
from tt.apps.trips.models import Trip

from .models import TripMember
from .schemas import InviteMemberResultData

User = get_user_model()
logger = logging.getLogger(__name__)


class MemberInvitationManager( Singleton ):
    """
    Manages member invitation workflow including email sending and acceptance.

    Handles two scenarios:
    1. Existing users - sends invitation email with direct acceptance link
    2. New users - creates User record with email_verified=False, sends signup link
    """

    INVITATION_SUBJECT_TEMPLATE_NAME = 'members/emails/invitation_subject.txt'
    INVITATION_MESSAGE_TEXT_TEMPLATE_NAME = 'members/emails/invitation_message.txt'
    INVITATION_MESSAGE_HTML_TEMPLATE_NAME = 'members/emails/invitation_message.html'

    SIGNUP_SUBJECT_TEMPLATE_NAME = 'members/emails/signup_invitation_subject.txt'
    SIGNUP_MESSAGE_TEXT_TEMPLATE_NAME = 'members/emails/signup_invitation_message.txt'
    SIGNUP_MESSAGE_HTML_TEMPLATE_NAME = 'members/emails/signup_invitation_message.html'

    def __init_singleton__(self):
        self._token_generator = PasswordResetTokenGenerator()
        return

    def invite_member( self,
                       request           : HttpRequest,
                       trip              : Trip,
                       email             : str,
                       permission_level  : TripPermissionLevel,
                       invited_by_user   : User,
                       send_email        : bool = True ) -> InviteMemberResultData:
        """
        Invite a member to a trip. Creates user if needed and optionally sends invitation email.
        """
        email = email.lower().strip()

        try:
            user = User.objects.get( email = email )
            new_user_created = False
            logger.debug( f'Inviting existing user {email} to trip {trip.pk}' )
        except User.DoesNotExist:
            new_user_created = True
            logger.debug( f'Will create new user {email} for trip invitation' )
            user = None

        with transaction.atomic():
            # Create user inside transaction if needed
            if new_user_created:
                first_name = email.split('@')[0].strip()
                user = User.objects.create(
                    email = email,
                    first_name = first_name,
                    email_verified = False,
                    is_active = True,
                )

            trip_member, created = TripMember.objects.get_or_create(
                trip = trip,
                user = user,
                defaults = {
                    'permission_level': permission_level,
                    'added_by': invited_by_user,
                }
            )

            if not created:
                trip_member.permission_level = permission_level
                trip_member.added_by = invited_by_user
                trip_member.save()

        if send_email:
            if new_user_created:
                self._send_signup_invitation_email(
                    request = request,
                    trip = trip,
                    user = user,
                    invited_by_user = invited_by_user,
                )
            else:
                self._send_invitation_email(
                    request = request,
                    trip = trip,
                    user = user,
                    invited_by_user = invited_by_user,
                )
            
        return InviteMemberResultData(
            trip_member = trip_member,
            new_user_created = new_user_created,
        )

    def _send_invitation_email( self,
                                request          : HttpRequest,
                                trip             : Trip,
                                user             : User,
                                invited_by_user  : User ) -> None:
        """Send invitation email to existing verified user."""

        token = self._token_generator.make_token( user )
        acceptance_url = request.build_absolute_uri(
            reverse( 'members_accept_invitation',
                     kwargs = {
                         'trip_uuid': trip.uuid,
                         'email': user.email,
                         'token': token,
                     })
        )

        email_template_context = {
            'trip_title': trip.title,
            'trip_description': trip.description,
            'invited_by_name': invited_by_user.get_full_name() or invited_by_user.email,
            'acceptance_url': acceptance_url,
        }

        email_sender_data = EmailData(
            request = request,
            subject_template_name = self.INVITATION_SUBJECT_TEMPLATE_NAME,
            message_text_template_name = self.INVITATION_MESSAGE_TEXT_TEMPLATE_NAME,
            message_html_template_name = self.INVITATION_MESSAGE_HTML_TEMPLATE_NAME,
            to_email_address = user.email,
            template_context = email_template_context,
            non_blocking = True,
        )

        email_sender = EmailSender( data = email_sender_data )
        email_sender.send()
        logger.debug( f'Sent invitation email to {user.email} for trip {trip.pk}' )
        return

    def _send_signup_invitation_email( self,
                                       request          : HttpRequest,
                                       trip             : Trip,
                                       user             : User,
                                       invited_by_user  : User ) -> None:
        """Send signup invitation email to new or unverified user."""

        token = self._token_generator.make_token( user )
        signin_url = request.build_absolute_uri(
            reverse( 'members_signup_and_accept',
                     kwargs = {
                         'trip_uuid': trip.uuid,
                         'email': user.email,
                         'token': token,
                     })
        )

        email_template_context = {
            'trip_title': trip.title,
            'trip_description': trip.description,
            'invited_by_name': invited_by_user.get_full_name() or invited_by_user.email,
            'signin_url': signin_url,
        }

        email_sender_data = EmailData(
            request = request,
            subject_template_name = self.SIGNUP_SUBJECT_TEMPLATE_NAME,
            message_text_template_name = self.SIGNUP_MESSAGE_TEXT_TEMPLATE_NAME,
            message_html_template_name = self.SIGNUP_MESSAGE_HTML_TEMPLATE_NAME,
            to_email_address = user.email,
            template_context = email_template_context,
            non_blocking = True,
        )

        email_sender = EmailSender( data = email_sender_data )
        email_sender.send()
        logger.debug( f'Sent signup invitation email to {user.email} for trip {trip.pk}' )
        return

    def verify_invitation_token( self, user, token : str, trip = None ) -> bool:
        """
        Verify that the invitation token is valid for the given user.

        Also checks one-time use: if trip is provided, verifies the invitation hasn't been accepted yet.
        """
        # First check the token itself
        if not self._token_generator.check_token( user = user, token = token ):
            return False

        # If trip provided, check if invitation has already been accepted (one-time use)
        if trip:
            try:
                member = TripMember.objects.get( trip = trip, user = user )
                # If invitation was already accepted, token is no longer valid
                if member.invitation_accepted_datetime is not None:
                    return False
            except TripMember.DoesNotExist:
                # Member doesn't exist yet - token is valid
                pass

        return True
