"""
Tests for API message helpers.

Focuses on high-value testing of:
- Message type contracts (methods return strings)
- Parameterized message inclusion (params appear in output)
- NOT testing exact message wording (to allow message changes without breaking tests)
"""
import logging

from django.test import TestCase

from tt.apps.api.messages import APIMessages

logging.disable(logging.CRITICAL)


class APIMessagesParameterizedTestCase(TestCase):
    """Test APIMessages parameterized helper methods."""

    def test_is_required_returns_string(self):
        """Test is_required returns a string (type contract)."""
        result = APIMessages.is_required('Token name')
        self.assertIsInstance(result, str)

    def test_is_required_includes_field_name(self):
        """Test is_required includes the field name in the message."""
        field = 'Token name'
        result = APIMessages.is_required(field)
        self.assertIn(field, result)

    def test_is_required_works_with_different_field_names(self):
        """Test is_required works with various field names."""
        test_fields = ['Email', 'Password', 'API Token', 'User ID']

        for field in test_fields:
            result = APIMessages.is_required(field)
            self.assertIsInstance(result, str)
            self.assertIn(field, result)

    def test_not_found_returns_string(self):
        """Test not_found returns a string (type contract)."""
        result = APIMessages.not_found('User')
        self.assertIsInstance(result, str)

    def test_not_found_includes_resource_name(self):
        """Test not_found includes the resource name in the message."""
        resource = 'User'
        result = APIMessages.not_found(resource)
        self.assertIn(resource, result)

    def test_not_found_works_with_different_resources(self):
        """Test not_found works with various resource names."""
        test_resources = ['User', 'Token', 'Trip', 'Journal']

        for resource in test_resources:
            result = APIMessages.not_found(resource)
            self.assertIsInstance(result, str)
            self.assertIn(resource, result)

    def test_already_exists_returns_string(self):
        """Test already_exists returns a string (type contract)."""
        result = APIMessages.already_exists('Token', 'name')
        self.assertIsInstance(result, str)

    def test_already_exists_includes_resource_and_field(self):
        """Test already_exists includes both resource and field in the message."""
        resource = 'Token'
        field = 'name'
        result = APIMessages.already_exists(resource, field)

        # Both parameters should appear in the message
        self.assertIn(resource, result)
        self.assertIn(field, result)

    def test_already_exists_works_with_different_params(self):
        """Test already_exists works with various resource/field combinations."""
        test_cases = [
            ('Token', 'name'),
            ('User', 'email'),
            ('Trip', 'title'),
            ('Journal', 'slug'),
        ]

        for resource, field in test_cases:
            result = APIMessages.already_exists(resource, field)
            self.assertIsInstance(result, str)
            self.assertIn(resource, result)
            self.assertIn(field, result)


class APIMessagesStaticTestCase(TestCase):
    """Test APIMessages static message attributes."""

    def test_invalid_token_is_string(self):
        """Test INVALID_TOKEN is a string (type contract)."""
        self.assertIsInstance(APIMessages.INVALID_TOKEN, str)

    def test_invalid_token_is_not_empty(self):
        """Test INVALID_TOKEN is not empty."""
        self.assertGreater(len(APIMessages.INVALID_TOKEN), 0)

    def test_user_inactive_is_string(self):
        """Test USER_INACTIVE is a string (type contract)."""
        self.assertIsInstance(APIMessages.USER_INACTIVE, str)

    def test_user_inactive_is_not_empty(self):
        """Test USER_INACTIVE is not empty."""
        self.assertGreater(len(APIMessages.USER_INACTIVE), 0)

    def test_bad_request_is_string(self):
        """Test BAD_REQUEST is a string (type contract)."""
        self.assertIsInstance(APIMessages.BAD_REQUEST, str)

    def test_bad_request_is_not_empty(self):
        """Test BAD_REQUEST is not empty."""
        self.assertGreater(len(APIMessages.BAD_REQUEST), 0)


class APIMessagesEdgeCasesTestCase(TestCase):
    """Test APIMessages edge cases and boundary conditions."""

    def test_is_required_with_empty_string(self):
        """Test is_required handles empty string field name."""
        result = APIMessages.is_required('')
        self.assertIsInstance(result, str)
        # Should still return a valid message even with empty field

    def test_is_required_with_special_characters(self):
        """Test is_required handles field names with special characters."""
        result = APIMessages.is_required('API Token (v2)')
        self.assertIsInstance(result, str)
        self.assertIn('API Token (v2)', result)

    def test_not_found_with_empty_string(self):
        """Test not_found handles empty string resource name."""
        result = APIMessages.not_found('')
        self.assertIsInstance(result, str)

    def test_already_exists_with_empty_strings(self):
        """Test already_exists handles empty string parameters."""
        result = APIMessages.already_exists('', '')
        self.assertIsInstance(result, str)

    def test_already_exists_with_special_characters(self):
        """Test already_exists handles parameters with special characters."""
        result = APIMessages.already_exists('API Token (v2)', 'name/id')
        self.assertIsInstance(result, str)
        self.assertIn('API Token (v2)', result)
        self.assertIn('name/id', result)
