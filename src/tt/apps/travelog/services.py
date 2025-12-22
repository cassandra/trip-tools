import json
import logging
import re
from datetime import date
from html.parser import HTMLParser
from typing import Callable, List, Optional, Tuple
from uuid import UUID

from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import User as UserType
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import Http404

from tt.apps.common.redis_client import get_redis_client
from tt.apps.images.models import TripImage
from tt.apps.journal.models import Journal, JournalContent, JournalEntryContent
from tt.apps.trips.models import Trip
from tt.environment.constants import TtConst

from .context import TravelogPageContext
from .enums import ContentType
from .exceptions import PasswordRequiredException
from .models import Travelog, TravelogEntry
from .schemas import (
    DayEntryNavData,
    DayPageData,
    TocEntryData,
    TocPageData,
    TravelogImageMetadata,
    TravelogListItemData,
)

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
        journal_entries = journal.entries.filter(include_in_publish=True)
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
    def resolve_content( travelog_page_context: TravelogPageContext ) -> JournalContent:
        """
        Raises: Http404: If requested version doesn't exist
        """
        if travelog_page_context.content_type.is_draft:
            return travelog_page_context.journal

        elif travelog_page_context.content_type.is_view:
            travelog = Travelog.objects.get_current( travelog_page_context.journal )
            if not travelog:
                raise Http404()
            return travelog

        elif travelog_page_context.content_type.is_version:
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

        
class TravelogPublicListBuilder:
    """
    Builds a sorted list of public travelogs for a user.

    Encapsulates all business logic for:
    - Querying journals with published travelogs
    - Filtering by access permissions
    - Computing date ranges (excluding special entries)
    - Selecting display images (preferring dated entries)
    - Sorting chronologically
    """

    @classmethod
    def build(
        cls,
        target_user: AbstractUser,
        access_checker: Callable[[Journal], None]
    ) -> List[TravelogListItemData]:
        """
        Build a sorted list of accessible travelogs for a user.

        Args:
            target_user: The user whose travelogs to list
            access_checker: Callable that checks journal access. Should raise
                PasswordRequiredException, Http404, or PermissionDenied as needed.

        Returns:
            List of TravelogListItemData sorted by latest date (newest first)
        """
        # Query journals with published travelogs
        trips = Trip.objects.owned_by( target_user )
        journals = Journal.objects.filter(
            trip__in=trips,
            travelogs__is_current=True
        ).distinct().select_related('trip').prefetch_related(
            'entries', 'entries__reference_image'
        )

        # Filter by access and build list items
        items = []
        for journal in journals:
            requires_password = False

            try:
                access_checker(journal)
            except PasswordRequiredException:
                requires_password = True
            except (Http404, PermissionDenied):
                continue

            items.append(cls._build_list_item(journal, requires_password))

        # Sort by latest date (newest first)
        return sorted(
            items,
            key=lambda item: item.latest_entry_date or '',
            reverse=True
        )

    @classmethod
    def _build_list_item(
        cls,
        journal: Journal,
        requires_password: bool
    ) -> TravelogListItemData:
        """
        Build a single TravelogListItemData from a journal.
        """
        entries = list(journal.entries.order_by('date'))

        earliest_date, latest_date, day_count = cls._compute_date_range(journal, entries)
        display_image = cls._select_display_image(journal, entries)

        return TravelogListItemData(
            journal=journal,
            requires_password=requires_password,
            earliest_entry_date=earliest_date,
            latest_entry_date=latest_date,
            day_count=day_count,
            display_image=display_image
        )

    @classmethod
    def _compute_date_range(
        cls,
        journal: Journal,
        entries: List
    ) -> Tuple[Optional[str], Optional[str], int]:
        """
        Compute earliest and latest dates and day count from dated entries only.

        Excludes prologue/epilogue entries (which use sentinel dates).
        Falls back to published_datetime or created_datetime if no dated entries.

        Returns:
            Tuple of (earliest_date, latest_date, day_count)
        """
        dated_entries = [e for e in entries if not e.is_special_entry]
        day_count = len(dated_entries)

        if dated_entries:
            earliest_date = dated_entries[0].date.strftime('%Y-%m-%d')
            latest_date = dated_entries[-1].date.strftime('%Y-%m-%d')
        else:
            current_travelog = journal.travelogs.filter(is_current=True).first()
            if current_travelog:
                fallback_date = current_travelog.published_datetime.strftime('%Y-%m-%d')
            else:
                fallback_date = journal.created_datetime.strftime('%Y-%m-%d')
            earliest_date = fallback_date
            latest_date = fallback_date

        return earliest_date, latest_date, day_count

    @classmethod
    def _select_display_image(
        cls,
        journal: Journal,
        entries: List
    ) -> Optional[TripImage]:
        """
        Select display image, preferring dated entries over special entries.
        """
        if journal.reference_image:
            return journal.reference_image

        for entry in entries:
            if not entry.is_special_entry and entry.reference_image:
                return entry.reference_image

        for entry in entries:
            if entry.is_special_entry and entry.reference_image:
                return entry.reference_image

        return None


