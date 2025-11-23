import json
import logging
import re
from typing import List, Optional
from uuid import UUID

from django.contrib.auth.models import User as UserType
from django.db import transaction
from django.http import Http404

from tt.apps.common.redis_client import get_redis_client
from tt.apps.journal.models import Journal, JournalContent
from .models import Travelog, TravelogEntry
from .transient_models import TravelogPageContext, TravelogImageMetadata
from .enums import ContentType

logger = logging.getLogger(__name__)


class PublishingError(Exception):
    """Exception raised when publishing operations fail."""
    pass


class PublishingService:

    @classmethod
    @transaction.atomic
    def publish_journal( cls, journal : Journal, user : UserType ) -> Travelog:
        """
        Publish a journal as a new Travelog version.

        Creates an immutable snapshot of the journal and all its entries.
        Manages version numbering and ensures only one version is marked as current.
        """
        journal_entries = journal.entries.all()
        if not journal_entries.exists():
            raise ValueError("Cannot publish journal with no entries")

        # Lock the journal row for this transaction to prevent race conditions
        locked_journal = Journal.objects.select_for_update().get( pk = journal.pk )

        next_version = Travelog.objects.get_next_version_number( locked_journal )

        Travelog.objects.filter(
            journal = locked_journal,
            is_current = True
        ).update( is_current = False )

        travelog = Travelog.objects.create(
            journal = locked_journal,
            version_number = next_version,
            is_current = True,
            published_by = user,

            # Copy journal content
            title = locked_journal.title,
            description = locked_journal.description,
            reference_image = locked_journal.reference_image,
        )

        for journal_entry in journal_entries:
            TravelogEntry.objects.create(
                travelog = travelog,

                # Copy entry content
                date = journal_entry.date,
                timezone = journal_entry.timezone,
                title = journal_entry.title,
                text = journal_entry.text,
                reference_image = journal_entry.reference_image,
            )

        # Invalidate VIEW cache since new version becomes current
        TravelogImageCacheService.invalidate_cache(
            journal_uuid = locked_journal.uuid,
            content_type = ContentType.VIEW
        )

        return travelog

    @staticmethod
    @transaction.atomic
    def set_as_current( journal: Journal, travelog: Travelog ) -> Travelog:
        """
        Set a specific travelog version as the current published version.

        This operation only changes which version is publicly visible.
        It does not affect the journal's working entries.

        Raises:
            PublishingError: If validation fails
        """
        if travelog.journal_id != journal.id:
            raise PublishingError(
                "Cannot set as current: Travelog does not belong to this journal"
            )

        if travelog.is_current:
            raise PublishingError(
                "This version is already the current published version"
            )

        Travelog.objects.filter( journal=journal ).update( is_current = False )
        travelog.is_current = True
        travelog.save( update_fields = ['is_current'] )

        # Invalidate VIEW cache since current version changed
        TravelogImageCacheService.invalidate_cache(
            journal_uuid = journal.uuid,
            content_type = ContentType.VIEW
        )

        return travelog


class ContentResolutionService:

    @staticmethod
    def resolve_content(travelog_page_context: TravelogPageContext) -> JournalContent:
        """
        Returns:
            JournalContent instance - either Journal (for DRAFT) or Travelog (for VIEW/VERSION)

        Raises:
            Http404: If requested version doesn't exist
        """
        if travelog_page_context.content_type == ContentType.DRAFT:
            return travelog_page_context.journal

        elif travelog_page_context.content_type == ContentType.VIEW:
            travelog = Travelog.objects.get_current(travelog_page_context.journal)
            if not travelog:
                raise Http404()
            return travelog

        elif travelog_page_context.content_type == ContentType.VERSION:
            travelog = Travelog.objects.get_version(
                travelog_page_context.journal,
                travelog_page_context.version_number
            )
            if not travelog:
                raise Http404()
            return travelog

        else:
            # This should never happen with proper enum handling
            raise ValueError(f"Unknown content type: {travelog_page_context.content_type}")


