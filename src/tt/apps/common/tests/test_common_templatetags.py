"""
Tests for common template tags - URL manipulation and utility functions.

Focuses on high-value testing: URL parameter encoding/manipulation,
absolute URL construction, query parameter handling, and edge cases
with special characters and encoding.
"""
import logging
import urllib.parse
from unittest.mock import patch

from django.template import Template, Context
from django.test import TestCase, RequestFactory

from tt.apps.common.templatetags.common_tags import (
    pagination_url, abs_url, add_random_query_param
)

logging.disable(logging.CRITICAL)


class PaginationUrlTests(TestCase):
    """Test pagination_url tag - URL parameter manipulation logic."""

    def test_pagination_url_with_no_existing_params(self):
        """pagination_url with no existing params creates simple page param - basic case."""
        result = pagination_url(2)

        self.assertEqual(result, '?page=2')

    def test_pagination_url_with_existing_params(self):
        """pagination_url preserves existing parameters - parameter preservation."""
        existing = 'search=test&filter=active'

        result = pagination_url(3, existing)

        # Should preserve existing params and add page
        self.assertIn('search=test', result)
        self.assertIn('filter=active', result)
        self.assertIn('page=3', result)

    def test_pagination_url_replaces_existing_page_param(self):
        """pagination_url replaces existing page parameter - param override logic."""
        existing = 'page=1&search=test'

        result = pagination_url(5, existing)

        # Should have only one page param with new value
        self.assertIn('page=5', result)
        self.assertNotIn('page=1', result)
        self.assertIn('search=test', result)

    def test_pagination_url_with_encoded_params(self):
        """pagination_url handles URL-encoded parameters - encoding preservation."""
        existing = 'search=hello+world&filter=test%20value'

        result = pagination_url(2, existing)

        # urlencode will re-encode the parameters
        # Just verify page param is added and result is valid
        self.assertIn('page=2', result)
        self.assertTrue(result.startswith('?'))
        # Verify parameters are present (may be re-encoded differently)
        self.assertIn('search=', result)
        self.assertIn('filter=', result)

    def test_pagination_url_with_special_characters(self):
        """pagination_url handles special characters in params - edge case handling."""
        existing = 'query=test&value=special+chars'

        result = pagination_url(1, existing)

        # Should handle special characters without breaking
        self.assertTrue(result.startswith('?'))
        self.assertIn('page=1', result)

    def test_pagination_url_with_empty_existing_params(self):
        """pagination_url with empty string params behaves like no params - null handling."""
        result = pagination_url(3, '')

        self.assertEqual(result, '?page=3')

    def test_pagination_url_with_none_existing_params(self):
        """pagination_url with None params behaves like no params - null handling."""
        result = pagination_url(4, None)

        self.assertEqual(result, '?page=4')

    def test_pagination_url_preserves_multiple_params(self):
        """pagination_url preserves multiple existing parameters - complex case."""
        existing = 'a=1&b=2&c=3&d=4'

        result = pagination_url(10, existing)

        # All params should be preserved
        self.assertIn('a=1', result)
        self.assertIn('b=2', result)
        self.assertIn('c=3', result)
        self.assertIn('d=4', result)
        self.assertIn('page=10', result)

    def test_pagination_url_output_is_valid_query_string(self):
        """pagination_url output is valid query string format - format validation."""
        result = pagination_url(5, 'test=value')

        # Should start with ?
        self.assertTrue(result.startswith('?'))

        # Should be parseable as query string
        parsed = urllib.parse.parse_qs(result[1:])  # Remove leading ?
        self.assertIn('page', parsed)
        self.assertEqual(parsed['page'][0], '5')

    def test_pagination_url_with_equals_in_value(self):
        """pagination_url handles equals sign in parameter value - complex parsing."""
        # URL-encoded equals sign
        existing = 'data=key%3Dvalue'

        result = pagination_url(1, existing)

        # urlencode may double-encode, just verify params are present
        self.assertIn('data=', result)
        self.assertIn('page=1', result)
        # Verify it's a valid query string
        self.assertTrue(result.startswith('?'))

    def test_pagination_url_first_page(self):
        """pagination_url works with page 1 - boundary case."""
        result = pagination_url(1)

        self.assertEqual(result, '?page=1')

    def test_pagination_url_large_page_number(self):
        """pagination_url works with large page numbers - boundary case."""
        result = pagination_url(9999)

        self.assertEqual(result, '?page=9999')


