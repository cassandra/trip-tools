import pytz

from django import forms

from tt.constants import TIMEZONE_NAME_LIST
from tt.environment.constants import TtConst

from .enums import JournalVisibility
from .models import Journal, JournalEntry


def _truncate_timezone_label(tz, max_length=24):
    """Truncate timezone display label with ellipsis if too long."""
    if len(tz) <= max_length:
        return tz
    return tz[:max_length - 1] + '\u2026'


TIMEZONE_CHOICES = [(tz, _truncate_timezone_label(tz)) for tz in TIMEZONE_NAME_LIST]


class JournalForm(forms.ModelForm):

    timezone = forms.ChoiceField(
        choices = [(tz, tz) for tz in TIMEZONE_NAME_LIST],
        widget = forms.Select(attrs={
            'class': 'form-control',
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Customize help text for theme field
        if 'theme' in self.fields:
            self.fields['theme'].help_text = 'Color theme for published travelog pages'

    class Meta:
        model = Journal
        fields = ('title', 'description', 'timezone', 'theme')
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
            'theme': forms.Select(attrs={
                'class': 'form-control',
            }),
        }

    def clean_timezone(self):
        timezone = self.cleaned_data.get('timezone')
        if timezone:
            try:
                pytz.timezone(timezone)
            except pytz.exceptions.UnknownTimeZoneError:
                raise forms.ValidationError('Invalid timezone.')
        return timezone


class JournalEntryForm(forms.ModelForm):

    timezone = forms.ChoiceField(
        choices = TIMEZONE_CHOICES,
        widget = forms.Select(attrs={
            'class': 'form-control',
            'id': TtConst.JOURNAL_TIMEZONE_INPUT_ID,
        })
    )

    class Meta:
        model = JournalEntry
        fields = ('title', 'date', 'timezone')
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'id': TtConst.JOURNAL_TITLE_INPUT_ID,
                'placeholder': 'Entry title',
            }),
            'date': forms.DateInput(attrs={
                'class': 'form-control',
                'id': TtConst.JOURNAL_DATE_INPUT_ID,
                'type': 'date',
            }),
        }

    def clean_timezone(self):
        timezone = self.cleaned_data.get('timezone')
        if timezone:
            try:
                pytz.timezone(timezone)
            except pytz.exceptions.UnknownTimeZoneError:
                raise forms.ValidationError('Invalid timezone.')
        return timezone


class JournalVisibilityForm(forms.Form):

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
            'class': f'form-control {TtConst.ATTR_SECRET_INPUT_CLASS}',
            'placeholder': 'Enter new password',
        }),
        label = 'New Password',
    )

    def __init__(self, *args, journal = None, **kwargs):
        super().__init__(*args, **kwargs)

        self.journal = journal

        if journal and not kwargs.get('data'):
            self.initial['visibility'] = journal.visibility.name

            if journal.has_password:
                self.initial['password_action'] = self.PASSWORD_KEEP_EXISTING
            else:
                self.fields['password_action'].widget = forms.HiddenInput()
        return
    
    def clean(self):
        cleaned_data = super().clean()
        visibility = cleaned_data.get('visibility')
        password_action = cleaned_data.get('password_action')
        password = cleaned_data.get('password')

        if visibility == JournalVisibility.PROTECTED.name:
            has_existing_password = self.journal and self.journal.has_password

            if has_existing_password:
                if password_action == self.PASSWORD_SET_NEW:
                    if not password:
                        raise forms.ValidationError({
                            'password': 'New password is required.'
                        })
                # If KEEP_EXISTING, no password validation needed
            else:
                if not password:
                    raise forms.ValidationError({
                        'password': 'Password is required for protected journals.'
                    })

        return cleaned_data

    def should_update_password(self) -> bool:
        password_action = self.cleaned_data.get('password_action')
        has_existing_password = self.journal and self.journal.has_password

        # If no existing password, always update (new password required)
        if not has_existing_password:
            return True

        # If existing password, only update if user chose SET_NEW
        return bool( password_action == self.PASSWORD_SET_NEW )


class JournalTimezonesBulkUpdateForm(forms.Form):
    """Form for bulk updating journal entry timezones."""

    timezone = forms.CharField(
        max_length=63,
        widget=forms.HiddenInput(),
    )

    def clean_timezone(self):
        timezone = self.cleaned_data.get('timezone')
        if not timezone:
            raise forms.ValidationError('Timezone is required.')
        try:
            pytz.timezone(timezone)
        except pytz.exceptions.UnknownTimeZoneError:
            raise forms.ValidationError('Invalid timezone.')
        return timezone
