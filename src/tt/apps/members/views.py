import logging
from uuid import UUID

from django.contrib.auth import get_user_model, login as django_login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import BadRequest, PermissionDenied
from django.db import transaction
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.generic import View

from tt.async_view import ModalView
from tt.apps.trips.context import TripPageContext
from tt.apps.trips.enums import TripPage, TripPermissionLevel
from tt.apps.trips.helpers import TripHelpers
from tt.apps.trips.mixins import TripViewMixin
from tt.apps.trips.models import Trip
from tt.apps.user.enums import SigninErrorType

from .forms import MemberInviteForm, MemberPermissionForm, MemberRemoveForm
from .invitation_manager import MemberInvitationManager
from .models import TripMember

User = get_user_model()
logger = logging.getLogger(__name__)

INVALID_INVITATION_MESSAGE = 'This invitation link is invalid or has expired.'


class MembersHomeView( LoginRequiredMixin, TripViewMixin, View ):

    def get(self, request, trip_uuid: UUID, *args, **kwargs) -> HttpResponse:
        request_member = self.get_trip_member( request, trip_uuid = trip_uuid )
        self.assert_is_viewer( request_member )
        trip = request_member.trip
        
        all_members = trip.members.select_related( 'user', 'added_by' ).all()
        member_data_list = list()
        for target_member in all_members:
            member_data = TripHelpers.create_trip_member_data( 
                request_member = request_member ,
                target_member = target_member,
            )
            member_data_list.append( member_data )
            continue

        trip_page_context = TripPageContext(
            active_page = TripPage.MEMBERS,
            request_member = request_member,
        )
        context = {
            'trip_page': trip_page_context,
            'request_member': request_member,
            'member_data_list': member_data_list,
        }

        return render( request, 'members/pages/members_home.html', context )


class MemberInviteModalView( LoginRequiredMixin, TripViewMixin, ModalView ):
    def get_template_name(self) -> str:
        return 'members/modals/invite.html'

    def get(self, request, trip_uuid: UUID, *args, **kwargs) -> HttpResponse:
        request_member = self.get_trip_member( request, trip_uuid = trip_uuid )
        self.assert_is_admin( request_member )
        trip = request_member.trip

        form = MemberInviteForm( trip = trip )
        context = {
            'form': form,
            'trip': trip,
        }
        return self.modal_response( request, context = context )

    def post(self, request, trip_uuid: UUID, *args, **kwargs) -> HttpResponse:
        request_member = self.get_trip_member( request, trip_uuid = trip_uuid )
        self.assert_is_admin( request_member )
        trip = request_member.trip

        form = MemberInviteForm( request.POST, trip = trip )

        if form.is_valid():
            email = form.cleaned_data['email']
            permission_level = form.cleaned_data['permission_level']
            send_email = form.cleaned_data.get( 'send_email', True )

            if permission_level > request_member.permission_level:
                form.add_error(
                    'permission_level',
                    'You cannot grant a permission level higher than your own.'
                )
            else:
                try:
                    invitation_manager = MemberInvitationManager()
                    invitation_manager.invite_member(
                        request = request,
                        trip = trip,
                        email = email,
                        permission_level = permission_level,
                        invited_by_user = request.user,
                        send_email = send_email,
                    )

                    return self.refresh_response( request )

                except Exception as e:
                    logger.error( f'Error inviting member: {e}', exc_info = True )
                    form.add_error( None, 'An error occurred while inviting the member.' )

        context = {
            'form': form,
            'trip': trip,
        }
        return self.modal_response( request, context = context, status = 400 )


class MemberPermissionChangeView( LoginRequiredMixin, TripViewMixin, View ):

    def post(self, request, trip_uuid: UUID, member_uuid: UUID, *args, **kwargs) -> HttpResponse:
        request_member = self.get_trip_member( request, trip_uuid = trip_uuid )
        self.assert_is_admin( request_member )
        trip = request_member.trip
    
        target_member = get_object_or_404( TripMember, uuid = member_uuid, trip = trip )

        if target_member.permission_level > request_member.permission_level:
            raise PermissionDenied( 'Cannot modify a member with higher permissions than your own' )

        form = MemberPermissionForm( request.POST, member = target_member )
        if not form.is_valid():
            raise BadRequest( 'Invalid permission level selected.' )
            
        new_permission_level = form.cleaned_data['permission_level']
        if new_permission_level > request_member.permission_level:
            raise BadRequest( 'You cannot grant a permission level higher than your own.' )

        with transaction.atomic():
            # If demoting from OWNER, verify another owner exists
            if (( target_member.permission_level == TripPermissionLevel.OWNER )
                and ( new_permission_level != TripPermissionLevel.OWNER )):
                owner_count = trip.members.select_for_update().filter(
                    permission_level = TripPermissionLevel.OWNER
                ).exclude( pk = target_member.pk ).count()
                if owner_count < 1:
                    raise BadRequest( 'Cannot demote the last owner. Promote another owner first.' )

            target_member.permission_level = new_permission_level
            target_member.save()

        logger.debug(
            f'User {request.user.email} changed permission for {target_member.user.email} '
            f'to {new_permission_level.label} on trip {trip.pk}'
        )

        member_data = TripHelpers.create_trip_member_data( 
            request_member = request_member ,
            target_member = target_member,
        )
        context = {
            'request_member': request_member,
            'member_data': member_data,
        }
        return render( request, 'members/components/member_card.html', context )


