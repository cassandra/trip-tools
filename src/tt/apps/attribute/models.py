import json
import logging

from django.core.files.storage import default_storage
from django.db import models

from tt.apps.common.file_utils import generate_unique_filename
from tt.apps.common.model_fields import LabeledEnumField

from .enums import AttributeValueType, AttributeType
from .value_ranges import PredefinedValueRanges

logger = logging.getLogger(__name__)


class AttributeValueHistoryModel(models.Model):
    """
    Abstract base class for tracking attribute value changes.
    Each concrete attribute subclass should have its own history model
    that defines the foreign key to its specific attribute type.
    
    Only tracks value-based attributes (Text, Boolean, Integer, Float, etc.).
    File attributes are excluded and will be handled separately.
    """
    
    class Meta:
        abstract = True
        ordering = ['-changed_datetime']
    
    value = models.TextField(
        'Value',
        blank=True, null=True,
    )
    changed_datetime = models.DateTimeField(
        'Changed',
        auto_now_add=True,
        db_index=True,
    )

    def __str__(self):
        return f'Changed at {self.changed_datetime}'


class AttributeModel(models.Model):

    class Meta:
        abstract = True
 
    name = models.CharField(
        'Name',
        max_length = 64,
    )
    value = models.TextField(
        'Value',
        blank = True, null = True,
    )
    file_value = models.FileField(
        upload_to = 'attributes/',  # Subclasses override via get_upload_to()
        blank = True, null = True,
    )
    file_mime_type = models.CharField(
        'Mime Type',
        max_length = 128,
        null = True, blank = True,
    )
    value_type = LabeledEnumField(
        AttributeValueType,
        'Value Type',
        null = False,
        blank = False,
    )
    value_range_str = models.TextField(
        'Value Range',
        null = True, blank = True,
    )
    attribute_type = LabeledEnumField(
        AttributeType,
        'Attribute Type',
        null = False,
        blank = False,
    )
    is_editable = models.BooleanField(
        'Editable?',
        default = True,
    )
    is_required = models.BooleanField(
        'Required?',
        default = False,
    )
    created_datetime = models.DateTimeField(
        'Created',
        auto_now_add = True,
    )
    updated_datetime = models.DateTimeField(
        'Updated',
        auto_now=True,
        blank = True,
    )

    def get_upload_to(self):
        raise NotImplementedError('Subclasses should override this method.' )

    def __str__(self):
        return f'Attr: {self.name}={self.value} [{self.value_type}] [{self.attribute_type}]'
    
    def __repr__(self):
        return self.__str__()
    
    @property
    def is_predefined(self):
        return bool( self.attribute_type == AttributeType.PREDEFINED )
    
    def choices(self):
        # First check predefined ids
        choice_list = PredefinedValueRanges.get_choices( self.value_range_str )
        if choice_list:
            return choice_list
        if not self.value_range_str:
            return list()
        try:
            value_range = json.loads( self.value_range_str )
            if isinstance( value_range, dict ):
                return [ ( k, v ) for k, v in value_range.items() ]
            if isinstance( value_range, list ):
                return [ ( x, x ) for x in value_range ]
        except json.JSONDecodeError as e:
            logger.error( f'Bad value range for attribute {self.name}: {e}' )
            pass
        return dict()

    def save(self, *args, **kwargs):
        # Skip history tracking for kwargs that disable it
        track_history = kwargs.pop('track_history', True)
        
        if self.file_value and self.file_value.name:
            self.file_value.field.upload_to = self.get_upload_to()
            if not self.value:
                self.value = self.file_value.name
            if not self.pk or not self.__class__.objects.filter( pk = self.pk ).exists():
                self.file_value.name = generate_unique_filename( self.file_value.name )
        
        # Save the attribute first
        super().save(*args, **kwargs)
        
        # Track history for value-based attributes only AFTER saving
        if track_history and not self.value_type.is_file:
            self._create_history_record()
        
        return
    
    def _create_history_record(self):
        """Create a history record for this attribute's value change."""
        # Get the history model class for this concrete attribute type
        history_model_class = self._get_history_model_class()
        if not history_model_class:
            return
        
        # Create history record
        history_model_class.objects.create(
            attribute=self,
            value=self.value
        )
    
    def _get_history_model_class(self):
        """
        Get the corresponding history model class for this attribute type.
        Must be implemented by all concrete subclasses.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement _get_history_model_class() "
            "to provide history tracking support."
        )
    
    def delete( self, *args, **kwargs ):
        """ Deleting file from MEDIA_ROOT on best effort basis.  Ignore if fails. """
        
        if self.file_value:
            try:
                if default_storage.exists( self.file_value.name ):
                    default_storage.delete( self.file_value.name )
                    logger.debug( f'Deleted Attribute file: {self.file_value.name}' )
                else:
                    logger.warn( f'Attribute file not found: {self.file_value.name}' )
            except Exception as e:
                # Log the error or handle it accordingly
                logger.warn( f'Error deleting Attribute file {self.file_value.name}: {e}' )

        super().delete( *args, **kwargs )
        return
