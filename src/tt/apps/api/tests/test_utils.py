"""
Tests for API utility functions.

Focuses on high-value testing of:
- Dict value extraction with defaults
- UUID parsing and validation
"""
import logging
from uuid import UUID

from django.test import TestCase

from tt.apps.api.utils import get_str, get_uuid

logging.disable(logging.CRITICAL)


class GetStrTestCase(TestCase):
    """Test get_str utility function."""

    def test_get_str_extracts_value_from_dict(self):
        """Test get_str extracts string value from dictionary."""
        data = {'name': 'Test Name'}
        result = get_str(data, 'name')
        self.assertEqual(result, 'Test Name')

    def test_get_str_strips_whitespace(self):
        """Test get_str strips whitespace from extracted value."""
        data = {'name': '  Test Name  '}
        result = get_str(data, 'name')
        self.assertEqual(result, 'Test Name')

    def test_get_str_returns_default_for_missing_key(self):
        """Test get_str returns default value when key is missing."""
        data = {'other_key': 'value'}
        result = get_str(data, 'name', default='default_value')
        self.assertEqual(result, 'default_value')

    def test_get_str_returns_empty_string_default_when_not_specified(self):
        """Test get_str returns empty string by default for missing key."""
        data = {'other_key': 'value'}
        result = get_str(data, 'name')
        self.assertEqual(result, '')

    def test_get_str_returns_default_for_none_value(self):
        """Test get_str returns default when value is None."""
        data = {'name': None}
        result = get_str(data, 'name', default='default_value')
        self.assertEqual(result, 'default_value')

    def test_get_str_converts_non_string_to_string(self):
        """Test get_str converts non-string values to strings."""
        data = {'count': 123}
        result = get_str(data, 'count')
        self.assertEqual(result, '123')

    def test_get_str_converts_boolean_to_string(self):
        """Test get_str converts boolean values to strings."""
        data = {'is_active': True}
        result = get_str(data, 'is_active')
        self.assertEqual(result, 'True')

    def test_get_str_strips_after_conversion(self):
        """Test get_str strips whitespace after type conversion."""
        data = {'value': 42}  # Will become '42' after str()
        result = get_str(data, 'value')
        self.assertEqual(result, '42')

    def test_get_str_handles_empty_string_value(self):
        """Test get_str handles empty string values correctly."""
        data = {'name': ''}
        result = get_str(data, 'name', default='default')
        # Empty string is a valid value, not None, so it should return empty string
        self.assertEqual(result, '')

    def test_get_str_handles_whitespace_only_value(self):
        """Test get_str strips whitespace-only values to empty string."""
        data = {'name': '   '}
        result = get_str(data, 'name')
        self.assertEqual(result, '')


class GetUuidTestCase(TestCase):
    """Test get_uuid utility function."""

    def test_get_uuid_parses_valid_uuid(self):
        """Test get_uuid successfully parses valid UUID string."""
        uuid_str = '123e4567-e89b-12d3-a456-426614174000'
        data = {'entity_id': uuid_str}
        result = get_uuid(data, 'entity_id')

        self.assertIsInstance(result, UUID)
        self.assertEqual(str(result), uuid_str)

    def test_get_uuid_parses_uuid_without_hyphens(self):
        """Test get_uuid parses UUID without hyphens."""
        uuid_str = '123e4567e89b12d3a456426614174000'
        data = {'entity_id': uuid_str}
        result = get_uuid(data, 'entity_id')

        self.assertIsInstance(result, UUID)
        self.assertEqual(result.hex, uuid_str)

    def test_get_uuid_strips_whitespace_before_parsing(self):
        """Test get_uuid strips whitespace before parsing UUID."""
        uuid_str = '  123e4567-e89b-12d3-a456-426614174000  '
        data = {'entity_id': uuid_str}
        result = get_uuid(data, 'entity_id')

        self.assertIsInstance(result, UUID)
        self.assertEqual(str(result), uuid_str.strip())

    def test_get_uuid_returns_none_for_missing_key(self):
        """Test get_uuid returns None when key is missing."""
        data = {'other_key': 'value'}
        result = get_uuid(data, 'entity_id')

        self.assertIsNone(result)

    def test_get_uuid_returns_none_for_none_value(self):
        """Test get_uuid returns None when value is None."""
        data = {'entity_id': None}
        result = get_uuid(data, 'entity_id')

        self.assertIsNone(result)

    def test_get_uuid_returns_none_for_empty_string(self):
        """Test get_uuid returns None for empty string."""
        data = {'entity_id': ''}
        result = get_uuid(data, 'entity_id')

        self.assertIsNone(result)

    def test_get_uuid_returns_none_for_whitespace_only(self):
        """Test get_uuid returns None for whitespace-only string."""
        data = {'entity_id': '   '}
        result = get_uuid(data, 'entity_id')

        self.assertIsNone(result)

    def test_get_uuid_returns_none_for_invalid_format(self):
        """Test get_uuid returns None for invalid UUID format."""
        data = {'entity_id': 'not-a-valid-uuid'}
        result = get_uuid(data, 'entity_id')

        self.assertIsNone(result)

    def test_get_uuid_returns_none_for_malformed_uuid(self):
        """Test get_uuid returns None for malformed UUID string."""
        data = {'entity_id': '123e4567-e89b-12d3-a456-42661417400'}  # One char short
        result = get_uuid(data, 'entity_id')

        self.assertIsNone(result)

    def test_get_uuid_converts_non_string_to_string_before_parsing(self):
        """Test get_uuid converts non-string values to string before parsing."""
        # Unlikely scenario, but tests the str(value) conversion
        uuid_str = '123e4567-e89b-12d3-a456-426614174000'

        # Create a mock object that converts to UUID string
        class MockUuidValue:
            def __str__(self):
                return uuid_str

        data = {'entity_id': MockUuidValue()}
        result = get_uuid(data, 'entity_id')

        self.assertIsInstance(result, UUID)
        self.assertEqual(str(result), uuid_str)

    def test_get_uuid_handles_uppercase_uuid(self):
        """Test get_uuid handles uppercase UUID strings."""
        uuid_str = '123E4567-E89B-12D3-A456-426614174000'
        data = {'entity_id': uuid_str}
        result = get_uuid(data, 'entity_id')

        self.assertIsInstance(result, UUID)
        # UUID normalizes to lowercase
        self.assertEqual(str(result), uuid_str.lower())
