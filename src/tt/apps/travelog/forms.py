from django import forms

from tt.environment.constants import TtConst


class TravelogPasswordForm(forms.Form):
    """
    Form for entering password to access a password-protected travelog.
    """

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': f'form-control {TtConst.ATTR_SECRET_INPUT_CLASS}',
            'placeholder': 'Enter password',
            'autofocus': True,
        }),
        label='Password',
        max_length=128,
        help_text='Enter the password provided by the journal owner.',
    )
