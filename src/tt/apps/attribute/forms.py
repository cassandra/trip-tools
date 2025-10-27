import mimetypes

from django.core.exceptions import ValidationError
from django import forms

from tt.apps.common.utils import is_blank, str_to_bool

from .enums import AttributeType, AttributeValueType


class RegularAttributeBaseFormSet(forms.BaseInlineFormSet):
    """Base formset that automatically excludes FILE attributes for regular attribute editing.
    
    This formset is used across all attribute-enabled modules (Entity, Location, Config)
    to ensure FILE type attributes are handled separately from regular attributes.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Apply filtering after parent initialization
        self.queryset = self.queryset.exclude( value_type = AttributeValueType.FILE )
    
    def get_queryset(self):
        """Override to automatically filter out FILE attributes"""
        queryset = super().get_queryset()
        return queryset.exclude( value_type = AttributeValueType.FILE )


class AttributeForm( forms.ModelForm ):
    """
    Abstract mode form class the corresponds to the abstract model calss
    Attribute.  When subclassing the Attribute model, you likely also want
    a subclass of this model form.  Subclassing this fomr looks something
    like this:
    
        class MyAttributeForm( AttributeForm ):
            class Meta( AttributeForm.Meta ):
                model = MyAttribute
    """
    class Meta:
        fields = (
            'name',
            'value',
        )
        widgets = {
            'name': forms.TextInput( attrs={'class': 'form-control'} ),
            'value': forms.TextInput( attrs={'class': 'form-control'} ),
        }

    secret = forms.BooleanField(
        required = False,
        label = 'Mark as Secret',
        widget = forms.CheckboxInput(attrs={'class': 'custom-control-input'}),
    )

    @property
    def show_as_editable(self):
        return self._show_as_editable
    
    @property
    def allow_reordering(self):
        return self._allow_reordering
    
    @property
    def suppress_history(self):
        return self._suppress_history
    
    @property
    def show_secrets(self):
        return self._show_secrets
        
    def __init__(self, *args, **kwargs):
        self._show_as_editable = kwargs.pop( 'show_as_editable', True )
        self._allow_reordering = kwargs.pop( 'allow_reordering', True )
        self._suppress_history = kwargs.pop( 'suppress_history', False )
        self._show_secrets = kwargs.pop( 'show_secrets', False )
        
        instance = kwargs.get('instance')
        super().__init__(*args, **kwargs)

        # For boolean attributes, keep string field but set initial as string consistently  
        if instance and instance.value_type.is_boolean:
            self.initial['value'] = str(str_to_bool(instance.value))
            
        for field in self.fields.values():
            if self._show_as_editable or ( instance and instance.is_editable ):
                continue
            field.widget.attrs['disabled'] = 'disabled'
            continue
            
        return
            
    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get('name')
        value = cleaned_data.get('value')
        
        form_is_bound = bool( self.instance.pk )
        if form_is_bound:
            if ( not self.instance.is_editable
                 and ( value is not None )
                 and ( value != self.instance.value )):
                raise ValidationError( f'The attribute "{self.instance.name}" is not editable.' )
            if ( self.instance.attribute_type == AttributeType.PREDEFINED
                 and ( name is not None )
                 and ( name != self.instance.name )):
                raise ValidationError( 'Changing name forbidden for predefined attributes.' )
            
            value = cleaned_data.get('value')
            if self.instance.is_required and is_blank( value ):
                self.add_error( 'value', 'A value is required.')
            if self.instance.value_type.is_boolean:
                cleaned_data['value'] = str(str_to_bool( value ))
                
        if self.cleaned_data.get('secret'):
            stripped_value = value.strip()
            value_lines = stripped_value.splitlines()
            if len( value_lines) > 1:
                self.add_error( 'value', 'Secret attributes are limited ot a single line.')
            
        return cleaned_data

    def save( self, commit = True ):
        instance = super().save( commit = False )

        if not instance.pk:
            instance.attribute_type = AttributeType.CUSTOM
            instance.is_editable = True
            instance.is_required = False

            if self.cleaned_data.get('secret'):
                instance.value_type = AttributeValueType.SECRET
            else:
                instance.value_type = AttributeValueType.TEXT

        elif not instance.is_editable:
            return instance
        
        if commit:
            instance.save()
        return instance

    
class AttributeUploadForm( forms.ModelForm ):

    class Meta:
        fields = (
            'file_value',
        )
        
    def clean(self):
        cleaned_data = super().clean()

        file_value = cleaned_data.get('file_value')
        if not file_value:
            self.add_error( 'file_value', 'A file is required.')

        return cleaned_data

    def save( self, commit = True ):
        instance = super().save( commit = False )

        mime_type_tuple = mimetypes.guess_type( instance.file_value.name )
        
        instance.name = instance.file_value.name
        instance.file_mime_type = mime_type_tuple[0]
        instance.value_type = AttributeValueType.FILE
        instance.attribute_type = AttributeType.CUSTOM
        instance.is_editable = True
        instance.is_required = False

        if commit:
            instance.save()
        return instance
