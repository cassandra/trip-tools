from django import forms

from .magic_code_generator import MagicCodeGenerator


class SigninMagicCodeForm(forms.Form):

    email_address = forms.CharField(
        max_length = 128,
        widget = forms.HiddenInput(),
    )

    magic_code = forms.CharField(
        label = '',
        max_length = 2 * MagicCodeGenerator.MAGIC_CODE_LENGTH,
        widget = forms.TextInput( attrs = { 'autofocus': 'autofocus',
                                            'placeholder': 'access code',
                                            'width': str(2 * MagicCodeGenerator.MAGIC_CODE_LENGTH) } ),
        required = True )


class APITokenCreateForm(forms.Form):

    name = forms.CharField(
        label = 'Name',
        max_length = 100,
        widget = forms.TextInput( attrs = {
            'autofocus': 'autofocus',
            'placeholder': 'e.g., Mobile App, Chrome Extension',
            'class': 'form-control',
        }),
        required = True,
        help_text = 'Choose a descriptive name to help you identify this key later.',
    )


class ProfileEditForm(forms.Form):

    first_name = forms.CharField(
        label = 'First Name',
        max_length = 150,
        widget = forms.TextInput( attrs = {
            'class': 'form-control',
            'placeholder': 'First name',
        }),
        required = True,
    )

    last_name = forms.CharField(
        label = 'Last Name',
        max_length = 150,
        widget = forms.TextInput( attrs = {
            'class': 'form-control',
            'placeholder': 'Last name',
        }),
        required = False,
    )
