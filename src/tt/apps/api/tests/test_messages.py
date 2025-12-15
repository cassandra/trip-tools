"""
Tests for API message helpers.

Focuses on high-value testing of:
- Parameterized message inclusion (params appear in output)
- NOT testing exact message wording (to allow message changes without breaking tests)
"""
import logging

from django.test import TestCase

from tt.apps.api.messages import APIMessages

logging.disable(logging.CRITICAL)


class APIMessagesParameterizedTestCase(TestCase):
    """Test APIMessages parameterized helper methods."""

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
            self.assertIn(field, result)

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
            self.assertIn(resource, result)

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
            self.assertIn(resource, result)
            self.assertIn(field, result)
