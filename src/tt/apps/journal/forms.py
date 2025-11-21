from django import forms

from tt.constants import TIMEZONE_NAME_LIST

from .enums import JournalVisibility
from .models import Journal, JournalEntry


class JournalForm(forms.ModelForm):
    """Form for creating a new journal."""

    timezone = forms.ChoiceField(
        choices = [(tz, tz) for tz in TIMEZONE_NAME_LIST],
        widget = forms.Select(attrs={
            'class': 'form-control',
        })
    )

    class Meta:
        model = Journal
        fields = ('title', 'description', 'timezone')
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter journal title',
                'autofocus': 'autofocus',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Enter optional description',
                'rows': 3,
            }),
        }

    def clean_timezone(self):
        """Validate that the timezone is in the allowed list."""
        timezone = self.cleaned_data.get('timezone')
        if timezone and timezone not in TIMEZONE_NAME_LIST:
            raise forms.ValidationError('Please select a valid timezone from the list.')
        return timezone


class JournalEntryForm(forms.ModelForm):
    """Form for editing a journal entry."""

    timezone = forms.ChoiceField(
        choices = [(tz, tz) for tz in TIMEZONE_NAME_LIST],
        widget = forms.Select(attrs={
            'class': 'form-control',
            'id': 'id_entry_timezone',
        })
    )

    class Meta:
        model = JournalEntry
        fields = ('title', 'date', 'timezone')
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'id_entry_title',
                'placeholder': 'Entry title',
            }),
            'date': forms.DateInput(attrs={
                'class': 'form-control',
                'id': 'id_entry_date',
                'type': 'date',
            }),
        }

    def clean_timezone(self):
        """Validate that the timezone is in the allowed list."""
        timezone = self.cleaned_data.get('timezone')
        if timezone and timezone not in TIMEZONE_NAME_LIST:
            raise forms.ValidationError('Please select a valid timezone from the list.')
        return timezone


class JournalVisibilityForm(forms.Form):
    """Form for managing journal visibility settings."""

    # Password action choices
    PASSWORD_KEEP_EXISTING = 'KEEP_EXISTING'
    PASSWORD_SET_NEW = 'SET_NEW'
    PASSWORD_ACTION_CHOICES = [
        (PASSWORD_KEEP_EXISTING, 'Use existing password'),
        (PASSWORD_SET_NEW, 'Set new password'),
    ]

    visibility = forms.ChoiceField(
        choices = [(vis.name, vis.label) for vis in JournalVisibility],
        widget = forms.RadioSelect(attrs={
            'class': 'visibility-radio',
        }),
        label = 'Visibility',
        help_text = 'Choose who can access this journal',
    )

    password_action = forms.ChoiceField(
        choices = PASSWORD_ACTION_CHOICES,
        widget = forms.RadioSelect(attrs={
            'class': 'password-action-radio',
        }),
        required = False,
        label = 'Password',
    )

    password = forms.CharField(
        required = False,
        widget = forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter new password',
        }),
        label = 'New Password',
    )

    def __init__(self, *args, journal=None, **kwargs):
        """
        Initialize form with optional journal instance for pre-population.

        Args:
            journal: Journal instance to pre-populate form with current values
        """
        super().__init__(*args, **kwargs)

        # Store journal instance for validation
        self.journal = journal

        # Pre-populate with current journal values if provided
        if journal and not kwargs.get('data'):
            self.initial['visibility'] = journal.visibility.name

            # Configure password_action field based on whether password exists
            if journal.has_password:
                # Journal has existing password - show password_action radios
                self.initial['password_action'] = self.PASSWORD_KEEP_EXISTING
            else:
                # No existing password - hide password_action field
                self.fields['password_action'].widget = forms.HiddenInput()

    def clean(self):
        """Validate password based on visibility and password_action choices."""
        cleaned_data = super().clean()
        visibility = cleaned_data.get('visibility')
        password_action = cleaned_data.get('password_action')
        password = cleaned_data.get('password')

        # Only validate password when PROTECTED visibility is selected
        if visibility == JournalVisibility.PROTECTED.name:
            has_existing_password = self.journal and self.journal.has_password

            if has_existing_password:
                # Journal has existing password - check password_action
                if password_action == self.PASSWORD_SET_NEW:
                    # User wants to set new password - require it
                    if not password:
                        raise forms.ValidationError({
                            'password': 'New password is required.'
                        })
                # If KEEP_EXISTING, no password validation needed
            else:
                # No existing password - password is required
                if not password:
                    raise forms.ValidationError({
                        'password': 'Password is required for protected journals.'
                    })

        return cleaned_data

    def should_update_password(self):
        """
        Determine if password should be updated based on form state.

        Returns:
            bool: True if password should be updated, False to keep existing
        """
        password_action = self.cleaned_data.get('password_action')
        has_existing_password = self.journal and self.journal.has_password

        # If no existing password, always update (new password required)
        if not has_existing_password:
            return True

        # If existing password, only update if user chose SET_NEW
        return password_action == self.PASSWORD_SET_NEW
