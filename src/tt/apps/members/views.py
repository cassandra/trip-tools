import logging

from django.contrib.auth import get_user_model, login as django_login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import BadRequest
from django.db import transaction
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.generic import View

from tt.async_view import ModalView
from tt.apps.trips.context import TripPageContext
from tt.apps.trips.enums import TripPage, TripPermissionLevel
from tt.apps.trips.mixins import TripPermissionMixin
from tt.apps.trips.models import Trip, TripMember

from .forms import MemberInviteForm, MemberPermissionForm, MemberRemoveForm
from .invitation_manager import MemberInvitationManager

User = get_user_model()
logger = logging.getLogger(__name__)

# Error message constants
INVALID_INVITATION_MESSAGE = 'This invitation link is invalid or has expired.'


class MemberListView( LoginRequiredMixin, TripPermissionMixin, View ):
    def get(self, request, trip_id: int, *args, **kwargs) -> HttpResponse:
        trip = get_object_or_404( Trip, pk = trip_id )

        if not self.has_trip_permission( request.user, trip, TripPermissionLevel.VIEWER ):
            raise Http404( 'Trip not found' )

        user_permission = trip.get_user_permission( request.user )
        can_manage_members = self.has_trip_permission(
            request.user,
            trip,
            TripPermissionLevel.ADMIN
        )

        members = trip.members.select_related( 'user', 'added_by' ).all()

        user_permission_rank = self.PERMISSION_HIERARCHY.get( user_permission, 0 )
        for member in members:
            member.can_modify = bool(
                can_manage_members
                and self.PERMISSION_HIERARCHY.get( member.permission_level, 0 ) < user_permission_rank
            )
            continue

        is_owner = bool( user_permission == TripPermissionLevel.OWNER )

        trip_page_context = TripPageContext(
            trip = trip,
            active_page = TripPage.MEMBERS,
        )

        context = {
            'trip_page': trip_page_context,
            'members': members,
            'can_manage_members': can_manage_members,
            'is_owner': is_owner,
            'user_permission': user_permission,
        }

        return render( request, 'members/pages/list.html', context )


class MemberInviteModalView( LoginRequiredMixin, TripPermissionMixin, ModalView ):
    def get_template_name(self) -> str:
        return 'members/modals/invite.html'

    def get(self, request, trip_id: int, *args, **kwargs) -> HttpResponse:
        trip = get_object_or_404( Trip, pk = trip_id )

        if not self.has_trip_permission( request.user, trip, TripPermissionLevel.ADMIN ):
            raise Http404( 'Trip not found' )

        form = MemberInviteForm( trip = trip )

        context = {
            'form': form,
            'trip': trip,
        }

        return self.modal_response( request, context = context )

    def post(self, request, trip_id: int, *args, **kwargs) -> HttpResponse:
        trip = get_object_or_404( Trip, pk = trip_id )

        if not self.has_trip_permission( request.user, trip, TripPermissionLevel.ADMIN ):
            raise Http404( 'Trip not found' )

        form = MemberInviteForm( request.POST, trip = trip )

        if form.is_valid():
            email = form.cleaned_data['email']
            permission_level = form.cleaned_data['permission_level']

            user_permission = trip.get_user_permission( request.user )
            user_permission_rank = self.PERMISSION_HIERARCHY.get( user_permission, 0 )
            new_member_rank = self.PERMISSION_HIERARCHY.get( permission_level, 0 )

            if new_member_rank >= user_permission_rank:
                form.add_error(
                    'permission_level',
                    'You cannot grant a permission level equal to or higher than your own.'
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
                    )

                    return self.refresh_response( request )

                except Exception as e:
                    logger.error( f'Error inviting member: {e}', exc_info = True )
                    form.add_error( None, 'An error occurred while sending the invitation.' )

        context = {
            'form': form,
            'trip': trip,
        }

        return self.modal_response( request, context = context, status = 400 )


