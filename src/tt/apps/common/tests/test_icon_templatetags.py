"""
Tests for icon template tags - security validation and rendering logic.

Focuses on high-value testing: icon name validation (security boundary),
size/color validation with fallback logic, template integration, and
protection against arbitrary file access.
"""
import logging
from unittest.mock import patch, Mock

from django.template import Template, Context, TemplateSyntaxError
from django.test import TestCase

from tt.apps.common.templatetags.icons import (
    icon, icon_list, has_icon,
    AVAILABLE_ICONS, ICON_SIZES, ICON_COLORS
)

logging.disable(logging.CRITICAL)


class IconTemplateTagSecurityTests(TestCase):
    """Test icon name validation - critical security boundary."""

    def test_icon_rejects_unavailable_icon_name(self):
        """Icon tag rejects names not in AVAILABLE_ICONS - prevents arbitrary file access."""
        with self.assertRaises(TemplateSyntaxError) as cm:
            icon('nonexistent-icon')

        error_msg = str(cm.exception)
        self.assertIn('nonexistent-icon', error_msg)
        self.assertIn('not available', error_msg)

    def test_icon_rejects_path_traversal_attempt(self):
        """Icon tag rejects path traversal attempts - security validation."""
        malicious_names = [
            '../../../etc/passwd',
            '../../settings.py',
            'icons/../../models',
            '..',
            '/',
        ]

        for malicious_name in malicious_names:
            with self.assertRaises(TemplateSyntaxError):
                icon(malicious_name)

    def test_icon_accepts_all_available_icons(self):
        """Icon tag accepts all icons in AVAILABLE_ICONS - whitelist validation."""
        # Test a representative sample of available icons
        test_icons = ['plus', 'edit', 'delete', 'home', 'settings']

        for icon_name in test_icons:
            if icon_name in AVAILABLE_ICONS:
                # Should not raise exception
                result = icon(icon_name)
                self.assertIsNotNone(result)

    def test_icon_name_case_sensitive(self):
        """Icon names are case-sensitive - exact match required."""
        # 'plus' exists, 'Plus' does not
        with self.assertRaises(TemplateSyntaxError):
            icon('Plus')

        with self.assertRaises(TemplateSyntaxError):
            icon('PLUS')


class IconValidationTests(TestCase):
    """Test size and color validation with fallback logic."""

    def test_icon_invalid_size_falls_back_to_md(self):
        """Invalid size falls back to 'md' - graceful degradation."""
        result = icon('plus', size='invalid')

        # Should render with 'md' size in classes
        self.assertIn('tt-icon-md', result)
        self.assertNotIn('tt-icon-invalid', result)

    def test_icon_valid_sizes_applied_correctly(self):
        """Valid sizes are applied correctly - validates all ICON_SIZES."""
        for size in ICON_SIZES:
            result = icon('plus', size=size)
            self.assertIn(f'tt-icon-{size}', result)

    def test_icon_default_size_is_md(self):
        """Default size is 'md' when not specified - default behavior."""
        result = icon('plus')
        self.assertIn('tt-icon-md', result)

    def test_icon_invalid_color_falls_back_to_none(self):
        """Invalid color falls back to None (no color class) - graceful degradation."""
        result = icon('plus', color='invalid')

        # Should not have invalid color class
        self.assertNotIn('tt-icon-invalid', result)
        # Should still render successfully
        self.assertIn('tt-icon', result)

    def test_icon_valid_colors_applied_correctly(self):
        """Valid colors are applied correctly - validates all ICON_COLORS."""
        for color in ICON_COLORS:
            result = icon('plus', color=color)
            self.assertIn(f'tt-icon-{color}', result)

    def test_icon_no_color_by_default(self):
        """No color class applied when color not specified - default behavior."""
        result = icon('plus')

        # Should not have any color-specific classes
        for color in ICON_COLORS:
            self.assertNotIn(f'tt-icon-{color}', result)


