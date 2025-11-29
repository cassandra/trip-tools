"""
Utilities for building regex patterns, particularly for HTML parsing.
"""
import re


class HtmlRegexPatterns:
    """
    Helper class for building regex patterns to match HTML elements.

    Provides reusable pattern components for matching class attributes,
    data attributes, and capturing values from HTML content.

    Usage:
        from tt.apps.common.regex_utils import HtmlRegexPatterns

        pattern = re.compile(
            r'<img' + HtmlRegexPatterns.ANY_ATTRS +
            HtmlRegexPatterns.class_containing('my-class') +
            HtmlRegexPatterns.attr_capture('data-id'),
            re.IGNORECASE
        )
    """

    # Matches any sequence of attributes (non-greedy, stops at >)
    ANY_ATTRS = r'[^>]+'

    @classmethod
    def class_containing(cls, class_name: str) -> str:
        """
        Build pattern to match a class attribute containing the specified class name.

        Args:
            class_name: The CSS class name to match (will be escaped)

        Returns:
            Regex pattern string matching class="...<class_name>..."
        """
        return rf'class="[^"]*{re.escape(class_name)}[^"]*"'

    @classmethod
    def attr_capture(cls, attr_name: str) -> str:
        """
        Build pattern to match an attribute and capture its value.

        Args:
            attr_name: The attribute name to match (will be escaped)

        Returns:
            Regex pattern string with capture group for the attribute value
        """
        return rf'{re.escape(attr_name)}="([^"]+)"'

    @classmethod
    def uuid_capture(cls, attr_name: str) -> str:
        """
        Build pattern to match an attribute and capture a UUID-formatted value.

        Args:
            attr_name: The attribute name to match (will be escaped)

        Returns:
            Regex pattern string with capture group for UUID value (36 chars)
        """
        return rf'{re.escape(attr_name)}="([0-9a-f-]{{36}})"'
