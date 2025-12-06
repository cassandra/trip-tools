import logging

from django.contrib.auth.models import User as UserType
from django.http import HttpRequest
from django.urls import reverse

from tt.apps.common.singleton import Singleton
from tt.apps.notify.email_sender import EmailData, EmailSender

logger = logging.getLogger(__name__)


class UserInvitationManager(Singleton):
    """
    Sends welcome/invitation emails to users.

    Used by Django Admin to invite new users to the application.
    Decoupled from user creation to allow re-sending invitations.
    """

    WELCOME_SUBJECT_TEMPLATE = 'user/emails/welcome_invitation_subject.txt'
    WELCOME_TEXT_TEMPLATE = 'user/emails/welcome_invitation_message.txt'
    WELCOME_HTML_TEMPLATE = 'user/emails/welcome_invitation_message.html'

    def send_welcome_email( self,
                            request          : HttpRequest,
                            user             : UserType,
                            invited_by_name  : str = '') -> None:
        if not user.email:
            logger.warning(f'Cannot send welcome email to user {user.pk} - no email address')
            return

        signin_url = request.build_absolute_uri( reverse('user_signin') )

        email_template_context = {
            'user_first_name': user.first_name or user.email.split('@')[0],
            'invited_by_name': invited_by_name,
            'signin_url': signin_url,
        }

        email_sender_data = EmailData(
            request = request,
            subject_template_name = self.WELCOME_SUBJECT_TEMPLATE,
            message_text_template_name = self.WELCOME_TEXT_TEMPLATE,
            message_html_template_name = self.WELCOME_HTML_TEMPLATE,
            to_email_address = user.email,
            template_context = email_template_context,
            non_blocking = True,
        )

        email_sender = EmailSender( data = email_sender_data )
        email_sender.send()
        logger.info(f'Sent welcome invitation email to {user.email}')
