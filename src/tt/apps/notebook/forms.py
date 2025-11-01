"""
Forms for the notebook app.
"""

from django import forms

from .models import NotebookEntry


class NotebookEntryForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        self.trip = kwargs.pop('trip', None)
        super().__init__(*args, **kwargs)

    def clean_date(self):
        date = self.cleaned_data.get('date')
        if not date or not self.trip:
            return date

        # Check for existing entry with this date for this trip
        existing = NotebookEntry.objects.filter(
            trip=self.trip,
            date=date
        )

        # Exclude current instance if editing
        if self.instance.pk:
            existing = existing.exclude(pk=self.instance.pk)

        if existing.exists():
            raise forms.ValidationError(
                f'An entry for {date.strftime("%B %d, %Y")} already exists.'
            )

        return date

    class Meta:
        model = NotebookEntry
        fields = ['date', 'text']
        widgets = {
            'date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
            }),
            'text': forms.Textarea(attrs={
                'rows': 20,
                'class': 'form-control',
                'placeholder': 'Enter your notes here...',
            }),
        }
