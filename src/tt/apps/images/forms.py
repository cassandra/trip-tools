from django import forms
from decimal import Decimal, InvalidOperation

from tt.apps.common.geo_utils import parse_long_lat_from_text, GeoPointParseError
from tt.constants import TIMEZONE_NAME_LIST

from .models import TripImage


class TripImageEditForm(forms.ModelForm):

    # Custom field for GPS input (comma-separated lat, lng)
    gps_coordinates = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., 37.7749, -122.4194 or 37.7749 N, 122.4194 W',
        }),
        help_text='Enter coordinates in various formats (decimal degrees, DMS, etc.)',
        label='GPS Coordinates',
    )

    # Custom field for tags input (comma-separated)
    tags_input = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'vacation, beach, sunset',
        }),
        help_text='Enter tags separated by commas (max 50 characters per tag)',
        label='Tags',
    )

    # Timezone selection field
    timezone = forms.ChoiceField(
        required=False,
        choices=[('', '(Unknown)')] + [(tz, tz) for tz in TIMEZONE_NAME_LIST],
        widget=forms.Select(attrs={
            'class': 'form-control',
        }),
        help_text='Timezone where the photo was taken',
        label='Timezone',
    )

    class Meta:
        model = TripImage
        fields = ['caption', 'datetime_utc', 'timezone', 'latitude', 'longitude', 'tags']
        widgets = {
            'caption': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter image caption',
            }),
            'datetime_utc': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control',
            }),
            'latitude': forms.HiddenInput(),
            'longitude': forms.HiddenInput(),
            'tags': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance.pk and self.instance.latitude and self.instance.longitude:
            self.initial['gps_coordinates'] = f"{self.instance.latitude}, {self.instance.longitude}"

        if self.instance.pk and self.instance.tags:
            self.initial['tags_input'] = ', '.join(self.instance.tags)

        if self.instance.pk and self.instance.datetime_utc:
            # If the image has a timezone, show the datetime in that timezone
            # Otherwise, show it in UTC
            # Note: datetime-local inputs expect naive datetime strings (no timezone info)
            if self.instance.timezone:
                import pytz
                tz = pytz.timezone(self.instance.timezone)
                dt_in_tz = self.instance.datetime_utc.astimezone(tz)
                # Convert to naive datetime for the input
                dt_str = dt_in_tz.replace(tzinfo=None).strftime('%Y-%m-%dT%H:%M')
            else:
                # For images without timezone, use UTC
                dt_str = self.instance.datetime_utc.replace(tzinfo=None).strftime('%Y-%m-%dT%H:%M')
            self.initial['datetime_utc'] = dt_str

    def clean_gps_coordinates(self):
        gps_text = self.cleaned_data.get('gps_coordinates', '').strip()

        if not gps_text:
            return None

        try:
            latitude, longitude = parse_long_lat_from_text(gps_text)
            return {'latitude': Decimal(str(latitude)), 'longitude': Decimal(str(longitude))}
        except (GeoPointParseError, ValueError, InvalidOperation) as e:
            raise forms.ValidationError(f'Invalid GPS coordinates: {str(e)}')

    def clean_tags_input(self):
        tags_text = self.cleaned_data.get('tags_input', '').strip()

        if not tags_text:
            return []

        tags = [tag.strip() for tag in tags_text.split(',')]
        tags = [tag for tag in tags if tag]  # Remove empty strings

        for tag in tags:
            if len(tag) > 50:
                raise forms.ValidationError(f'Tag "{tag}" exceeds maximum length of 50 characters.')
            continue
        
        return tags

    def clean(self):
        cleaned_data = super().clean()

        gps_data = self.cleaned_data.get('gps_coordinates')
        if gps_data:
            cleaned_data['latitude'] = gps_data['latitude']
            cleaned_data['longitude'] = gps_data['longitude']
        else:
            cleaned_data['latitude'] = None
            cleaned_data['longitude'] = None

        tags_list = self.cleaned_data.get('tags_input', [])
        cleaned_data['tags'] = tags_list

        # Convert datetime from the selected timezone to UTC
        datetime_value = cleaned_data.get('datetime_utc')
        timezone_value = cleaned_data.get('timezone')

        if datetime_value and timezone_value:
            # User entered datetime in the context of the selected timezone
            # Need to convert it to UTC for storage
            import pytz

            tz = pytz.timezone(timezone_value)

            # The datetime from the form may be naive or aware (with UTC tzinfo from Django)
            # We need to interpret it as if it's in the selected timezone
            if datetime_value.tzinfo is None:
                # Naive datetime - localize to selected timezone
                dt_in_tz = tz.localize(datetime_value)
            else:
                # Already has tzinfo (probably UTC from Django) - strip it and localize
                dt_naive = datetime_value.replace(tzinfo=None)
                dt_in_tz = tz.localize(dt_naive)

            # Convert to UTC
            cleaned_data['datetime_utc'] = dt_in_tz.astimezone(pytz.utc)
        elif datetime_value and not timezone_value:
            # No timezone selected, treat the datetime as UTC
            import pytz
            from django.utils import timezone as django_timezone
            if datetime_value.tzinfo is None:
                cleaned_data['datetime_utc'] = django_timezone.make_aware(datetime_value, timezone=pytz.utc)

        return cleaned_data

    def save(self, commit = True, user = None):
        instance = super().save(commit=False)

        if 'tags' in self.cleaned_data:
            instance.tags = self.cleaned_data['tags']

        # Timezone field is now handled directly by the form field
        # No need to set timezone_unknown as it's a property based on timezone field

        if user:
            instance.modified_by = user

        if commit:
            instance.save()

        return instance
