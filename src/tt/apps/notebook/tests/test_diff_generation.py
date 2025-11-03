"""
Tests for generate_unified_diff_html() function.

This module provides comprehensive test coverage for the diff generation utility,
particularly focusing on XSS prevention and edge cases.
"""
from django.test import TestCase

from tt.apps.notebook.views import generate_unified_diff_html


class GenerateUnifiedDiffHtmlTests(TestCase):
    """Tests for the generate_unified_diff_html() function."""

    def test_no_differences(self):
        """Test that identical texts return 'No differences detected' message."""
        server_text = "Hello, world!"
        client_text = "Hello, world!"

        result = generate_unified_diff_html(server_text, client_text)

        self.assertIn('diff-no-changes', result)
        self.assertIn('No differences detected', result)

    def test_simple_addition(self):
        """Test that added lines are marked with diff-add class."""
        server_text = "Line 1\nLine 2"
        client_text = "Line 1\nLine 2\nLine 3"

        result = generate_unified_diff_html(server_text, client_text)

        self.assertIn('diff-add', result)
        self.assertIn('Line 3', result)

    def test_simple_deletion(self):
        """Test that deleted lines are marked with diff-delete class."""
        server_text = "Line 1\nLine 2\nLine 3"
        client_text = "Line 1\nLine 2"

        result = generate_unified_diff_html(server_text, client_text)

        self.assertIn('diff-delete', result)
        self.assertIn('Line 3', result)

    def test_modification(self):
        """Test that modified lines show both deletion and addition."""
        server_text = "Hello, world!"
        client_text = "Hello, universe!"

        result = generate_unified_diff_html(server_text, client_text)

        self.assertIn('diff-delete', result)
        self.assertIn('diff-add', result)
        self.assertIn('world', result)
        self.assertIn('universe', result)

    def test_xss_prevention_script_tag(self):
        """Test that script tags are properly escaped to prevent XSS."""
        server_text = "Safe content"
        client_text = "<script>alert('XSS')</script>"

        result = generate_unified_diff_html(server_text, client_text)

        # Script tags should be escaped
        self.assertNotIn('<script>', result)
        self.assertIn('&lt;script&gt;', result)
        self.assertIn('&lt;/script&gt;', result)

    def test_xss_prevention_html_injection(self):
        """Test that HTML entities are properly escaped."""
        server_text = "Normal text"
        client_text = "<img src=x onerror=alert('XSS')>"

        result = generate_unified_diff_html(server_text, client_text)

        # HTML should be escaped
        self.assertNotIn('<img', result)
        self.assertIn('&lt;img', result)
        self.assertIn('&gt;', result)

    def test_xss_prevention_ampersand_escaping(self):
        """Test that ampersands are properly escaped."""
        server_text = "A & B"
        client_text = "A & B & C"

        result = generate_unified_diff_html(server_text, client_text)

        # Ampersands should be escaped (unless part of existing entity)
        self.assertIn('&amp;', result)

    def test_xss_prevention_quote_escaping(self):
        """Test that quotes are properly escaped."""
        server_text = 'Normal text'
        client_text = 'Text with "quotes" and \'apostrophes\''

        result = generate_unified_diff_html(server_text, client_text)

        # Quotes should be escaped or handled safely
        # (html.escape converts " to &quot; and ' to &#x27;)
        self.assertTrue(
            '&quot;' in result or '&#34;' in result or '"' not in result.split('class=')[1]
        )

    def test_multiline_diff(self):
        """Test that multiline diffs are properly formatted."""
        server_text = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"
        client_text = "Line 1\nModified Line 2\nLine 3\nLine 4\nNew Line 5"

        result = generate_unified_diff_html(server_text, client_text)

        # Should contain header, hunk, delete, and add divs
        self.assertIn('diff-header', result)
        self.assertIn('diff-hunk', result)
        self.assertIn('diff-delete', result)
        self.assertIn('diff-add', result)
        self.assertIn('unified-diff', result)

    def test_context_lines(self):
        """Test that context lines are included with diff-context class."""
        server_text = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\nLine 6\nLine 7"
        client_text = "Line 1\nLine 2\nLine 3\nModified 4\nLine 5\nLine 6\nLine 7"

        result = generate_unified_diff_html(server_text, client_text)

        # Should contain context lines (unchanged lines around the change)
        self.assertIn('diff-context', result)

    def test_empty_server_text(self):
        """Test diff when server text is empty (all additions)."""
        server_text = ""
        client_text = "New line 1\nNew line 2"

        result = generate_unified_diff_html(server_text, client_text)

        self.assertIn('diff-add', result)
        self.assertIn('New line 1', result)
        self.assertIn('New line 2', result)

    def test_empty_client_text(self):
        """Test diff when client text is empty (all deletions)."""
        server_text = "Old line 1\nOld line 2"
        client_text = ""

        result = generate_unified_diff_html(server_text, client_text)

        self.assertIn('diff-delete', result)
        self.assertIn('Old line 1', result)
        self.assertIn('Old line 2', result)

    def test_both_empty(self):
        """Test diff when both texts are empty."""
        server_text = ""
        client_text = ""

        result = generate_unified_diff_html(server_text, client_text)

        self.assertIn('diff-no-changes', result)
        self.assertIn('No differences detected', result)

    def test_file_headers(self):
        """Test that file headers are included with proper labels."""
        server_text = "Old content"
        client_text = "New content"

        result = generate_unified_diff_html(server_text, client_text)

        # Should contain file headers with descriptive labels
        self.assertIn('Server Version (Latest)', result)
        self.assertIn('Your Changes', result)
        self.assertIn('diff-header', result)

    def test_hunk_headers(self):
        """Test that hunk headers (line number ranges) are included."""
        server_text = "Line 1\nLine 2\nLine 3"
        client_text = "Line 1\nModified\nLine 3"

        result = generate_unified_diff_html(server_text, client_text)

        # Should contain hunk header with @@ markers
        self.assertIn('diff-hunk', result)
        self.assertIn('@@', result)

    def test_special_characters_preserved(self):
        """Test that special characters are preserved (after escaping)."""
        server_text = "Special: @#$%^&*()"
        client_text = "Special: @#$%^&*()!+"

        result = generate_unified_diff_html(server_text, client_text)

        # Special chars should be present (escaped if needed)
        self.assertIn('@#$%', result)

    def test_unicode_handling(self):
        """Test that unicode characters are handled correctly."""
        server_text = "Hello 世界"
        client_text = "Hello 世界! 🌍"

        result = generate_unified_diff_html(server_text, client_text)

        # Unicode should be preserved
        self.assertIn('世界', result)
        self.assertIn('🌍', result)

    def test_whitespace_changes(self):
        """Test that whitespace changes are detected."""
        server_text = "Line with spaces"
        client_text = "Line  with  spaces"  # Extra spaces

        result = generate_unified_diff_html(server_text, client_text)

        # Should detect the difference
        self.assertNotIn('diff-no-changes', result)
        self.assertIn('diff-delete', result)
        self.assertIn('diff-add', result)

    def test_newline_handling(self):
        """Test that different newline styles are handled."""
        server_text = "Line 1\nLine 2\nLine 3"
        client_text = "Line 1\nLine 2\nLine 3\nLine 4"

        result = generate_unified_diff_html(server_text, client_text)

        # Should properly detect the added line
        self.assertIn('diff-add', result)
        self.assertIn('Line 4', result)

    def test_large_diff(self):
        """Test handling of large diffs with many lines."""
        server_lines = [f"Line {i}" for i in range(1, 101)]
        client_lines = [f"Line {i}" for i in range(1, 101)]
        client_lines[50] = "Modified Line 51"  # Change one line in the middle

        server_text = "\n".join(server_lines)
        client_text = "\n".join(client_lines)

        result = generate_unified_diff_html(server_text, client_text)

        # Should handle large diffs without error
        self.assertIn('diff-delete', result)
        self.assertIn('diff-add', result)
        self.assertIn('Modified Line 51', result)
        # Context lines should be included (3 before and after by default)
        self.assertIn('Line 48', result)  # Context before
        self.assertIn('Line 54', result)  # Context after
