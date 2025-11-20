from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

from tt.apps.trips.enums import TripPermissionLevel

from .models import TripMember

User = get_user_model()


class MemberInviteForm( forms.Form ):
    email = forms.EmailField(
        required = True,
        widget = forms.EmailInput( attrs = {
            'class': 'form-control',
            'placeholder': 'Enter email address',
            'autofocus': 'autofocus',
        })
    )
    permission_level = forms.ChoiceField(
        required = True,
        choices = TripPermissionLevel.choices(),
        initial = TripPermissionLevel.VIEWER.name.lower(),
        widget = forms.Select( attrs = {
            'class': 'form-control',
        })
    )
    send_email = forms.BooleanField(
        required = False,
        initial = True,
        widget = forms.CheckboxInput( attrs = {
            'class': 'form-check-input',
            'checked': 'checked',
        })
    )

    def __init__( self, *args, trip = None, **kwargs ):
        super().__init__( *args, **kwargs )
        self.trip = trip
        return

    def clean_email(self) -> str:
        email = self.cleaned_data.get('email')
        if not email:
            return email

        try:
            validate_email( email )
        except ValidationError:
            raise ValidationError( 'Please enter a valid email address.' )

        if self.trip and TripMember.objects.filter( trip = self.trip, user__email = email ).exists():
            raise ValidationError( 'This user is already a member of this trip.' )

        return email.lower().strip()

    def clean_permission_level(self) -> TripPermissionLevel | None:
        permission_level_str = self.cleaned_data.get('permission_level')
        if not permission_level_str:
            return None

        try:
            return TripPermissionLevel.from_name( permission_level_str )
        except ValueError:
            raise ValidationError( 'Invalid permission level selected.' )


class MemberPermissionForm( forms.Form ):
    permission_level = forms.ChoiceField(
        required = True,
        choices = TripPermissionLevel.choices(),
        widget = forms.Select( attrs = {
            'class': 'form-control',
        })
    )

    def __init__( self, *args, member = None, **kwargs ):
        super().__init__( *args, **kwargs )
        self.member = member
        if member:
            self.fields['permission_level'].initial = member.permission_level.name.lower()
        return

    def clean_permission_level(self) -> TripPermissionLevel | None:
        permission_level_str = self.cleaned_data.get('permission_level')
        if not permission_level_str:
            return None

        try:
            return TripPermissionLevel.from_name( permission_level_str )
        except ValueError:
            raise ValidationError( 'Invalid permission level selected.' )


class MemberRemoveForm( forms.Form ):
    def __init__( self, *args, member = None, is_self_removal = False, **kwargs ):
        super().__init__( *args, **kwargs )
        self.member = member
        self.is_self_removal = is_self_removal
        return