class MemberRemoveModalView( LoginRequiredMixin, TripViewMixin, ModalView ):

    def get_template_name(self) -> str:
        return 'members/modals/remove.html'

    def get(self, request, trip_uuid: UUID, member_uuid: UUID, *args, **kwargs) -> HttpResponse:
        request_member = self.get_trip_member( request, trip_uuid = trip_uuid )
        trip = request_member.trip

        target_member = get_object_or_404( TripMember, uuid = member_uuid, trip = trip )
        is_self_removal = bool( request_member.user == target_member.user )

        if not is_self_removal:
            self.assert_is_admin( trip_member = request_member )
            if target_member.permission_level > request_member.permission_level:
                raise PermissionDenied( 'Cannot remove a member with higher permissions than your own' )

        if target_member.permission_level == TripPermissionLevel.OWNER:
            owner_count = trip.members.filter(
                permission_level = TripPermissionLevel.OWNER
            ).count()
            if owner_count <= 1:
                raise BadRequest(
                    'Cannot remove the last owner. Add another owner first.'
                )

        form = MemberRemoveForm( member = target_member, is_self_removal = is_self_removal )

        context = {
            'form': form,
            'trip': trip,
            'member': target_member,
            'is_self_removal': is_self_removal,
        }
        return self.modal_response( request, context = context )

    def post(self, request, trip_uuid: UUID, member_uuid: UUID, *args, **kwargs) -> HttpResponse:
        request_member = self.get_trip_member( request, trip_uuid = trip_uuid )
        trip = request_member.trip

        target_member = get_object_or_404( TripMember, uuid = member_uuid, trip = trip )
        is_self_removal = bool( request_member.user == target_member.user )

        if not is_self_removal:
            self.assert_is_admin( trip_member = request_member )
            if target_member.permission_level > request_member.permission_level:
                raise PermissionDenied( 'Cannot remove a member with higher permissions than your own' )

        form = MemberRemoveForm( request.POST, member = target_member, is_self_removal = is_self_removal )

        if form.is_valid():
            with transaction.atomic():
                # Re-check owner count inside transaction with row locking to prevent race conditions
                if target_member.permission_level == TripPermissionLevel.OWNER:
                    owner_count = trip.members.select_for_update().filter(
                        permission_level = TripPermissionLevel.OWNER
                    ).count()
                    if owner_count <= 1:
                        raise BadRequest(
                            'Cannot remove the last owner. Add another owner first.'
                        )

                target_member.delete()

            logger.info(
                f'User {request.user.email} removed {target_member.user.email} '
                f'from trip {trip.pk} (self_removal={is_self_removal})'
            )

            if is_self_removal:
                return self.redirect_response( request, reverse( 'dashboard_home' ) )

            return self.refresh_response( request )

        context = {
            'form': form,
            'trip': trip,
            'member': target_member,
            'is_self_removal': is_self_removal,
        }

        return self.modal_response( request, context = context, status = 400 )