class TravelogImageCacheService:
    """
    Service for caching image lists extracted from travelog HTML content.

    Provides efficient image list retrieval for travelog gallery and browse views
    by caching parsed image metadata with different TTL strategies based on content type.

    Cache Strategy:
    - DRAFT: 1 hour TTL (content changes frequently)
    - VIEW: Infinite TTL with manual invalidation (immutable published content)
    - VERSION: 24 hour TTL (historical versions rarely accessed)
    """

    # Cache TTL values in seconds
    TTL_DRAFT = 3600        # 1 hour
    TTL_VIEW = None         # Infinite (manual invalidation only)
    TTL_VERSION = 86400     # 24 hours

    # Regex pattern for extracting image UUIDs from HTML
    # Matches: <img class="trip-image" data-uuid="{UUID}" ...>
    IMAGE_UUID_PATTERN = re.compile(
        r'<img[^>]+class="[^"]*trip-image[^"]*"[^>]+data-uuid="([0-9a-f-]{36})"',
        re.IGNORECASE
    )

    # Regex pattern for extracting layout from wrapper
    # Matches: <span class="trip-image-wrapper" data-layout="{LAYOUT}">
    LAYOUT_PATTERN = re.compile(
        r'<span[^>]+class="[^"]*trip-image-wrapper[^"]*"[^>]+data-layout="([^"]+)"',
        re.IGNORECASE
    )

    # Constants for image processing
    IMAGE_WRAPPER_SEARCH_WINDOW = 500  # Characters to search backward for wrapper element
    DEFAULT_IMAGE_LAYOUT = 'float-right'  # Default layout when wrapper not found

    @classmethod
    def _get_cache_key( cls,
                        journal_uuid    : UUID,
                        content_type    : ContentType,
                        version_number  : Optional[int]  = None ) -> str:
        """
        Generate Redis cache key for image list.

        Format: travelog:images:{journal_uuid}:{content_type}:{version?}
        """
        key_parts = [ 'travelog', 'images', str(journal_uuid), content_type.name ]
        if version_number is not None:
            key_parts.append( str(version_number) )
        return ':'.join( key_parts )

    @classmethod
    def _get_ttl_for_content_type(cls, content_type: ContentType) -> Optional[int]:
        """Get TTL in seconds for the given content type."""
        if content_type == ContentType.DRAFT:
            return cls.TTL_DRAFT
        elif content_type == ContentType.VIEW:
            return cls.TTL_VIEW
        elif content_type == ContentType.VERSION:
            return cls.TTL_VERSION
        return None

    @classmethod
    def _extract_images_from_html( cls,
                                   html_content    : str,
                                   entry_date      : str,
                                   document_order  : int ) -> List[TravelogImageMetadata]:
        """
        Extract image metadata from HTML content.

        Args:
            html_content: HTML string containing trip-image elements
            entry_date: Date string (YYYY-MM-DD) for the entry
            document_order: Starting order number for images in this entry

        Returns:
            List of TravelogImageMetadata objects
        """
        images = []

        # Split HTML into sections to track layout context
        # We need to find images and their surrounding wrapper elements
        image_matches = list( cls.IMAGE_UUID_PATTERN.finditer( html_content ))

        for match in image_matches:
            uuid_str = match.group(1)

            # Look backwards from image position to find the wrapper element
            # Search up to IMAGE_WRAPPER_SEARCH_WINDOW characters before the image tag
            search_start = max( 0, match.start() - cls.IMAGE_WRAPPER_SEARCH_WINDOW )
            context_html = html_content[ search_start:match.end() ]

            # Try to find the layout from the wrapper
            layout = cls.DEFAULT_IMAGE_LAYOUT
            layout_match = cls.LAYOUT_PATTERN.search( context_html )
            if layout_match:
                layout = layout_match.group(1)

            images.append( TravelogImageMetadata(
                uuid = uuid_str,
                entry_date = entry_date,
                layout = layout,
                document_order = document_order,
            ))
            document_order += 1

        return images

    @classmethod
    def _extract_images_from_content(cls, content: JournalContent) -> List[TravelogImageMetadata]:
        """
        Extract all images from journal content entries in chronological order.

        Deduplicates images - only the first occurrence of each image UUID is kept.

        Args:
            content: JournalContent instance (Journal or Travelog)

        Returns:
            List of unique TravelogImageMetadata objects in chronological order
        """
        all_images = []
        seen_uuids = set()
        document_order = 1

        # Get entries in chronological order
        entries = content.get_entries().order_by('date')

        for entry in entries:
            if not entry.text:
                continue

            entry_date = entry.date.strftime('%Y-%m-%d')
            entry_images = cls._extract_images_from_html(
                entry.text,
                entry_date,
                document_order
            )

            # Deduplicate - only keep first occurrence of each image
            for img in entry_images:
                if img.uuid not in seen_uuids:
                    all_images.append(img)
                    seen_uuids.add(img.uuid)
                    document_order += 1

        return all_images

    @classmethod
    def get_images( cls,
                    travelog_page_context  : TravelogPageContext ) -> List[TravelogImageMetadata]:
        """
        Get cached image list or extract from content if not cached.

        Cache invalidation is handled separately via invalidate_cache() method.
        If cache was invalidated before this call, images will be re-extracted.

        Args:
            travelog_page_context: Context containing journal and content type info

        Returns:
            List of TravelogImageMetadata objects in chronological order
        """
        cache_key = cls._get_cache_key(
            travelog_page_context.journal.uuid,
            travelog_page_context.content_type,
            travelog_page_context.version_number
        )

        # Try to get from cache
        try:
            redis_client = get_redis_client()
            if redis_client:
                cached_data = redis_client.get(cache_key)
                if cached_data:
                    logger.debug(f"Cache hit for images: {cache_key}")
                    # Deserialize from JSON using from_dict
                    images_data = json.loads(cached_data)
                    return [ TravelogImageMetadata.from_dict(img) for img in images_data ]
                logger.debug(f"Cache miss for images: {cache_key}")
        except Exception as e:
            logger.warning(f"Redis error getting cached images: {e}")
            # Fall through to extraction

        # Cache miss - extract from content
        logger.debug(f"Extracting images from content for: {cache_key}")
        content = ContentResolutionService.resolve_content( travelog_page_context )
        images = cls._extract_images_from_content( content )

        # Cache the result
        cls._cache_images(
            travelog_page_context.journal.uuid,
            travelog_page_context.content_type,
            travelog_page_context.version_number,
            images
        )

        return images

    @classmethod
    def _cache_images( cls,
                       journal_uuid    : UUID,
                       content_type    : ContentType,
                       version_number  : Optional[int],
                       images          : List[TravelogImageMetadata] ) -> None:
        """
        Store images in Redis cache with appropriate TTL.
        """
        try:
            redis_client = get_redis_client()
            if not redis_client:
                logger.debug("Redis not available, skipping cache storage")
                return

            cache_key = cls._get_cache_key(journal_uuid, content_type, version_number)
            ttl = cls._get_ttl_for_content_type(content_type)

            # Serialize to JSON using to_dict
            images_data = [ img.to_dict() for img in images ]
            cached_data = json.dumps(images_data)

            # Store with appropriate TTL
            if ttl is None:
                # Infinite TTL - no expiration
                redis_client.set(cache_key, cached_data)
                logger.debug(f"Cached images (no expiration): {cache_key}")
            else:
                redis_client.setex(cache_key, ttl, cached_data)
                logger.debug(f"Cached images (TTL={ttl}s): {cache_key}")

        except Exception as e:
            logger.warning(f"Redis error caching images: {e}")
            # Not fatal - system continues without cache

    @classmethod
    def invalidate_cache( cls,
                          journal_uuid    : UUID,
                          content_type    : ContentType,
                          version_number  : Optional[int] = None ) -> None:
        """
        Invalidate cached image list for specific journal/content type.
        """
        try:
            redis_client = get_redis_client()
            if not redis_client:
                return

            cache_key = cls._get_cache_key(journal_uuid, content_type, version_number)
            deleted = redis_client.delete(cache_key)

            if deleted:
                logger.info(f"Invalidated image cache: {cache_key}")
            else:
                logger.debug(f"No cache to invalidate: {cache_key}")

        except Exception as e:
            logger.warning(f"Redis error invalidating cache: {e}")
