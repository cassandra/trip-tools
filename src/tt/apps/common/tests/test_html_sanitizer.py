"""
Tests for HTML sanitization utilities.

Ensures that user-generated HTML is properly sanitized to prevent XSS
while preserving allowed rich text formatting.
"""
from django.test import TestCase

from tt.apps.common.html_sanitizer import HTMLSanitizer, sanitize_rich_text_html


class HTMLSanitizerTests(TestCase):
    """Test cases for the HTMLSanitizer utility."""

    def test_sanitize_basic_allowed_tags(self):
        """Test that basic allowed tags are preserved."""
        html = '<p>Hello <strong>world</strong> with <em>emphasis</em></p>'
        result = sanitize_rich_text_html(html)
        self.assertEqual(result, html)

    def test_sanitize_headings(self):
        """Test that heading tags are preserved."""
        html = '<h1>Title</h1><h2>Subtitle</h2><h3>Section</h3>'
        result = sanitize_rich_text_html(html)
        self.assertEqual(result, html)

    def test_sanitize_lists(self):
        """Test that list tags are preserved."""
        html = '<ul><li>Item 1</li><li>Item 2</li></ul>'
        result = sanitize_rich_text_html(html)
        self.assertEqual(result, html)

    def test_sanitize_code_blocks(self):
        """Test that code and pre tags are preserved."""
        html = '<pre><code>console.log("test");</code></pre>'
        result = sanitize_rich_text_html(html)
        self.assertEqual(result, html)

    def test_sanitize_blockquote(self):
        """Test that blockquote tags are preserved."""
        html = '<blockquote>Famous quote here</blockquote>'
        result = sanitize_rich_text_html(html)
        self.assertEqual(result, html)

    def test_sanitize_links_with_allowed_attributes(self):
        """Test that links with href are preserved."""
        html = '<a href="https://example.com">Link</a>'
        result = sanitize_rich_text_html(html)
        self.assertEqual(result, html)

    def test_sanitize_images_with_allowed_attributes(self):
        """Test that images with allowed attributes are preserved."""
        html = '<img src="image.jpg" alt="Description" data-uuid="123" data-layout="full">'
        result = sanitize_rich_text_html(html)
        self.assertIn('src="image.jpg"', result)
        self.assertIn('alt="Description"', result)
        self.assertIn('data-uuid="123"', result)
        self.assertIn('data-layout="full"', result)

    def test_sanitize_removes_script_tags(self):
        """Test that script tags are removed (content is stripped by default)."""
        html = '<p>Safe content</p><script>alert("XSS")</script>'
        result = sanitize_rich_text_html(html)
        self.assertNotIn('<script>', result)
        self.assertNotIn('</script>', result)
        self.assertIn('Safe content', result)
        # Note: Bleach strips tags by default, content may remain

    def test_sanitize_removes_onclick_attributes(self):
        """Test that onclick and other event handlers are removed."""
        html = '<p onclick="alert(\'XSS\')">Click me</p>'
        result = sanitize_rich_text_html(html)
        self.assertNotIn('onclick', result)
        self.assertIn('Click me', result)

    def test_sanitize_removes_style_tags(self):
        """Test that style tags are removed."""
        html = '<p>Safe</p><style>body { display: none; }</style>'
        result = sanitize_rich_text_html(html)
        self.assertNotIn('style', result.lower())
        self.assertIn('Safe', result)

    def test_sanitize_removes_iframe_tags(self):
        """Test that iframe tags are removed."""
        html = '<p>Safe</p><iframe src="evil.com"></iframe>'
        result = sanitize_rich_text_html(html)
        self.assertNotIn('iframe', result)
        self.assertIn('Safe', result)

    def test_sanitize_removes_disallowed_attributes_from_images(self):
        """Test that disallowed attributes are removed from images."""
        html = '<img src="test.jpg" onclick="alert(\'XSS\')" onerror="alert(\'XSS\')">'
        result = sanitize_rich_text_html(html)
        self.assertIn('src="test.jpg"', result)
        self.assertNotIn('onclick', result)
        self.assertNotIn('onerror', result)

    def test_sanitize_removes_javascript_protocol_from_links(self):
        """Test that javascript: protocol is removed from links."""
        html = '<a href="javascript:alert(\'XSS\')">Click</a>'
        result = sanitize_rich_text_html(html)
        self.assertNotIn('javascript:', result)

    def test_sanitize_allows_http_and_https_protocols(self):
        """Test that http and https protocols are allowed."""
        html = '<a href="http://example.com">HTTP</a> <a href="https://example.com">HTTPS</a>'
        result = sanitize_rich_text_html(html)
        self.assertIn('http://example.com', result)
        self.assertIn('https://example.com', result)

    def test_sanitize_allows_mailto_protocol(self):
        """Test that mailto protocol is allowed."""
        html = '<a href="mailto:test@example.com">Email</a>'
        result = sanitize_rich_text_html(html)
        self.assertIn('mailto:test@example.com', result)

    def test_sanitize_empty_string(self):
        """Test that empty string is handled correctly."""
        result = sanitize_rich_text_html('')
        self.assertEqual(result, '')

    def test_sanitize_none_input(self):
        """Test that None input is handled correctly."""
        result = sanitize_rich_text_html(None)
        self.assertEqual(result, '')

    def test_sanitize_complex_nested_structure(self):
        """Test sanitization of complex nested HTML structure."""
        html = '''
        <div>
            <h2>My Trip Day 1</h2>
            <p>We visited <strong>Paris</strong> and saw the <em>Eiffel Tower</em>.</p>
            <ul>
                <li>Morning: Breakfast at <a href="https://cafe.com">Café</a></li>
                <li>Afternoon: Museum tour</li>
            </ul>
            <blockquote>What a wonderful day!</blockquote>
            <img src="eiffel.jpg" alt="Eiffel Tower" data-uuid="abc123">
        </div>
        '''
        result = sanitize_rich_text_html(html)

        # Should preserve allowed tags
        self.assertIn('<h2>My Trip Day 1</h2>', result)
        self.assertIn('<strong>Paris</strong>', result)
        self.assertIn('<em>Eiffel Tower</em>', result)
        self.assertIn('<ul>', result)
        self.assertIn('<li>', result)
        self.assertIn('href="https://cafe.com"', result)
        self.assertIn('<blockquote>', result)
        self.assertIn('data-uuid="abc123"', result)

        # Should remove div (not in allowed tags)
        self.assertNotIn('<div>', result)

    def test_sanitize_malicious_attribute_injection(self):
        """Test that malicious attribute injection attempts are blocked."""
        html = '<p style="background: url(javascript:alert(\'XSS\'))">Text</p>'
        result = sanitize_rich_text_html(html)
        self.assertNotIn('style', result)
        self.assertNotIn('javascript', result)
        self.assertIn('Text', result)


