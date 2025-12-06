"""
Admin customizations for user-related functionality.

This module injects admin actions into CustomUserAdmin without creating
a circular dependency (custom -> tt.apps.user).
"""
from django.contrib import admin

from custom.models import CustomUser

from .invitation_manager import UserInvitationManager


@admin.action(description='Send invitation email to selected users')
def send_invitation_email(modeladmin, request, queryset):
    """Send welcome/invitation emails to selected users."""
    manager = UserInvitationManager()
    count = 0
    skipped = 0
    for user in queryset:
        if user.email:
            manager.send_welcome_email(
                request,
                user,
                invited_by_name=request.user.get_full_name(),
            )
            count += 1
        else:
            skipped += 1

    if skipped:
        modeladmin.message_user(
            request,
            f'Sent invitation email to {count} user(s). Skipped {skipped} user(s) without email.',
        )
    else:
        modeladmin.message_user(request, f'Sent invitation email to {count} user(s).')


# Inject the action into the existing CustomUserAdmin
# This runs when this admin module is loaded (via INSTALLED_APPS)
CustomUserAdmin = admin.site._registry.get(CustomUser)
if CustomUserAdmin:
    CustomUserAdmin.actions = list(CustomUserAdmin.actions or []) + [send_invitation_email]
