from django import forms


class TravelogPasswordForm(forms.Form):
    """
    Form for entering password to access a password-protected travelog.
    """

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter password',
            'autofocus': True,
        }),
        label='Password',
        max_length=128,
        help_text='Enter the password provided by the journal owner.',
    )