class IconAccessibilityTests(TestCase):
    """Test accessibility attribute generation - important for UX."""

    def test_icon_with_aria_label_is_meaningful(self):
        """Icon with aria_label gets role='img' and label - meaningful icon."""
        result = icon('plus', aria_label='Add item')

        # Attributes are HTML-encoded in output
        self.assertIn('aria-label=&quot;Add item&quot;', result)
        self.assertIn('role=&quot;img&quot;', result)
        self.assertNotIn('aria-hidden', result)

    def test_icon_without_aria_label_is_decorative(self):
        """Icon without aria_label gets aria-hidden - decorative icon."""
        result = icon('plus')

        # Attributes are HTML-encoded in output
        self.assertIn('aria-hidden=&quot;true&quot;', result)
        self.assertNotIn('aria-label', result)
        self.assertNotIn('role=&quot;img&quot;', result)

    def test_icon_with_title_attribute(self):
        """Icon with title gets title attribute - tooltip support."""
        result = icon('plus', title='Add new item')

        # Attributes are HTML-encoded in output
        self.assertIn('title=&quot;Add new item&quot;', result)

    def test_icon_without_title_has_no_title_attr(self):
        """Icon without title has no title attribute - clean output."""
        result = icon('plus')

        self.assertNotIn('title=', result)

    def test_icon_with_both_aria_label_and_title(self):
        """Icon can have both aria_label and title - accessibility + tooltip."""
        result = icon('plus', aria_label='Add item', title='Click to add new item')

        # Attributes are HTML-encoded in output
        self.assertIn('aria-label=&quot;Add item&quot;', result)
        self.assertIn('title=&quot;Click to add new item&quot;', result)
        self.assertIn('role=&quot;img&quot;', result)


class IconCssClassTests(TestCase):
    """Test CSS class generation logic."""

    def test_icon_base_classes_always_present(self):
        """Icon always has base 'tt-icon' class - consistent styling."""
        result = icon('plus')

        self.assertIn('tt-icon', result)

    def test_icon_custom_css_class_added(self):
        """Custom CSS class is added to icon - extensibility."""
        result = icon('plus', css_class='my-custom-class')

        self.assertIn('my-custom-class', result)
        self.assertIn('tt-icon', result)  # Base class still present

    def test_icon_multiple_classes_combined(self):
        """All applicable classes are combined correctly - class composition."""
        result = icon('plus', size='lg', color='primary', css_class='custom')

        # Should have all classes
        self.assertIn('tt-icon', result)
        self.assertIn('tt-icon-lg', result)
        self.assertIn('tt-icon-primary', result)
        self.assertIn('custom', result)


class IconTemplateLoadingTests(TestCase):
    """Test template loading and fallback behavior."""

    @patch('tt.apps.common.templatetags.icons.get_template')
    def test_icon_loads_specific_template(self, mock_get_template):
        """Icon tag loads the specific icon template - template integration."""
        mock_template = Mock()
        mock_template.render.return_value = '<svg>test</svg>'
        mock_get_template.return_value = mock_template

        result = icon('plus')

        # Should load the plus icon template
        mock_get_template.assert_called_once_with('icons/plus.html')
        self.assertIn('<svg>test</svg>', result)

    @patch('tt.apps.common.templatetags.icons.get_template')
    def test_icon_fallback_when_template_missing(self, mock_get_template):
        """Icon provides fallback when template doesn't exist - error handling."""
        from django.template import TemplateDoesNotExist
        mock_get_template.side_effect = TemplateDoesNotExist('icons/plus.html')

        result = icon('plus')

        # Should return fallback with icon name
        self.assertIn('[plus]', result)
        self.assertIn('tt-icon', result)
        self.assertIn('aria-hidden="true"', result)

    @patch('tt.apps.common.templatetags.icons.get_template')
    def test_icon_template_receives_correct_context(self, mock_get_template):
        """Icon template receives class_attr and accessibility_attrs - context data."""
        mock_template = Mock()
        mock_template.render.return_value = '<svg>test</svg>'
        mock_get_template.return_value = mock_template

        icon('plus', size='lg', color='primary', aria_label='Add')

        # Check that render was called with correct context
        call_args = mock_template.render.call_args
        context = call_args[0][0]

        self.assertIn('class_attr', context)
        self.assertIn('accessibility_attrs', context)
        self.assertIn('tt-icon-lg', context['class_attr'])
        self.assertIn('tt-icon-primary', context['class_attr'])
        self.assertIn('aria-label="Add"', context['accessibility_attrs'])