class TravelogImageExtractor(HTMLParser):
    """
    Extract image metadata from journal HTML content using Python's html.parser.

    Handles float-right image reordering: when multiple consecutive float-right
    images appear in the same has-float-image container (paragraph or div), they
    are reversed to match CSS display order.

    CSS float:right causes images to display in reverse HTML order. When images
    are prepended to a paragraph, the HTML order [Image2, Image1] displays as
    [Image1, Image2]. This parser detects such groups by their parent container
    and reverses them, but only if they are truly consecutive (no text between).

    Usage:
        parser = TravelogImageExtractor()
        parser.feed(html_content)
        images = parser.get_images()
    """

    # Regex for validating UUID format (8-4-4-4-12 hex digits)
    UUID_PATTERN = re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        re.IGNORECASE
    )

    def __init__(self):
        super().__init__()
        self.images = []                    # Final list of all images
        self.in_float_container = False     # Inside <p/div class="has-float-image">
        self.consecutive_float_images = []  # Current group of consecutive float-right images
        self.text_since_last_image = False  # Track if text appeared since last float-right image
        self.in_wrapper = False             # Inside <span class="trip-image-wrapper">
        self.current_layout = None          # Current wrapper's data-layout
        self.in_caption = False             # Inside <span class="trip-image-caption">
        self.current_caption = ''           # Caption text accumulator

    def _flush_consecutive_group(self):
        """Flush current consecutive float-right group with reversal."""
        if self.consecutive_float_images:
            self.images.extend(reversed(self.consecutive_float_images))
            self.consecutive_float_images = []
        self.text_since_last_image = False

    def handle_starttag(self, tag, attrs):
        attrs_dict = {k.lower(): v for k, v in attrs}
        classes = attrs_dict.get('class', '')

        # Track float-right containers (paragraphs/divs with has-float-image class)
        if tag in ('p', 'div') and 'has-float-image' in classes:
            self.in_float_container = True
            self.consecutive_float_images = []
            self.text_since_last_image = False

        # Track image wrappers
        elif tag == 'span' and TtConst.JOURNAL_IMAGE_WRAPPER_CLASS in classes:
            self.in_wrapper = True
            self.current_layout = attrs_dict.get('data-' + TtConst.LAYOUT_DATA_ATTR, 'float-right')

        # Track caption spans
        elif tag == 'span' and TtConst.TRIP_IMAGE_CAPTION_CLASS in classes:
            self.in_caption = True
            self.current_caption = ''

        # Extract image data
        elif tag == 'img' and TtConst.JOURNAL_IMAGE_CLASS in classes:
            uuid = attrs_dict.get('data-' + TtConst.UUID_DATA_ATTR, '')

            # Validate UUID format
            if not self.UUID_PATTERN.match(uuid):
                return

            img_data = {
                'uuid': uuid,
                'layout': self.current_layout or 'float-right',
                'caption': '',
            }

            if self.in_float_container and self.current_layout == 'float-right':
                # Check if text appeared since last float-right image
                if self.text_since_last_image and self.consecutive_float_images:
                    # Text breaks the consecutive group - flush previous group
                    self._flush_consecutive_group()
                self.consecutive_float_images.append(img_data)
                self.text_since_last_image = False
            else:
                self.images.append(img_data)

    def handle_endtag(self, tag):
        if tag == 'span':
            if self.in_caption:
                self.in_caption = False
                # Attach caption to most recent image in current context
                target = self.consecutive_float_images if self.consecutive_float_images else self.images
                if target:
                    target[-1]['caption'] = self.current_caption.strip()
                self.current_caption = ''
            elif self.in_wrapper:
                self.in_wrapper = False
                self.current_layout = None

        elif tag in ('p', 'div') and self.in_float_container:
            # Exiting float container - flush collected images
            self._flush_consecutive_group()
            self.in_float_container = False

    def handle_data(self, data):
        if self.in_caption:
            self.current_caption += data
        elif self.in_float_container and not self.in_wrapper:
            # Text outside wrappers in float container marks non-consecutive
            if data.strip():
                self.text_since_last_image = True

    def get_images(self):
        """Return extracted images in display order."""
        # Flush any remaining consecutive group (shouldn't happen with well-formed HTML)
        self._flush_consecutive_group()
        return self.images


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
                                   display_date    : str,
                                   document_order  : int ) -> List[TravelogImageMetadata]:
        """
        Extract image metadata from HTML content.

        Uses TravelogImageExtractor (html.parser based) to parse HTML structure
        and extract image metadata. Handles float-right image reordering by
        detecting images in has-float-image containers.

        Args:
            html_content: HTML string containing trip-image elements
            entry_date: Date string (YYYY-MM-DD) for the entry
            display_date: Formatted date for display (e.g., "Friday, Sept. 8, 2025")
            document_order: Starting order number for images in this entry

        Returns:
            List of TravelogImageMetadata objects
        """
        # Use HTML parser for robust extraction and float-right reordering
        parser = TravelogImageExtractor()
        parser.feed(html_content)
        images = parser.get_images()

        # Convert to TravelogImageMetadata with document_order
        result = []
        for img_data in images:
            result.append(TravelogImageMetadata(
                uuid=img_data['uuid'],
                entry_date=entry_date,
                layout=img_data['layout'],
                document_order=document_order,
                caption=img_data['caption'],
                display_date=display_date,
            ))
            document_order += 1

        return result

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

            entry_date = entry.date.isoformat()
            display_date = entry.display_date_abbrev
            entry_images = cls._extract_images_from_html(
                entry.text,
                entry_date,
                display_date,
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


class DayPageBuilder:
    """
    Builds display data for travelog day pages.

    Encapsulates all computation needed for rendering a day page:
    - Day number calculation (excluding prologue/epilogue)
    - TOC entry generation with active state
    - Current entry navigation resolution (prev/next)
    - First/last day boundary detection

    This replaces the anti-pattern of dynamically attaching day_number
    attributes to model instances in the view.
    """

    @classmethod
    def build( cls,
               entries      : List[JournalEntryContent],
               target_date  : date                  ) -> DayPageData:
        """
        Build complete day page context from entries.

        Args:
            entries: List of journal/travelog entries ordered by date
            target_date: The date of the entry being viewed

        Returns:
            DayPageData containing TOC entries, current entry nav, and metadata

        Raises:
            Http404: If no entry matches target_date
        """
        toc_entries = []
        current_entry = None
        prev_date = None
        next_date = None
        current_day_number = None

        day_number = 0
        day_dates = []

        for idx, entry in enumerate( entries ):
            # Calculate day number (None for special entries)
            entry_day_number = None
            if not entry.is_special_entry:
                day_number += 1
                entry_day_number = day_number
                day_dates.append( entry.date )

            # Build TOC entry
            toc_entries.append( TocEntryData(
                entry = entry,
                day_number = entry_day_number,
                is_active = ( entry.date == target_date )
            ))

            # Find current entry and neighbors
            if entry.date == target_date:
                current_day_number = entry_day_number
                current_entry = entry
                if idx > 0:
                    prev_date = entries[idx - 1].date
                if idx < len(entries) - 1:
                    next_date = entries[idx + 1].date

        if current_entry is None:
            raise Http404(f"No entry found for date {target_date}")

        return DayPageData(
            toc_entries = toc_entries,
            current_entry = DayEntryNavData(
                entry = current_entry,
                day_number = current_day_number,
                prev_date = prev_date,
                next_date = next_date,
            ),
            day_count = len(day_dates),
            first_day_date = day_dates[0] if day_dates else None,
            last_day_date = day_dates[-1] if day_dates else None,
        )


class TocPageBuilder:
    """
    Builds display data for travelog table of contents pages.

    Encapsulates all computation needed for rendering a TOC page:
    - Day number calculation (excluding prologue/epilogue)
    - TOC entry generation for grid display
    - First/last day boundary detection
    """

    @classmethod
    def build( cls,
               entries : List[JournalEntryContent] ) -> TocPageData:
        """
        Build complete TOC page context from entries.

        Args:
            entries: List of journal/travelog entries ordered by date

        Returns:
            TocPageData containing TOC entries and metadata
        """
        toc_entries = []
        day_number = 0
        day_dates = []

        for entry in entries:
            # Calculate day number (None for special entries)
            entry_day_number = None
            if not entry.is_special_entry:
                day_number += 1
                entry_day_number = day_number
                day_dates.append( entry.date )

            # Build TOC entry
            toc_entries.append( TocEntryData(
                entry = entry,
                day_number = entry_day_number,
                is_active = False,
            ))

        return TocPageData(
            toc_entries = toc_entries,
            day_count = len(day_dates),
            first_day_date = day_dates[0] if day_dates else None,
            last_day_date = day_dates[-1] if day_dates else None,
        )
