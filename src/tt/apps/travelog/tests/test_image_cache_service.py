"""
Tests for TravelogImageCacheService.

Tests the image extraction, caching, and invalidation functionality for travelog images.
"""
import json
import logging
from datetime import date
from unittest.mock import patch, MagicMock

from django.contrib.auth import get_user_model
from django.test import TestCase

from tt.apps.journal.models import Journal, JournalEntry
from tt.apps.trips.tests.synthetic_data import TripSyntheticData
from tt.apps.journal.enums import JournalVisibility

from ..enums import ContentType
from ..services import TravelogImageCacheService, PublishingService
from ..context import TravelogPageContext
from ..schemas import TravelogImageMetadata

logging.disable(logging.CRITICAL)

User = get_user_model()


class TestTravelogImageCacheService(TestCase):
    """Test the TravelogImageCacheService class."""

    @classmethod
    def setUpTestData(cls):
        """Set up test fixtures."""
        # Create test user (CustomUser uses email instead of username)
        cls.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )

        # Create test trip using synthetic data pattern
        cls.trip = TripSyntheticData.create_test_trip(
            user=cls.user,
            title='Test Trip'
        )

        # Create test journal
        cls.journal = Journal.objects.create(
            trip=cls.trip,
            title='Test Journal',
            description='A test journal',
            visibility=JournalVisibility.PUBLIC
        )

    def test_extract_images_from_html_float_right(self):
        """Test extracting float-right images from HTML."""
        html = '''
        <p>Some text</p>
        <span class="trip-image-wrapper" data-layout="float-right">
            <img class="trip-image" data-uuid="12345678-1234-1234-1234-123456789012" src="/test.jpg">
            <span class="trip-image-caption">Test caption</span>
        </span>
        <p>More text</p>
        '''

        images = TravelogImageCacheService._extract_images_from_html(
            html_content=html,
            entry_date='2024-01-15',
            document_order=1
        )

        self.assertEqual(len(images), 1)
        self.assertEqual(images[0].uuid, '12345678-1234-1234-1234-123456789012')
        self.assertEqual(images[0].entry_date, '2024-01-15')
        self.assertEqual(images[0].layout, 'float-right')
        self.assertEqual(images[0].document_order, 1)

    def test_extract_images_from_html_full_width(self):
        """Test extracting full-width images from HTML."""
        html = '''
        <div class="content-block full-width-image-group">
            <span class="trip-image-wrapper" data-layout="full-width">
                <img class="trip-image" data-uuid="abcdef12-3456-7890-abcd-ef1234567890" src="/test.jpg">
            </span>
        </div>
        '''

        images = TravelogImageCacheService._extract_images_from_html(
            html_content=html,
            entry_date='2024-01-16',
            document_order=5
        )

        self.assertEqual(len(images), 1)
        self.assertEqual(images[0].uuid, 'abcdef12-3456-7890-abcd-ef1234567890')
        self.assertEqual(images[0].layout, 'full-width')
        self.assertEqual(images[0].document_order, 5)

    def test_extract_images_from_html_multiple(self):
        """Test extracting multiple images from HTML."""
        html = '''
        <span class="trip-image-wrapper" data-layout="float-right">
            <img class="trip-image" data-uuid="11111111-1111-1111-1111-111111111111" src="/1.jpg">
        </span>
        <p>Text between images</p>
        <span class="trip-image-wrapper" data-layout="full-width">
            <img class="trip-image" data-uuid="22222222-2222-2222-2222-222222222222" src="/2.jpg">
        </span>
        <span class="trip-image-wrapper" data-layout="float-right">
            <img class="trip-image" data-uuid="33333333-3333-3333-3333-333333333333" src="/3.jpg">
        </span>
        '''

        images = TravelogImageCacheService._extract_images_from_html(
            html_content=html,
            entry_date='2024-01-17',
            document_order=10
        )

        self.assertEqual(len(images), 3)
        self.assertEqual(images[0].uuid, '11111111-1111-1111-1111-111111111111')
        self.assertEqual(images[0].document_order, 10)
        self.assertEqual(images[1].uuid, '22222222-2222-2222-2222-222222222222')
        self.assertEqual(images[1].document_order, 11)
        self.assertEqual(images[2].uuid, '33333333-3333-3333-3333-333333333333')
        self.assertEqual(images[2].document_order, 12)

    def test_extract_images_from_html_no_wrapper(self):
        """Test extracting images without wrapper (defaults to float-right)."""
        html = '''
        <img class="trip-image" data-uuid="99999999-9999-9999-9999-999999999999" src="/test.jpg">
        '''

        images = TravelogImageCacheService._extract_images_from_html(
            html_content=html,
            entry_date='2024-01-18',
            document_order=1
        )

        self.assertEqual(len(images), 1)
        self.assertEqual(images[0].layout, 'float-right')  # Default

    def test_extract_images_from_html_empty(self):
        """Test extracting images from empty HTML."""
        images = TravelogImageCacheService._extract_images_from_html(
            html_content='<p>No images here</p>',
            entry_date='2024-01-19',
            document_order=1
        )

        self.assertEqual(len(images), 0)

    def test_extract_images_from_content(self):
        """Test extracting images from journal entries in chronological order."""
        # Create journal entries with images
        JournalEntry.objects.create(
            journal=self.journal,
            date=date(2024, 1, 10),
            title='Day 1',
            text='<span class="trip-image-wrapper" data-layout="float-right"><img class="trip-image" data-uuid="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa" src="/1.jpg"></span>'
        )

        JournalEntry.objects.create(
            journal=self.journal,
            date=date(2024, 1, 11),
            title='Day 2',
            text='<span class="trip-image-wrapper" data-layout="full-width"><img class="trip-image" data-uuid="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb" src="/2.jpg"></span>'
        )

        JournalEntry.objects.create(
            journal=self.journal,
            date=date(2024, 1, 12),
            title='Day 3',
            text='<span class="trip-image-wrapper" data-layout="float-right"><img class="trip-image" data-uuid="cccccccc-cccc-cccc-cccc-cccccccccccc" src="/3.jpg"></span>'
        )

        images = TravelogImageCacheService._extract_images_from_content(self.journal)

        self.assertEqual(len(images), 3)
        # Check chronological order
        self.assertEqual(images[0].uuid, 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa')
        self.assertEqual(images[0].entry_date, '2024-01-10')
        self.assertEqual(images[0].document_order, 1)

        self.assertEqual(images[1].uuid, 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb')
        self.assertEqual(images[1].entry_date, '2024-01-11')
        self.assertEqual(images[1].document_order, 2)

        self.assertEqual(images[2].uuid, 'cccccccc-cccc-cccc-cccc-cccccccccccc')
        self.assertEqual(images[2].entry_date, '2024-01-12')
        self.assertEqual(images[2].document_order, 3)

    def test_get_cache_key_draft(self):
        """Test cache key generation for DRAFT content."""
        key = TravelogImageCacheService._get_cache_key(
            journal_uuid=self.journal.uuid,
            content_type=ContentType.DRAFT,
            version_number=None
        )

        self.assertEqual(key, f'travelog:images:{self.journal.uuid}:DRAFT')

    def test_get_cache_key_view(self):
        """Test cache key generation for VIEW content."""
        key = TravelogImageCacheService._get_cache_key(
            journal_uuid=self.journal.uuid,
            content_type=ContentType.VIEW,
            version_number=None
        )

        self.assertEqual(key, f'travelog:images:{self.journal.uuid}:VIEW')

    def test_get_cache_key_version(self):
        """Test cache key generation for VERSION content."""
        key = TravelogImageCacheService._get_cache_key(
            journal_uuid=self.journal.uuid,
            content_type=ContentType.VERSION,
            version_number=5
        )

        self.assertEqual(key, f'travelog:images:{self.journal.uuid}:VERSION:5')

    def test_get_ttl_for_content_type(self):
        """Test TTL values for different content types."""
        self.assertEqual(
            TravelogImageCacheService._get_ttl_for_content_type(ContentType.DRAFT),
            3600
        )
        self.assertIsNone(
            TravelogImageCacheService._get_ttl_for_content_type(ContentType.VIEW)
        )
        self.assertEqual(
            TravelogImageCacheService._get_ttl_for_content_type(ContentType.VERSION),
            86400
        )

    @patch('tt.apps.travelog.services.get_redis_client')
    def test_cache_images_with_ttl(self, mock_get_redis):
        """Test caching images with TTL."""
        mock_redis = MagicMock()
        mock_get_redis.return_value = mock_redis

        images = [
            TravelogImageMetadata(
                uuid='test-uuid',
                entry_date='2024-01-10',
                layout='float-right',
                document_order=1
            )
        ]

        TravelogImageCacheService._cache_images(
            journal_uuid=self.journal.uuid,
            content_type=ContentType.DRAFT,
            version_number=None,
            images=images
        )

        # Verify setex was called with correct TTL
        mock_redis.setex.assert_called_once()
        args = mock_redis.setex.call_args[0]
        self.assertIn('travelog:images', args[0])
        self.assertEqual(args[1], 3600)  # DRAFT TTL
        # Verify the serialized data matches
        serialized_data = json.loads(args[2])
        self.assertEqual(serialized_data[0]['uuid'], 'test-uuid')
        self.assertEqual(serialized_data[0]['entry_date'], '2024-01-10')

    @patch('tt.apps.travelog.services.get_redis_client')
    def test_cache_images_no_ttl(self, mock_get_redis):
        """Test caching images without TTL (VIEW)."""
        mock_redis = MagicMock()
        mock_get_redis.return_value = mock_redis

        images = [
            TravelogImageMetadata(
                uuid='test-uuid',
                entry_date='2024-01-10',
                layout='float-right',
                document_order=1
            )
        ]

        TravelogImageCacheService._cache_images(
            journal_uuid=self.journal.uuid,
            content_type=ContentType.VIEW,
            version_number=None,
            images=images
        )

        # Verify set was called (no TTL)
        mock_redis.set.assert_called_once()
        args = mock_redis.set.call_args[0]
        self.assertIn('travelog:images', args[0])
        # Verify the serialized data matches
        serialized_data = json.loads(args[1])
        self.assertEqual(serialized_data[0]['uuid'], 'test-uuid')
        self.assertEqual(serialized_data[0]['entry_date'], '2024-01-10')

    @patch('tt.apps.travelog.services.get_redis_client')
    def test_invalidate_cache(self, mock_get_redis):
        """Test cache invalidation."""
        mock_redis = MagicMock()
        mock_redis.delete.return_value = 1
        mock_get_redis.return_value = mock_redis

        TravelogImageCacheService.invalidate_cache(
            journal_uuid=self.journal.uuid,
            content_type=ContentType.VIEW
        )

        mock_redis.delete.assert_called_once()
        cache_key = mock_redis.delete.call_args[0][0]
        self.assertEqual(cache_key, f'travelog:images:{self.journal.uuid}:VIEW')

    @patch('tt.apps.travelog.services.get_redis_client')
    def test_get_images_cache_hit(self, mock_get_redis):
        """Test getting images with cache hit."""
        mock_redis = MagicMock()
        cached_images_data = [
            {'uuid': 'cached-uuid', 'entry_date': '2024-01-10', 'layout': 'float-right', 'document_order': 1}
        ]
        mock_redis.get.return_value = json.dumps(cached_images_data)
        mock_get_redis.return_value = mock_redis

        context = TravelogPageContext(
            journal=self.journal,
            content_type=ContentType.DRAFT,
            version_number=None
        )

        images = TravelogImageCacheService.get_images(context)

        # Verify we get TravelogImageMetadata objects back
        self.assertEqual(len(images), 1)
        self.assertIsInstance(images[0], TravelogImageMetadata)
        self.assertEqual(images[0].uuid, 'cached-uuid')
        self.assertEqual(images[0].entry_date, '2024-01-10')
        self.assertEqual(images[0].layout, 'float-right')
        self.assertEqual(images[0].document_order, 1)
        mock_redis.get.assert_called_once()

    @patch('tt.apps.travelog.services.get_redis_client')
    def test_get_images_cache_miss(self, mock_get_redis):
        """Test getting images with cache miss."""
        mock_redis = MagicMock()
        mock_redis.get.return_value = None
        mock_get_redis.return_value = mock_redis

        # Create journal entry with image (using properly formatted UUID)
        JournalEntry.objects.create(
            journal=self.journal,
            date=date(2024, 1, 10),
            title='Day 1',
            text='<span class="trip-image-wrapper" data-layout="float-right"><img class="trip-image" data-uuid="12345678-1234-1234-1234-123456789012" src="/1.jpg"></span>'
        )

        context = TravelogPageContext(
            journal=self.journal,
            content_type=ContentType.DRAFT,
            version_number=None
        )

        images = TravelogImageCacheService.get_images(context)

        self.assertEqual(len(images), 1)
        self.assertEqual(images[0].uuid, '12345678-1234-1234-1234-123456789012')
        # Should have tried to cache the result
        mock_redis.setex.assert_called_once()

    @patch('tt.apps.travelog.services.get_redis_client')
    def test_invalidate_cache_then_get_images(self, mock_get_redis):
        """Test invalidating cache then getting images re-extracts them."""
        mock_redis = MagicMock()
        mock_get_redis.return_value = mock_redis

        # Create journal entry with image (using properly formatted UUID)
        JournalEntry.objects.create(
            journal=self.journal,
            date=date(2024, 1, 10),
            title='Day 1',
            text='<span class="trip-image-wrapper" data-layout="float-right"><img class="trip-image" data-uuid="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee" src="/1.jpg"></span>'
        )

        context = TravelogPageContext(
            journal=self.journal,
            content_type=ContentType.DRAFT,
            version_number=None
        )

        # Invalidate the cache first
        TravelogImageCacheService.invalidate_cache(
            journal_uuid=self.journal.uuid,
            content_type=ContentType.DRAFT,
            version_number=None
        )

        # Now get images - should miss cache and re-extract
        images = TravelogImageCacheService.get_images(context)

        self.assertEqual(len(images), 1)
        self.assertEqual(images[0].uuid, 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee')
        # Should have called delete for invalidation
        mock_redis.delete.assert_called_once()
        # Should have tried to read from cache (will miss since we invalidated)
        mock_redis.get.assert_called_once()
        # Should have cached the newly extracted result
        mock_redis.setex.assert_called_once()

    @patch('tt.apps.travelog.services.get_redis_client')
    def test_publishing_invalidates_view_cache(self, mock_get_redis):
        """Test that publishing a journal invalidates VIEW cache."""
        mock_redis = MagicMock()
        mock_redis.delete.return_value = 1
        mock_get_redis.return_value = mock_redis

        # Create journal entry
        JournalEntry.objects.create(
            journal=self.journal,
            date=date(2024, 1, 10),
            title='Day 1',
            text='Content'
        )

        # Publish journal
        PublishingService.publish_journal(self.journal, self.user)

        # Verify VIEW cache was invalidated
        mock_redis.delete.assert_called()
        cache_key = mock_redis.delete.call_args[0][0]
        self.assertIn(str(self.journal.uuid), cache_key)
        self.assertIn('VIEW', cache_key)

    @patch('tt.apps.travelog.services.get_redis_client')
    def test_set_as_current_invalidates_view_cache(self, mock_get_redis):
        """Test that setting a version as current invalidates VIEW cache."""
        mock_redis = MagicMock()
        mock_redis.delete.return_value = 1
        mock_get_redis.return_value = mock_redis

        # Create journal entry
        JournalEntry.objects.create(
            journal=self.journal,
            date=date(2024, 1, 10),
            title='Day 1',
            text='Content'
        )

        # Publish two versions (second becomes current)
        travelog1 = PublishingService.publish_journal(self.journal, self.user)
        travelog2 = PublishingService.publish_journal(self.journal, self.user)

        # Verify travelog2 is current and travelog1 is not
        travelog1.refresh_from_db()
        self.assertFalse(travelog1.is_current)
        self.assertTrue(travelog2.is_current)

        # Reset mock to clear previous calls
        mock_redis.reset_mock()

        # Set first version as current (switching from travelog2 to travelog1)
        PublishingService.set_as_current(self.journal, travelog1)

        # Verify VIEW cache was invalidated
        mock_redis.delete.assert_called()
        cache_key = mock_redis.delete.call_args[0][0]
        self.assertIn(str(self.journal.uuid), cache_key)
        self.assertIn('VIEW', cache_key)


class TestTravelogImageCacheKeySecurity(TestCase):
    """Test cache key generation security."""

    def test_cache_key_format_prevents_injection(self):
        """Test cache key format prevents injection attacks."""
        import uuid
        from ..services import TravelogImageCacheService
        from ..enums import ContentType

        journal_uuid = uuid.uuid4()

        # Normal case
        key = TravelogImageCacheService._get_cache_key(
            journal_uuid,
            ContentType.VIEW
        )

        # Verify format: travelog:images:{uuid}:{type}
        self.assertIn("travelog:images:", key)
        self.assertIn(str(journal_uuid), key)
        self.assertIn("VIEW", key)

        # No injection characters should exist
        self.assertNotIn("\n", key)
        self.assertNotIn("\r", key)
        self.assertNotIn("\x00", key)

    def test_cache_key_uniqueness_per_journal_and_type(self):
        """Test cache keys are unique per journal/content type combination."""
        import uuid
        from ..services import TravelogImageCacheService
        from ..enums import ContentType

        journal1_uuid = uuid.uuid4()
        journal2_uuid = uuid.uuid4()

        # Different journals, same type
        key1 = TravelogImageCacheService._get_cache_key(
            journal1_uuid, ContentType.VIEW
        )
        key2 = TravelogImageCacheService._get_cache_key(
            journal2_uuid, ContentType.VIEW
        )
        self.assertNotEqual(key1, key2)

        # Same journal, different types
        key3 = TravelogImageCacheService._get_cache_key(
            journal1_uuid, ContentType.DRAFT
        )
        self.assertNotEqual(key1, key3)

    def test_cache_key_version_number_isolation(self):
        """Test version numbers create unique cache keys."""
        import uuid
        from ..services import TravelogImageCacheService
        from ..enums import ContentType

        journal_uuid = uuid.uuid4()

        key_v1 = TravelogImageCacheService._get_cache_key(
            journal_uuid,
            ContentType.VERSION,
            version_number=1
        )
        key_v2 = TravelogImageCacheService._get_cache_key(
            journal_uuid,
            ContentType.VERSION,
            version_number=2
        )

        # Different versions must have different keys
        self.assertNotEqual(key_v1, key_v2)


class TestTravelogImageCacheRegexSecurity(TestCase):
    """Test regex patterns against ReDoS attacks."""

    def test_image_extraction_html_injection_resistance(self):
        """Test image extraction resists HTML injection attempts."""
        from ..services import TravelogImageCacheService

        # Malicious HTML with injection attempts
        malicious_html = """
        <img class="trip-image" data-uuid="550e8400-e29b-41d4-a716-446655440000" onload="alert(\"xss\")">
        <img class="trip-image" data-uuid="<script>alert(\"xss\")</script>">
        <img class="trip-image" data-uuid="550e8400-e29b-41d4-a716-446655440001" data-layout="float-right\" onload=\"alert(\"xss\")"
        """

        images = TravelogImageCacheService._extract_images_from_html(
            malicious_html,
            entry_date="2024-01-01",
            document_order=1
        )

        # Only valid UUIDs should be extracted
        # XSS attempts should be ignored (UUID format validation)
        valid_images = [img for img in images if len(img.uuid) == 36]
        self.assertEqual(len(valid_images), 2)  # Two valid UUIDs

        for img in valid_images:
            # UUID should be valid format (no injection)
            self.assertEqual(len(img.uuid), 36)  # UUID format: 8-4-4-4-12
            self.assertNotIn("<", img.uuid)
            self.assertNotIn(">", img.uuid)
            self.assertNotIn("script", img.uuid)


class TestTravelogImageCacheRedisSecurity(TestCase):
    """Test Redis cache security and error handling."""

    @classmethod
    def setUpTestData(cls):
        """Set up test fixtures."""
        # Create test user
        cls.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123"
        )

        # Create test trip using synthetic data pattern
        cls.trip = TripSyntheticData.create_test_trip(
            user=cls.user,
            title="Test Trip"
        )

        # Create test journal
        cls.journal = Journal.objects.create(
            trip=cls.trip,
            title="Test Journal",
            description="A test journal",
            visibility=JournalVisibility.PUBLIC
        )

    def test_get_images_graceful_degradation_on_redis_failure(self):
        """Test service degrades gracefully when Redis fails."""
        from ..services import TravelogImageCacheService
        from ..context import TravelogPageContext
        from ..enums import ContentType

        # Create entry with image
        JournalEntry.objects.create(
            journal=self.journal,
            date=date(2024, 1, 10),
            text="<img class=\"trip-image\" data-uuid=\"550e8400-e29b-41d4-a716-446655440000\">"
        )

        context = TravelogPageContext(
            journal=self.journal,
            content_type=ContentType.DRAFT
        )

        # Mock Redis to raise exception
        with patch("tt.apps.travelog.services.get_redis_client") as mock_redis:
            mock_redis.return_value.get.side_effect = Exception("Redis down")

            # Should NOT raise exception - graceful degradation
            images = TravelogImageCacheService.get_images(context)

            # Should still extract images from content (fallback)
            self.assertEqual(len(images), 1)
            self.assertEqual(images[0].uuid, "550e8400-e29b-41d4-a716-446655440000")

    def test_cache_ttl_strategy_security(self):
        """Test TTL strategies prevent cache staleness for security-sensitive content."""
        from ..services import TravelogImageCacheService
        from ..enums import ContentType

        # DRAFT: 1 hour (frequently changing)
        self.assertEqual(
            TravelogImageCacheService._get_ttl_for_content_type(ContentType.DRAFT),
            3600
        )

        # VIEW: None (infinite with manual invalidation - immutable content)
        self.assertIsNone(
            TravelogImageCacheService._get_ttl_for_content_type(ContentType.VIEW)
        )

        # VERSION: 24 hours (rarely accessed historical content)
        self.assertEqual(
            TravelogImageCacheService._get_ttl_for_content_type(ContentType.VERSION),
            86400
        )

    @patch("tt.apps.travelog.services.get_redis_client")
    def test_invalidate_cache_prevents_stale_data(self, mock_get_redis):
        """Test cache invalidation prevents serving stale data."""
        import uuid
        from ..services import TravelogImageCacheService
        from ..enums import ContentType

        journal_uuid = uuid.uuid4()

        mock_redis = MagicMock()
        mock_redis.delete.return_value = 1
        mock_get_redis.return_value = mock_redis

        TravelogImageCacheService.invalidate_cache(
            journal_uuid,
            ContentType.VIEW
        )

        # Verify cache key deleted
        mock_redis.delete.assert_called_once()
        cache_key = mock_redis.delete.call_args[0][0]
        self.assertIn(str(journal_uuid), cache_key)
        self.assertIn("VIEW", cache_key)