class MemberPermissionModalView( LoginRequiredMixin, TripPermissionMixin, ModalView ):
    def get_template_name(self) -> str:
        return 'members/modals/change_permission.html'

    def get(self, request, trip_id: int, member_id: int, *args, **kwargs) -> HttpResponse:
        trip = get_object_or_404( Trip, pk = trip_id )
        member = get_object_or_404( TripMember, pk = member_id, trip = trip )

        if not self.has_trip_permission( request.user, trip, TripPermissionLevel.ADMIN ):
            raise Http404( 'Trip not found' )

        user_permission = trip.get_user_permission( request.user )
        user_permission_rank = self.PERMISSION_HIERARCHY.get( user_permission, 0 )
        member_permission_rank = self.PERMISSION_HIERARCHY.get( member.permission_level, 0 )

        if member_permission_rank >= user_permission_rank:
            raise Http404( 'Cannot modify this member' )

        form = MemberPermissionForm( member = member )

        context = {
            'form': form,
            'trip': trip,
            'member': member,
            'user_permission_rank': user_permission_rank,
        }

        return self.modal_response( request, context = context )

    def post(self, request, trip_id: int, member_id: int, *args, **kwargs) -> HttpResponse:
        trip = get_object_or_404( Trip, pk = trip_id )
        member = get_object_or_404( TripMember, pk = member_id, trip = trip )

        if not self.has_trip_permission( request.user, trip, TripPermissionLevel.ADMIN ):
            raise Http404( 'Trip not found' )

        user_permission = trip.get_user_permission( request.user )
        user_permission_rank = self.PERMISSION_HIERARCHY.get( user_permission, 0 )
        member_permission_rank = self.PERMISSION_HIERARCHY.get( member.permission_level, 0 )

        if member_permission_rank >= user_permission_rank:
            raise Http404( 'Cannot modify this member' )

        form = MemberPermissionForm( request.POST, member = member )

        if form.is_valid():
            new_permission_level = form.cleaned_data['permission_level']
            new_permission_rank = self.PERMISSION_HIERARCHY.get( new_permission_level, 0 )

            if new_permission_rank >= user_permission_rank:
                form.add_error(
                    'permission_level',
                    'You cannot grant a permission level equal to or higher than your own.'
                )
            else:
                with transaction.atomic():
                    # If demoting from OWNER, verify another owner exists
                    if member.permission_level == TripPermissionLevel.OWNER and \
                       new_permission_level != TripPermissionLevel.OWNER:
                        owner_count = trip.members.select_for_update().filter(
                            permission_level = TripPermissionLevel.OWNER
                        ).exclude( pk = member.pk ).count()
                        if owner_count < 1:
                            form.add_error(
                                'permission_level',
                                'Cannot demote the last owner. Promote another member to owner first.'
                            )
                            context = {
                                'form': form,
                                'trip': trip,
                                'member': member,
                                'user_permission_rank': user_permission_rank,
                            }
                            return self.modal_response( request, context = context, status = 400 )

                    member.permission_level = new_permission_level
                    member.save()

                logger.info(
                    f'User {request.user.email} changed permission for {member.user.email} '
                    f'to {new_permission_level.label} on trip {trip.pk}'
                )

                return self.refresh_response( request )

        context = {
            'form': form,
            'trip': trip,
            'member': member,
            'user_permission_rank': user_permission_rank,
        }

        return self.modal_response( request, context = context, status = 400 )


