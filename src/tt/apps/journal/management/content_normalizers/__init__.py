"""
Content normalizers for journal entry migration.

Edit ACTIVE_NORMALIZERS to control which normalizers run.
After running in production, normalizers can be removed from this list
or deleted entirely.
"""
from .thumbnail_urls import ThumbnailUrlNormalizer

# List of normalizer instances to run
# Edit this list to add/remove normalizers as needed
ACTIVE_NORMALIZERS = [
    ThumbnailUrlNormalizer(),
]