class CustomSanitizerTests(TestCase):
    """Test cases for custom HTMLSanitizer configurations."""

    def test_custom_allowed_tags(self):
        """Test creating sanitizer with custom allowed tags."""
        sanitizer = HTMLSanitizer(
            allowed_tags=['p', 'b'],
            allowed_attributes={},
        )
        html = '<p>Text with <b>bold</b> and <em>emphasis</em></p>'
        result = sanitizer.sanitize(html)
        self.assertIn('<b>bold</b>', result)
        self.assertNotIn('<em>', result)
        self.assertIn('emphasis', result)  # Text preserved

    def test_custom_allowed_attributes(self):
        """Test creating sanitizer with custom allowed attributes."""
        sanitizer = HTMLSanitizer(
            allowed_tags=['a'],
            allowed_attributes={'a': ['href', 'title']},
        )
        html = '<a href="test.com" title="Test" class="link">Link</a>'
        result = sanitizer.sanitize(html)
        self.assertIn('href="test.com"', result)
        self.assertIn('title="Test"', result)
        self.assertNotIn('class', result)

    def test_strip_false_escapes_tags(self):
        """Test that strip=False escapes disallowed tags instead of removing them."""
        sanitizer = HTMLSanitizer(
            allowed_tags=['p'],
            allowed_attributes={},
            strip=False,
        )
        html = '<p>Safe</p><script>alert("XSS")</script>'
        result = sanitizer.sanitize(html)
        self.assertIn('<p>Safe</p>', result)
        self.assertIn('&lt;script&gt;', result)  # Escaped, not removed