class MemberRemoveModalView( LoginRequiredMixin, TripPermissionMixin, ModalView ):
    def get_template_name(self) -> str:
        return 'members/modals/remove.html'

    def get(self, request, trip_id: int, member_id: int, *args, **kwargs) -> HttpResponse:
        trip = get_object_or_404( Trip, pk = trip_id )
        member = get_object_or_404( TripMember, pk = member_id, trip = trip )

        is_self_removal = bool( member.user == request.user )

        if is_self_removal:
            required_permission = TripPermissionLevel.VIEWER
        else:
            required_permission = TripPermissionLevel.ADMIN

        if not self.has_trip_permission( request.user, trip, required_permission ):
            raise Http404( 'Trip not found' )

        if not is_self_removal:
            user_permission = trip.get_user_permission( request.user )
            user_permission_rank = self.PERMISSION_HIERARCHY.get( user_permission, 0 )
            member_permission_rank = self.PERMISSION_HIERARCHY.get( member.permission_level, 0 )

            if member_permission_rank >= user_permission_rank:
                raise Http404( 'Cannot remove this member' )

        if member.permission_level == TripPermissionLevel.OWNER:
            owner_count = trip.members.filter(
                permission_level = TripPermissionLevel.OWNER
            ).count()
            if owner_count <= 1:
                raise BadRequest(
                    'Cannot remove the last owner. Transfer ownership to another member first.'
                )

        form = MemberRemoveForm( member = member, is_self_removal = is_self_removal )

        context = {
            'form': form,
            'trip': trip,
            'member': member,
            'is_self_removal': is_self_removal,
        }

        return self.modal_response( request, context = context )

    def post(self, request, trip_id: int, member_id: int, *args, **kwargs) -> HttpResponse:
        trip = get_object_or_404( Trip, pk = trip_id )
        member = get_object_or_404( TripMember, pk = member_id, trip = trip )

        is_self_removal = bool( member.user == request.user )

        if is_self_removal:
            required_permission = TripPermissionLevel.VIEWER
        else:
            required_permission = TripPermissionLevel.ADMIN

        if not self.has_trip_permission( request.user, trip, required_permission ):
            raise Http404( 'Trip not found' )

        if not is_self_removal:
            user_permission = trip.get_user_permission( request.user )
            user_permission_rank = self.PERMISSION_HIERARCHY.get( user_permission, 0 )
            member_permission_rank = self.PERMISSION_HIERARCHY.get( member.permission_level, 0 )

            if member_permission_rank >= user_permission_rank:
                raise Http404( 'Cannot remove this member' )

        form = MemberRemoveForm( request.POST, member = member, is_self_removal = is_self_removal )

        if form.is_valid():
            with transaction.atomic():
                # Re-check owner count inside transaction with row locking to prevent race conditions
                if member.permission_level == TripPermissionLevel.OWNER:
                    owner_count = trip.members.select_for_update().filter(
                        permission_level = TripPermissionLevel.OWNER
                    ).count()
                    if owner_count <= 1:
                        raise BadRequest(
                            'Cannot remove the last owner. Transfer ownership to another member first.'
                        )

                member.delete()

            logger.info(
                f'User {request.user.email} removed {member.user.email} '
                f'from trip {trip.pk} (self_removal={is_self_removal})'
            )

            if is_self_removal:
                return self.redirect_response( request, reverse( 'home' ) )

            return self.refresh_response( request )

        context = {
            'form': form,
            'trip': trip,
            'member': member,
            'is_self_removal': is_self_removal,
        }

        return self.modal_response( request, context = context, status = 400 )


class MemberAcceptInvitationView( View ):
    """Accept invitation link for existing verified users."""

    def get(self, request, trip_id: int, email: str, token: str, *args, **kwargs) -> HttpResponse:
        trip = get_object_or_404( Trip, pk = trip_id )

        try:
            user = User.objects.get( email = email )
        except User.DoesNotExist:
            raise Http404( 'Invalid invitation link' )

        invitation_manager = MemberInvitationManager()
        is_valid = invitation_manager.verify_invitation_token( user = user, token = token )

        if not is_valid:
            context = {
                'trip': trip,
                'error_message': INVALID_INVITATION_MESSAGE,
            }
            return render( request, 'members/pages/invitation_invalid.html', context )

        if not request.user.is_authenticated:
            request.user = user
            django_login( request, user )

        if not user.email_verified:
            user.email_verified = True
            user.save()

        try:
            TripMember.objects.get( trip = trip, user = user )
            logger.info( f'User {user.email} accepted invitation to trip {trip.pk}' )
        except TripMember.DoesNotExist:
            logger.warning( f'User {user.email} has no membership for trip {trip.pk}' )

        return HttpResponseRedirect( reverse( 'trips_home', kwargs = { 'trip_id': trip.pk } ) )


class MemberSignupAndAcceptView( View ):
    """Signup and accept invitation link for new/unverified users."""

    def get(self, request, trip_id: int, email: str, token: str, *args, **kwargs) -> HttpResponse:
        trip = get_object_or_404( Trip, pk = trip_id )

        try:
            user = User.objects.get( email = email )
        except User.DoesNotExist:
            raise Http404( 'Invalid invitation link' )

        invitation_manager = MemberInvitationManager()
        is_valid = invitation_manager.verify_invitation_token( user = user, token = token )

        if not is_valid:
            context = {
                'trip': trip,
                'error_message': INVALID_INVITATION_MESSAGE,
            }
            return render( request, 'members/pages/invitation_invalid.html', context )

        if not request.user.is_authenticated:
            request.user = user
            django_login( request, user )

        if not user.email_verified:
            user.email_verified = True
            user.save()

        try:
            TripMember.objects.get( trip = trip, user = user )
            logger.info( f'New user {user.email} signed up and accepted invitation to trip {trip.pk}' )
        except TripMember.DoesNotExist:
            logger.warning( f'User {user.email} has no membership for trip {trip.pk}' )

        context = {
            'trip': trip,
            'user': user,
        }

        return render( request, 'members/pages/welcome.html', context )
