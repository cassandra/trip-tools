import json
import logging
from unittest.mock import patch

from tt.apps.attribute.models import AttributeModel
from tt.apps.attribute.enums import AttributeValueType, AttributeType
from tt.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class ConcreteAttributeModel(AttributeModel):
    """Concrete implementation for testing the abstract AttributeModel."""
    
    def get_upload_to(self):
        return 'test_attributes/'


class TestAttributeModel(BaseTestCase):

    def test_attribute_model_enum_property_conversions(self):
        """Test enum property conversions - custom business logic."""
        attr = ConcreteAttributeModel(
            name='test_attr',
            value_type_str='FILE',
            attribute_type_str='CUSTOM'
        )
        
        # Test getter converts string to enum
        self.assertEqual(attr.value_type, AttributeValueType.FILE)
        self.assertEqual(attr.attribute_type, AttributeType.CUSTOM)
        
        # Test setter converts enum to string
        attr.value_type = AttributeValueType.BOOLEAN
        attr.attribute_type = AttributeType.PREDEFINED
        self.assertEqual(attr.value_type_str, 'boolean')
        self.assertEqual(attr.attribute_type_str, 'predefined')
        return

    def test_attribute_model_choices_json_parsing(self):
        """Test choices JSON parsing - complex data processing logic."""
        attr = ConcreteAttributeModel(
            name='test_attr',
            value_type_str='ENUM',
            attribute_type_str='CUSTOM'
        )
        
        # Test with dictionary format
        attr.value_range_str = json.dumps({'key1': 'Label 1', 'key2': 'Label 2'})
        choices = attr.choices()
        expected = [('key1', 'Label 1'), ('key2', 'Label 2')]
        self.assertEqual(choices, expected)
        
        # Test with list format
        attr.value_range_str = json.dumps(['option1', 'option2', 'option3'])
        choices = attr.choices()
        expected = [('option1', 'option1'), ('option2', 'option2'), ('option3', 'option3')]
        self.assertEqual(choices, expected)
        
        # Test with invalid JSON
        attr.value_range_str = 'invalid json {'
        choices = attr.choices()
        self.assertEqual(choices, {})  # Should return empty dict on parse error
        
        # Test with empty value_range_str
        attr.value_range_str = None
        choices = attr.choices()
        self.assertEqual(choices, [])
        return

    @patch('tt.apps.attribute.models.PredefinedValueRanges.get_choices')
    def test_attribute_model_choices_predefined_lookup(self, mock_get_choices):
        """Test choices predefined value range lookup - external integration logic."""
        mock_get_choices.return_value = [('pred1', 'Predefined 1'), ('pred2', 'Predefined 2')]
        
        attr = ConcreteAttributeModel(
            name='test_attr',
            value_type_str='ENUM',
            attribute_type_str='PREDEFINED',
            value_range_str='tt.test.choices'
        )
        
        choices = attr.choices()
        
        # Should use predefined choices, not parse JSON
        mock_get_choices.assert_called_once_with('tt.test.choices')
        self.assertEqual(choices, [('pred1', 'Predefined 1'), ('pred2', 'Predefined 2')])
        return

    @patch('tt.apps.attribute.models.generate_unique_filename')
    def test_attribute_model_file_save_logic(self, mock_generate_unique_filename):
        """Test file save logic with unique filename generation - complex file handling."""
        mock_generate_unique_filename.return_value = 'unique_test_file.txt'
        
        # Use isolated MEDIA_ROOT to prevent production pollution
        with self.isolated_media_root():
            # Create test file using base test utility
            test_file = self.create_test_text_file('test_file.txt', 'test content')
            
            attr = ConcreteAttributeModel(
                name='test_attr',
                value_type_str='FILE',
                attribute_type_str='CUSTOM'
            )
            attr.file_value = test_file
            # Ensure pk is None for new object behavior
            attr.pk = None
            
            # Mock the super().save() call to avoid database issues
            with patch('django.db.models.Model.save'):
                # Simulate calling save
                attr.save()
                
                # Should set upload_to and generate unique filename for new objects
                mock_generate_unique_filename.assert_called_once_with('test_file.txt')
                self.assertEqual(attr.value, 'test_file.txt')  # Value set to original filename
                self.assertEqual(attr.file_value.name, 'unique_test_file.txt')  # Name updated to unique
                self.assertEqual(attr.file_value.field.upload_to, 'test_attributes/')
        return

    @patch('tt.apps.attribute.models.default_storage')
    def test_attribute_model_file_deletion_missing_file(self, mock_storage):
        """Test file deletion when file doesn't exist - error handling."""
        mock_storage.exists.return_value = False
        
        # Create attribute with file reference that doesn't exist
        attr = ConcreteAttributeModel(
            name='test_attr',
            value_type_str='FILE',
            attribute_type_str='CUSTOM'
        )
        attr.file_value = 'nonexistent_file.txt'
        attr.pk = 1  # Set a fake primary key
        
        # Mock the delete operation to avoid database issues
        with patch('django.db.models.Model.delete'):
            attr.delete()
            
            # Should check existence but not try to delete
            mock_storage.exists.assert_called_once_with('nonexistent_file.txt')
            mock_storage.delete.assert_not_called()
        return

    @patch('tt.apps.attribute.models.default_storage')
    def test_attribute_model_file_deletion_exception_handling(self, mock_storage):
        """Test file deletion exception handling - resilient error handling."""
        mock_storage.exists.return_value = True
        mock_storage.delete.side_effect = Exception('Storage error')
        
        attr = ConcreteAttributeModel(
            name='test_attr',
            value_type_str='FILE',
            attribute_type_str='CUSTOM'
        )
        attr.file_value = 'test_file.txt'
        attr.pk = 1  # Set a fake primary key
        
        # Mock the delete operation to avoid database issues  
        with patch('django.db.models.Model.delete'):
            # Delete should not raise exception even if storage deletion fails
            attr.delete()
            
            mock_storage.exists.assert_called_once_with('test_file.txt')
            mock_storage.delete.assert_called_once_with('test_file.txt')
        return

    def test_attribute_model_abstract_upload_to_enforcement(self):
        """Test abstract get_upload_to method enforcement - critical for subclass contracts."""
        # Test that abstract method raises NotImplementedError
        # We use our concrete class but call parent method directly
        attr = ConcreteAttributeModel(
            name='test_attr',
            value_type_str='FILE',
            attribute_type_str='CUSTOM'
        )
        
        # Should raise NotImplementedError when calling parent method
        with self.assertRaises(NotImplementedError):
            AttributeModel.get_upload_to(attr)
        return

    def test_attribute_model_string_representation(self):
        """Test __str__ and __repr__ methods - important for debugging."""
        attr = ConcreteAttributeModel(
            name='test_attr',
            value='test_value',
            value_type_str='TEXT',
            attribute_type_str='CUSTOM'
        )
        
        str_repr = str(attr)
        self.assertIn('test_attr', str_repr)
        self.assertIn('test_value', str_repr)
        self.assertIn('TEXT', str_repr)
        self.assertIn('CUSTOM', str_repr)
        
        # __repr__ should equal __str__
        self.assertEqual(repr(attr), str(attr))
        return