class IconListTagTests(TestCase):
    """Test icon_list template tag - utility function."""

    def test_icon_list_returns_sorted_list(self):
        """icon_list returns sorted list of available icons - documentation helper."""
        result = icon_list()

        self.assertIsInstance(result, list)
        self.assertEqual(result, sorted(result))  # Should be sorted
        self.assertGreater(len(result), 0)  # Should have icons

    def test_icon_list_contains_known_icons(self):
        """icon_list contains known available icons - completeness check."""
        result = icon_list()

        # Check a few known icons are in the list
        known_icons = ['plus', 'edit', 'delete', 'home']
        for icon_name in known_icons:
            self.assertIn(icon_name, result)

    def test_icon_list_matches_available_icons(self):
        """icon_list matches AVAILABLE_ICONS constant - consistency."""
        result = icon_list()

        self.assertEqual(set(result), AVAILABLE_ICONS)


class HasIconFilterTests(TestCase):
    """Test has_icon template filter - availability checking."""

    def test_has_icon_returns_true_for_available_icons(self):
        """has_icon returns True for available icons - positive case."""
        self.assertTrue(has_icon('plus'))
        self.assertTrue(has_icon('edit'))
        self.assertTrue(has_icon('delete'))

    def test_has_icon_returns_false_for_unavailable_icons(self):
        """has_icon returns False for unavailable icons - negative case."""
        self.assertFalse(has_icon('nonexistent'))
        self.assertFalse(has_icon('fake-icon'))
        self.assertFalse(has_icon(''))

    def test_has_icon_case_sensitive(self):
        """has_icon is case-sensitive - exact match required."""
        self.assertTrue(has_icon('plus'))
        self.assertFalse(has_icon('Plus'))
        self.assertFalse(has_icon('PLUS'))


class IconTemplateIntegrationTests(TestCase):
    """Test icon tags in actual template rendering."""

    def test_icon_tag_in_template(self):
        """Icon tag works in template rendering - integration test."""
        template_str = """
        {% load icons %}
        {% icon "plus" size="lg" color="primary" %}
        """

        template = Template(template_str)
        context = Context({})

        rendered = template.render(context)

        self.assertIn('tt-icon', rendered)
        self.assertIn('tt-icon-lg', rendered)
        self.assertIn('tt-icon-primary', rendered)

    def test_icon_tag_with_variables_in_template(self):
        """Icon tag works with template variables - dynamic usage."""
        template_str = """
        {% load icons %}
        {% icon icon_name size=icon_size color=icon_color %}
        """

        template = Template(template_str)
        context = Context({
            'icon_name': 'edit',
            'icon_size': 'md',
            'icon_color': 'success',
        })

        rendered = template.render(context)

        self.assertIn('tt-icon', rendered)
        self.assertIn('tt-icon-md', rendered)
        self.assertIn('tt-icon-success', rendered)

    def test_has_icon_filter_in_template(self):
        """has_icon filter works in template conditionals - conditional rendering."""
        template_str = """
        {% load icons %}
        {% if 'plus'|has_icon %}YES{% else %}NO{% endif %}
        {% if 'fake'|has_icon %}YES{% else %}NO{% endif %}
        """

        template = Template(template_str)
        context = Context({})

        rendered = template.render(context).strip()

        # First check should be YES, second should be NO
        self.assertIn('YES', rendered)
        self.assertIn('NO', rendered)

    def test_icon_list_tag_in_template(self):
        """icon_list tag works in template - listing icons."""
        template_str = """
        {% load icons %}
        {% icon_list as icons %}
        {{ icons|length }}
        """

        template = Template(template_str)
        context = Context({})

        rendered = template.render(context).strip()

        # Should show count of available icons
        icon_count = len(AVAILABLE_ICONS)
        self.assertIn(str(icon_count), rendered)

    def test_icon_tag_invalid_name_raises_error(self):
        """Icon tag with invalid name raises TemplateSyntaxError - error handling."""
        template_str = """
        {% load icons %}
        {% icon "invalid-icon-name" %}
        """

        # Template parsing should succeed
        template = Template(template_str)
        context = Context({})

        # But rendering should raise TemplateSyntaxError
        with self.assertRaises(TemplateSyntaxError):
            template.render(context)
