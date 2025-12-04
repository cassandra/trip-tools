"""
Thumbnail URL normalizer for entry content.

Replaces full-size image URLs with thumbnail URLs in journal/travelog entry
content. This improves page load performance by using appropriately sized
images for in-page display.
"""
import re

from tt.apps.common.regex_utils import HtmlRegexPatterns
from tt.apps.images.models import TripImage
from tt.apps.journal.models import JournalEntryContent

from tt.environment.constants import TtConst

from .base import EntryContentNormalizer


class ThumbnailUrlNormalizer(EntryContentNormalizer):
    """
    Replaces full-size image URLs with thumbnail URLs in entry content.

    Finds all <img class="trip-image" data-uuid="..." src="..."> elements,
    looks up the TripImage by UUID, and replaces the src attribute with
    the thumbnail_image URL.
    """

    name = "thumbnail_urls"
    description = "Replace full-size image URLs with thumbnail URLs"

    # Pattern to match trip-image elements and capture UUID and src
    # Matches: <img ... class="...trip-image..." ... data-uuid="UUID" ... src="URL" ...>
    # or:      <img ... src="URL" ... class="...trip-image..." ... data-uuid="UUID" ...>
    # The attributes can appear in any order
    IMAGE_TAG_PATTERN = re.compile(
        r'(<img'                                    # Start of img tag
        + HtmlRegexPatterns.ANY_ATTRS               # Any attributes before
        + HtmlRegexPatterns.class_containing( TtConst.JOURNAL_IMAGE_CLASS )
        + r'[^>]*>)',                               # Rest of tag including >
        re.IGNORECASE
    )

    # Pattern to extract UUID from data-uuid attribute
    UUID_ATTR_PATTERN = re.compile(
        r'data-' + re.escape( TtConst.UUID_DATA_ATTR ) + r'=["\']([^"\']+)["\']',
        re.IGNORECASE
    )

    # Pattern to extract and replace src attribute
    SRC_ATTR_PATTERN = re.compile(
        r'(src=["\'])([^"\']+)(["\'])',
        re.IGNORECASE
    )

    def normalize( self,
                   html_content: str,
                   entry: JournalEntryContent ) -> tuple[str, list[str]]:
        """
        Replace full-size image URLs with thumbnail URLs.

        Args:
            html_content: The HTML text to normalize
            entry: The entry being processed (for context/logging)

        Returns:
            Tuple of (normalized_html, list_of_change_descriptions)
        """
        if not html_content:
            return html_content, []

        changes = []

        # Build a cache of UUID -> thumbnail URL to avoid repeated DB lookups
        uuid_to_thumbnail = {}

        def replace_img_src( match: re.Match ) -> str:
            """Replace src in a single img tag if needed."""
            img_tag = match.group(1)

            # Extract UUID from the tag
            uuid_match = self.UUID_ATTR_PATTERN.search(img_tag)
            if not uuid_match:
                return img_tag  # No UUID, leave unchanged

            image_uuid = uuid_match.group(1)

            # Get thumbnail URL (from cache or DB)
            if image_uuid not in uuid_to_thumbnail:
                try:
                    trip_image = TripImage.objects.get(uuid=image_uuid)
                    uuid_to_thumbnail[image_uuid] = trip_image.thumbnail_image.url
                except TripImage.DoesNotExist:
                    uuid_to_thumbnail[image_uuid] = None  # Mark as not found

            thumbnail_url = uuid_to_thumbnail.get(image_uuid)
            if thumbnail_url is None:
                return img_tag  # Image not found, leave unchanged

            # Extract current src
            src_match = self.SRC_ATTR_PATTERN.search(img_tag)
            if not src_match:
                return img_tag  # No src attribute, leave unchanged

            current_src = src_match.group(2)

            # Check if already using thumbnail
            if current_src == thumbnail_url:
                return img_tag  # Already correct

            # Replace src with thumbnail URL
            new_tag = self.SRC_ATTR_PATTERN.sub(
                rf'\g<1>{thumbnail_url}\g<3>',
                img_tag
            )

            # Record the change
            changes.append(f"{image_uuid}: {current_src} -> {thumbnail_url}")

            return new_tag

        # Process all img tags
        normalized_html = self.IMAGE_TAG_PATTERN.sub(replace_img_src, html_content)

        return normalized_html, changes
