"""
Custom Django model fields for common patterns.
"""
from django.core.exceptions import ValidationError
from django.db import models

from .enums import LabeledEnum


class LabeledEnumDescriptor:
    """
    Descriptor that converts database strings to enum instances automatically.
    Returns the field object when accessed from the class (for Django admin).
    """

    def __init__(self, field):
        self.field = field

    def __get__(self, instance, owner):
        if instance is None:
            # Class access - return field for admin/meta access
            return self.field

        # Get raw value
        value = instance.__dict__.get(self.field.attname)

        if value is None:
            return None

        # If already an enum, return it
        if isinstance(value, self.field.enum_class):
            return value

        # Convert string to enum
        if isinstance(value, str):
            try:
                return self.field._convert_from_string(value)
            except (ValueError, ValidationError):
                if self.field.use_safe_conversion:
                    return self.field.enum_class.default()
                return value

        # Try to convert other types
        try:
            return self.field.to_python(value)
        except (ValueError, ValidationError):
            if self.field.use_safe_conversion:
                return self.field.enum_class.default()
            return value

    def __set__(self, instance, value):
        instance.__dict__[self.field.attname] = value


class LabeledEnumField(models.CharField):
    """
    A Django model field for storing LabeledEnum values.
    
    This field:
    - Stores enum values as lowercase strings in the database (VARCHAR)
    - Accepts enum instances or strings when setting values
    - Returns enum instances when accessing values
    - Validates that values are valid enum members
    - Does NOT require migrations when enum values change
    
    Usage:
        class MyModel(models.Model):
            # Use safe conversion (returns default for invalid values)
            status = LabeledEnumField(StatusType, max_length=32)
            
            # Use strict conversion (raises ValueError for invalid values)
            priority = LabeledEnumField(PriorityType, max_length=32, use_safe_conversion=False)
            
        # Can set with enum instance
        obj.status = StatusType.ACTIVE
        
        # Can set with string (case-insensitive)
        obj.status = 'active'
        obj.status = 'ACTIVE'
        
        # Always returns enum instance
        assert obj.status == StatusType.ACTIVE
        assert isinstance(obj.status, StatusType)
    """
    
    description = "A field for storing LabeledEnum values as lowercase strings"
    
    def __init__(self, enum_class, *args, use_safe_conversion=True, **kwargs):
        """
        Initialize the field.

        Args:
            enum_class: The LabeledEnum subclass this field stores
            use_safe_conversion: If True, use from_name_safe() which returns default for invalid values.
                               If False, use from_name() which raises ValueError for invalid values.
                               Default is True for backward compatibility and safety.
        """
        if not issubclass(enum_class, LabeledEnum):
            raise TypeError(f"{enum_class} must be a subclass of LabeledEnum")

        self.enum_class = enum_class
        self.use_safe_conversion = use_safe_conversion

        # Set default max_length if not provided
        if 'max_length' not in kwargs:
            # Calculate max length from enum values
            max_len = max(len(str(e)) for e in enum_class)
            kwargs['max_length'] = max(32, max_len + 10)  # Add buffer, min 32

        # DO NOT set choices on the field - we want dynamic choices without migrations
        # Choices will be provided via formfield() for admin forms

        # Set default if the enum has one and no default was provided
        if 'default' not in kwargs and hasattr(enum_class, 'default'):
            kwargs['default'] = str(enum_class.default())

        super().__init__(*args, **kwargs)
    
    def _convert_from_string(self, value):
        """
        Convert string value to enum instance using configured conversion method.
        
        Args:
            value: String value to convert
            
        Returns:
            Enum instance
            
        Raises:
            ValueError: If use_safe_conversion is False with invalid value
        """
        if self.use_safe_conversion:
            return self.enum_class.from_name_safe(value)
        else:
            return self.enum_class.from_name(value)
    
    def deconstruct(self):
        """
        Return enough information to recreate the field.
        Required for migrations.
        """
        name, path, args, kwargs = super().deconstruct()
        # Store the enum class path for reconstruction
        kwargs['enum_class'] = self.enum_class
        kwargs['use_safe_conversion'] = self.use_safe_conversion
        return name, path, args, kwargs
    
    def from_db_value(self, value, expression, connection):
        """
        Convert database value to Python enum instance.
        Called when fetching from database.
        """
        if value is None:
            return None
        
        try:
            return self._convert_from_string(value)
        except ValueError as e:
            # This should rarely happen with database values
            # but if it does, we want to know about it
            raise ValidationError(
                f"Invalid database value '{value}' for {self.enum_class.__name__}: {e}"
            )
    
    def to_python(self, value):
        """
        Convert input value to Python enum instance.
        Called during deserialization and clean().
        """
        if value is None:
            return None
        
        if isinstance(value, self.enum_class):
            return value
        
        if isinstance(value, str):
            try:
                return self._convert_from_string(value)
            except ValueError as e:
                raise ValidationError(
                    f"Invalid value '{value}' for {self.enum_class.__name__}: {e}"
                )
        
        # Try to convert other types to string first
        try:
            return self._convert_from_string(str(value))
        except (TypeError, ValueError) as e:
            raise ValidationError(
                f"Cannot convert {value!r} to {self.enum_class.__name__}: {e}"
            )
    
    def get_prep_value(self, value):
        """
        Convert Python value to database value.
        Called before saving to database.
        """
        if value is None:
            return None
        
        if isinstance(value, self.enum_class):
            # Convert enum to lowercase string
            return str(value)
        
        if isinstance(value, str):
            # Ensure lowercase
            # First validate it's a valid enum value
            try:
                enum_instance = self._convert_from_string(value)
                return str(enum_instance)
            except ValueError as e:
                raise ValidationError(
                    f"Invalid value '{value}' for {self.enum_class.__name__}: {e}"
                )
        
        # Try to convert to enum first for validation
        try:
            enum_instance = self.to_python(value)
            return str(enum_instance) if enum_instance else None
        except ValidationError:
            # Re-raise with clear message
            raise ValidationError(
                f"Value {value!r} is not valid for {self.enum_class.__name__}"
            )
    
    def value_to_string(self, obj):
        """
        Convert value to string for serialization.
        Used by dumpdata and other serializers.
        """
        value = self.value_from_object(obj)
        if value is None:
            return None
        return str(value)
    
    def validate(self, value, model_instance):
        """
        Validate that the value is a valid enum member.
        Called during model validation.

        Note: We do custom validation against the enum class, not CharField's choices.
        This allows enums to change without requiring migrations.
        """
        if value is None:
            if not self.null:
                raise ValidationError("This field cannot be null.")
            return

        # Convert enum to string for parent validation (max_length, etc.)
        string_value = str(value) if isinstance(value, self.enum_class) else value

        # Call parent's validate with string value to check max_length, etc.
        # Skip CharField's choice validation by calling Field.validate directly
        super(models.CharField, self).validate(string_value, model_instance)

        # Now validate that it's a valid enum member
        if isinstance(value, self.enum_class):
            # Already a valid enum
            return

        # Try to convert string to enum to validate
        try:
            self.to_python(value)
        except ValidationError:
            # Re-raise with clearer message
            valid_values = [str(e) for e in self.enum_class]
            raise ValidationError(
                f"'{value}' is not a valid {self.enum_class.__name__}. "
                f"Valid values are: {', '.join(valid_values)}"
            )

    def formfield(self, **kwargs):
        """
        Return a form field for this model field.

        Provides choices dynamically for admin forms without storing them on the model.
        This allows enum values to change without requiring migrations.
        """
        from django import forms

        # Get choices dynamically from the enum
        choices = self.enum_class.choices()

        # Set up the form field with choices
        defaults = {
            'form_class': forms.TypedChoiceField,
            'choices': choices,
            'coerce': lambda val: self.to_python(val) if val else None,
        }
        defaults.update(kwargs)

        # Skip CharField's formfield to avoid its choice handling
        return super(models.CharField, self).formfield(**defaults)

    def contribute_to_class(self, cls, name, **kwargs):
        """
        Hook for adding the field to the model class.
        Installs a descriptor for automatic string-to-enum conversion.
        """
        super().contribute_to_class(cls, name, **kwargs)
        # Install descriptor for automatic conversion
        setattr(cls, name, LabeledEnumDescriptor(self))


class NullableLabeledEnumField(LabeledEnumField):
    """
    A nullable version of LabeledEnumField.
    
    Convenience class that sets null=True, blank=True by default.
    """
    
    def __init__(self, enum_class, *args, **kwargs):
        kwargs.setdefault('null', True)
        kwargs.setdefault('blank', True)
        super().__init__(enum_class, *args, **kwargs)
