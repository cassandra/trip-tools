from django import forms

from tt.constants import TIMEZONE_NAME_LIST

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