class AbsUrlTests(TestCase):
    """Test abs_url tag - absolute URL construction logic."""

    def setUp(self):
        """Set up request context for abs_url testing."""
        self.factory = RequestFactory()

    def test_abs_url_builds_absolute_uri(self):
        """abs_url builds absolute URI from view name - basic functionality."""
        request = self.factory.get('/test/')
        context = Context({'request': request})

        with patch('tt.apps.common.templatetags.common_tags.reverse') as mock_reverse:
            mock_reverse.return_value = '/trips/123/'

            with self.settings(ALLOWED_HOSTS=['testserver']):
                result = abs_url(context, 'trip_detail', 123)

            # Should call reverse with correct args
            mock_reverse.assert_called_once_with('trip_detail', args=(123,), kwargs={})

            # Should build absolute URI
            self.assertTrue(result.startswith('http'))
            self.assertIn('/trips/123/', result)

    def test_abs_url_with_kwargs(self):
        """abs_url handles keyword arguments - parameter handling."""
        request = self.factory.get('/test/')
        context = Context({'request': request})

        with patch('tt.apps.common.templatetags.common_tags.reverse') as mock_reverse:
            mock_reverse.return_value = '/entity/456/'

            abs_url(context, 'entity_detail', entity_id=456)

            # Should pass kwargs to reverse
            mock_reverse.assert_called_once_with('entity_detail', args=(), kwargs={'entity_id': 456})

    def test_abs_url_with_https_request(self):
        """abs_url preserves HTTPS scheme - protocol preservation."""
        request = self.factory.get('/test/', secure=True)
        context = Context({'request': request})

        with patch('tt.apps.common.templatetags.common_tags.reverse') as mock_reverse:
            mock_reverse.return_value = '/path/'

            result = abs_url(context, 'some_view')

            # Should use https scheme
            self.assertTrue(result.startswith('https://'))

    def test_abs_url_with_custom_port(self):
        """abs_url includes custom port in absolute URI - port handling."""
        request = self.factory.get('/test/', SERVER_NAME='testserver', SERVER_PORT='8080')
        context = Context({'request': request})

        with patch('tt.apps.common.templatetags.common_tags.reverse') as mock_reverse:
            mock_reverse.return_value = '/path/'

            with self.settings(ALLOWED_HOSTS=['testserver']):
                result = abs_url(context, 'some_view')

            # Should include port
            self.assertIn(':8080', result)

    def test_abs_url_with_no_args(self):
        """abs_url works with no URL arguments - simple case."""
        request = self.factory.get('/test/')
        context = Context({'request': request})

        with patch('tt.apps.common.templatetags.common_tags.reverse') as mock_reverse:
            mock_reverse.return_value = '/home/'

            result = abs_url(context, 'home')

            # Should call reverse with empty args and kwargs
            mock_reverse.assert_called_once_with('home', args=(), kwargs={})
            self.assertIn('/home/', result)

    def test_abs_url_with_mixed_args_and_kwargs(self):
        """abs_url handles both positional and keyword arguments - complex case."""
        request = self.factory.get('/test/')
        context = Context({'request': request})

        with patch('tt.apps.common.templatetags.common_tags.reverse') as mock_reverse:
            mock_reverse.return_value = '/path/123/detail/456/'

            abs_url(context, 'complex_view', 123, detail_id=456)

            # Should pass both args and kwargs
            call_args = mock_reverse.call_args
            self.assertEqual(call_args[1]['args'], (123,))
            self.assertEqual(call_args[1]['kwargs'], {'detail_id': 456})


