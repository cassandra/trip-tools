from django import forms

from .models import Trip
from .enums import TripStatus


class TripForm( forms.ModelForm ):

    class Meta:
        model = Trip
        fields = (
            'title',
            'description',
            'trip_status',
        )
        widgets = {
            'title': forms.TextInput( attrs = {
                'class': 'form-control',
                'placeholder': 'Enter trip title',
                'autofocus': 'autofocus',
            }),
            'description': forms.Textarea( attrs = {
                'class': 'form-control',
                'placeholder': 'Enter optional description',
                'rows': 3,
            }),
            'trip_status': forms.Select( attrs = {
                'class': 'form-control',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not self.instance.pk:
            self.initial['trip_status'] = TripStatus.UPCOMING

        return