class MemberAcceptInvitationView( View ):
    """Accept invitation link for existing verified users."""

    def get(self, request, trip_uuid: UUID, email: str, token: str, *args, **kwargs) -> HttpResponse:
        from django.utils import timezone

        trip = get_object_or_404( Trip, uuid = trip_uuid )

        try:
            user = User.objects.get( email = email )
        except User.DoesNotExist:
            raise Http404( 'Invalid invitation link' )

        # Check if user is logged in as different user (security check)
        if request.user.is_authenticated and request.user.email != email:
            logger.warning(
                f'User {request.user.email} attempted to accept invitation for {email} '
                f'on trip {trip.pk}'
            )
            context = {
                'invited_email': email,
                'current_email': request.user.email,
                'trip': trip,
            }
            return render( request, 'members/pages/wrong_user_invitation.html', context, status = 403 )

        # Verify token with one-time use check
        invitation_manager = MemberInvitationManager()
        is_valid = invitation_manager.verify_invitation_token( user = user, token = token, trip = trip )

        if not is_valid:
            # If logged in as correct user and already accepted, just go to trip
            if request.user.is_authenticated and request.user.email == email:
                try:
                    member = TripMember.objects.get( trip = trip, user = user )
                    if member.invitation_accepted_datetime is not None:
                        # Already accepted - redirect to trip
                        return HttpResponseRedirect( reverse( 'trips_home',
                                                              kwargs = { 'trip_uuid': trip.uuid } ) )
                except TripMember.DoesNotExist:
                    pass

            # Redirect to signin with error message for expired/used tokens
            signin_url = reverse( 'user_signin' ) + f'?error={SigninErrorType.INVITATION_EXPIRED}'
            return HttpResponseRedirect( signin_url )

        # Log user in if not authenticated
        if not request.user.is_authenticated:
            request.user = user
            django_login( request, user )

        # Mark email as verified and invitation as accepted in single transaction
        with transaction.atomic():
            # Mark email as verified (clicking email link proves they have access to the email)
            if not user.email_verified:
                user.email_verified = True
                user.save()
                logger.info( f'Verified email for {user.email} via invitation link' )

            # Mark invitation as accepted (one-time use)
            try:
                member = TripMember.objects.get( trip = trip, user = user )
                member.invitation_accepted_datetime = timezone.now()
                member.save()
                logger.info( f'User {user.email} accepted invitation to trip {trip.pk}' )
            except TripMember.DoesNotExist:
                logger.warning( f'User {user.email} has no membership for trip {trip.pk}' )

        return HttpResponseRedirect( reverse( 'trips_home', kwargs = { 'trip_uuid': trip.uuid } ) )


class MemberSignupAndAcceptView( View ):
    """Signup and accept invitation link for new/unverified users."""

    def get(self, request, trip_uuid: UUID, email: str, token: str, *args, **kwargs) -> HttpResponse:
        from django.utils import timezone

        trip = get_object_or_404( Trip, uuid = trip_uuid )

        try:
            user = User.objects.get( email = email )
        except User.DoesNotExist:
            raise Http404( 'Invalid invitation link' )

        # Check if user is logged in as different user (security check)
        if request.user.is_authenticated and request.user.email != email:
            logger.warning(
                f'User {request.user.email} attempted to accept invitation for {email} '
                f'on trip {trip.pk}'
            )
            context = {
                'invited_email': email,
                'current_email': request.user.email,
                'trip': trip,
            }
            return render( request, 'members/pages/wrong_user_invitation.html', context, status = 403 )

        # Verify token with one-time use check
        invitation_manager = MemberInvitationManager()
        is_valid = invitation_manager.verify_invitation_token( user = user, token = token, trip = trip )

        if not is_valid:
            # If logged in as correct user and already accepted, just go to trip
            if request.user.is_authenticated and request.user.email == email:
                try:
                    member = TripMember.objects.get( trip = trip, user = user )
                    if member.invitation_accepted_datetime is not None:
                        # Already accepted - redirect to trip
                        return HttpResponseRedirect( reverse( 'trips_home',
                                                              kwargs = { 'trip_uuid': trip.uuid } ) )
                except TripMember.DoesNotExist:
                    pass

            # Redirect to signin with error message for expired/used tokens
            signin_url = reverse( 'user_signin' ) + f'?error={SigninErrorType.INVITATION_EXPIRED}'
            return HttpResponseRedirect( signin_url )

        # Log user in if not authenticated
        if not request.user.is_authenticated:
            request.user = user
            django_login( request, user )

        # Mark email as verified and invitation as accepted in single transaction
        with transaction.atomic():
            # Mark email as verified (clicking email link proves they have access to the email)
            if not user.email_verified:
                user.email_verified = True
                user.save()
                logger.info( f'Verified email for {user.email} via invitation link' )

            # Mark invitation as accepted (one-time use)
            try:
                member = TripMember.objects.get( trip = trip, user = user )
                member.invitation_accepted_datetime = timezone.now()
                member.save()
                logger.info( f'New user {user.email} signed up and accepted invitation to trip {trip.pk}' )
            except TripMember.DoesNotExist:
                logger.warning( f'User {user.email} has no membership for trip {trip.pk}' )

        context = {
            'trip': trip,
            'user': user,
        }

        return render( request, 'members/pages/welcome.html', context )