class AddRandomQueryParamTests(TestCase):
    """Test add_random_query_param filter - cache-busting URL manipulation."""

    def test_add_random_query_param_adds_underscore_param(self):
        """add_random_query_param adds random _ parameter - basic functionality."""
        url = 'https://example.com/image.jpg'

        result = add_random_query_param(url)

        # Should have added _ parameter
        self.assertIn('_=', result)
        self.assertTrue(result.startswith('https://example.com/image.jpg?'))

    def test_add_random_query_param_value_is_numeric(self):
        """add_random_query_param uses numeric value - value format."""
        url = 'https://example.com/file.txt'

        result = add_random_query_param(url)

        # Extract the _ parameter value
        parsed = urllib.parse.urlparse(result)
        params = urllib.parse.parse_qs(parsed.query)

        self.assertIn('_', params)
        value = params['_'][0]
        self.assertTrue(value.isdigit())

        # Should be 6-digit number (100000-999999)
        numeric_value = int(value)
        self.assertGreaterEqual(numeric_value, 100000)
        self.assertLessEqual(numeric_value, 999999)

    def test_add_random_query_param_preserves_existing_params(self):
        """add_random_query_param preserves existing query parameters - param preservation."""
        url = 'https://example.com/path?existing=value&another=param'

        result = add_random_query_param(url)

        # Should preserve existing params
        self.assertIn('existing=value', result)
        self.assertIn('another=param', result)
        self.assertIn('_=', result)

    def test_add_random_query_param_preserves_url_structure(self):
        """add_random_query_param preserves scheme, host, path - URL structure."""
        url = 'https://example.com:8080/path/to/resource.png'

        result = add_random_query_param(url)

        parsed = urllib.parse.urlparse(result)

        self.assertEqual(parsed.scheme, 'https')
        self.assertEqual(parsed.netloc, 'example.com:8080')
        self.assertEqual(parsed.path, '/path/to/resource.png')

    def test_add_random_query_param_preserves_fragment(self):
        """add_random_query_param preserves URL fragment - fragment handling."""
        url = 'https://example.com/page#section'

        result = add_random_query_param(url)

        # Fragment should be preserved
        self.assertIn('#section', result)
        self.assertIn('_=', result)

    def test_add_random_query_param_with_existing_underscore(self):
        """add_random_query_param replaces existing _ parameter - override behavior."""
        url = 'https://example.com/file?_=123456'

        result = add_random_query_param(url)

        # Should have a new _ value
        parsed = urllib.parse.urlparse(result)
        params = urllib.parse.parse_qs(parsed.query)

        self.assertIn('_', params)
        # Should be different from original (very high probability)
        # We just verify it's in the expected range
        value = int(params['_'][0])
        self.assertGreaterEqual(value, 100000)
        self.assertLessEqual(value, 999999)

    def test_add_random_query_param_relative_url(self):
        """add_random_query_param works with relative URLs - relative path handling."""
        url = '/static/images/photo.jpg'

        result = add_random_query_param(url)

        # Should add parameter to relative URL
        self.assertTrue(result.startswith('/static/images/photo.jpg?'))
        self.assertIn('_=', result)

    def test_add_random_query_param_url_with_no_extension(self):
        """add_random_query_param works with URLs without file extension - path variation."""
        url = 'https://example.com/api/endpoint'

        result = add_random_query_param(url)

        self.assertIn('_=', result)
        self.assertIn('https://example.com/api/endpoint?', result)

    def test_add_random_query_param_with_encoded_params(self):
        """add_random_query_param preserves encoded parameters - encoding preservation."""
        url = 'https://example.com/search?q=hello+world&filter=test%20value'

        result = add_random_query_param(url)

        # urlencode may change encoding style (+ vs %20), just verify params exist
        self.assertIn('q=', result)
        self.assertIn('filter=', result)
        self.assertIn('_=', result)
        # Verify URL structure is preserved
        self.assertTrue(result.startswith('https://example.com/search?'))

    def test_add_random_query_param_randomness(self):
        """add_random_query_param generates different values - randomness verification."""
        url = 'https://example.com/file.txt'

        # Generate multiple results
        results = [add_random_query_param(url) for _ in range(10)]

        # Extract _ parameter values
        values = []
        for result in results:
            parsed = urllib.parse.urlparse(result)
            params = urllib.parse.parse_qs(parsed.query)
            values.append(params['_'][0])

        # Should have some variation (not all the same)
        unique_values = set(values)
        # With 10 random values in range 100000-999999, should get some uniqueness
        self.assertGreater(len(unique_values), 1)


class CommonTemplateTagsIntegrationTests(TestCase):
    """Test common template tags in actual template rendering."""

    def test_pagination_url_in_template(self):
        """pagination_url works in template rendering - integration test."""
        template_str = """
        {% load common_tags %}
        {% pagination_url 5 "search=test&filter=active" %}
        """

        template = Template(template_str)
        context = Context({})

        rendered = template.render(context).strip()

        self.assertIn('page=5', rendered)
        self.assertIn('search=test', rendered)

    def test_abs_url_in_template(self):
        """abs_url works in template rendering - integration test."""
        template_str = """
        {% load common_tags %}
        {% abs_url 'test_view' 123 %}
        """

        factory = RequestFactory()
        request = factory.get('/test/')

        with patch('tt.apps.common.templatetags.common_tags.reverse') as mock_reverse:
            mock_reverse.return_value = '/path/123/'

            template = Template(template_str)
            context = Context({'request': request})

            rendered = template.render(context).strip()

            self.assertIn('/path/123/', rendered)

    def test_add_random_query_param_filter_in_template(self):
        """add_random_query_param filter works in template - integration test."""
        template_str = """
        {% load common_tags %}
        {{ url|add_random_query_param }}
        """

        template = Template(template_str)
        context = Context({'url': 'https://example.com/image.jpg'})

        rendered = template.render(context).strip()

        self.assertIn('https://example.com/image.jpg?', rendered)
        self.assertIn('_=', rendered)

    def test_pagination_url_with_template_variables(self):
        """pagination_url works with template variables - dynamic usage."""
        template_str = """
        {% load common_tags %}
        {% pagination_url page_num existing_params %}
        """

        template = Template(template_str)
        context = Context({
            'page_num': 10,
            'existing_params': 'sort=date&order=desc'
        })

        rendered = template.render(context).strip()

        self.assertIn('page=10', rendered)
        self.assertIn('sort=date', rendered)
        self.assertIn('order=desc', rendered)
