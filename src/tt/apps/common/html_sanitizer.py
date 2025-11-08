"""
HTML sanitization utilities for user-generated content.

Provides safe HTML sanitization using Bleach library with configurable
whitelists for tags and attributes.
"""
import logging
from typing import Dict, List, Optional

try:
    import bleach
    BLEACH_AVAILABLE = True
except ImportError:
    BLEACH_AVAILABLE = False
    logging.warning(
        "bleach library not installed. HTML sanitization will not be available. "
        "Install with: pip install bleach"
    )

logger = logging.getLogger(__name__)


class HTMLSanitizer:
    """
    HTML sanitizer with configurable whitelists.

    Uses Bleach library to sanitize HTML content, allowing only specified
    tags and attributes while stripping dangerous content.
    """

    # Default allowed tags for rich text content
    DEFAULT_ALLOWED_TAGS = [
        'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'ul', 'ol', 'li',
        'strong', 'em', 'code', 'pre',
        'blockquote', 'hr', 'br',
        'img', 'a',
    ]

    # Default allowed attributes by tag
    DEFAULT_ALLOWED_ATTRIBUTES = {
        'img': ['src', 'alt', 'data-uuid', 'data-layout'],
        'a': ['href'],
    }

    # Default allowed protocols for URLs
    DEFAULT_ALLOWED_PROTOCOLS = ['http', 'https', 'mailto']

    def __init__( self,
                  allowed_tags       : Optional[List[str]]              = None,
                  allowed_attributes : Optional[Dict[str, List[str]]]  = None,
                  allowed_protocols  : Optional[List[str]]              = None,
                  strip              : bool                             = True):
        """
        Initialize HTML sanitizer with custom configuration.

        Args:
            allowed_tags: List of allowed HTML tags (defaults to DEFAULT_ALLOWED_TAGS)
            allowed_attributes: Dict of tag -> list of allowed attributes 
                                (defaults to DEFAULT_ALLOWED_ATTRIBUTES)
            allowed_protocols: List of allowed URL protocols (defaults to DEFAULT_ALLOWED_PROTOCOLS)
            strip: If True, strip disallowed tags; if False, escape them
        """
        if not BLEACH_AVAILABLE:
            raise ImportError(
                "bleach library is required for HTML sanitization. "
                "Install with: pip install bleach"
            )

        self.allowed_tags = allowed_tags or self.DEFAULT_ALLOWED_TAGS
        self.allowed_attributes = allowed_attributes or self.DEFAULT_ALLOWED_ATTRIBUTES
        self.allowed_protocols = allowed_protocols or self.DEFAULT_ALLOWED_PROTOCOLS
        self.strip = strip

    def sanitize( self, html_content: str ) -> str:
        """
        Sanitize HTML content using configured whitelist.

        Args:
            html_content: Raw HTML content to sanitize

        Returns:
            Sanitized HTML content with only allowed tags/attributes
        """
        if not html_content:
            return ''

        try:
            # Use bleach.clean to sanitize the HTML
            cleaned_html = bleach.clean(
                html_content,
                tags=self.allowed_tags,
                attributes=self.allowed_attributes,
                protocols=self.allowed_protocols,
                strip=self.strip,
            )
            return cleaned_html
        except Exception as e:
            logger.error(f'Error sanitizing HTML: {e}')
            # On error, return empty string for safety
            return ''


# Pre-configured sanitizer for rich text content
RICH_TEXT_SANITIZER = None
if BLEACH_AVAILABLE:
    RICH_TEXT_SANITIZER = HTMLSanitizer(
        allowed_tags=[
            'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            'ul', 'ol', 'li',
            'strong', 'em', 'code', 'pre',
            'blockquote', 'hr', 'br',
            'img', 'a',
        ],
        allowed_attributes={
            'img': ['src', 'alt', 'data-uuid', 'data-layout'],
            'a': ['href'],
        },
        allowed_protocols=['http', 'https', 'mailto'],
        strip=True,
    )


def sanitize_rich_text_html( html_content: str ) -> str:
    """
    Sanitize HTML content for rich text entries.

    Convenience function that uses the pre-configured RICH_TEXT_SANITIZER.
    Suitable for journal entries, notebook entries, or any rich text content.

    Args:
        html_content: Raw HTML content to sanitize

    Returns:
        Sanitized HTML content safe for storage and display
    """
    if not RICH_TEXT_SANITIZER:
        raise RuntimeError(
            "bleach library is not available. Cannot sanitize HTML. "
            "Install with: pip install bleach"
        )
    return RICH_TEXT_SANITIZER.sanitize(html_content)
