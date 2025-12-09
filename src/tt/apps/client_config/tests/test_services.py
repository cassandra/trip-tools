"""
Tests for ClientConfigService.

Focuses on high-value testing of:
- Config building with correct structure and ordering
- Version hash stability (same data = same hash)
- Caching behavior (get from cache, build on miss)
- Cache invalidation

Note: These tests use the seeded location data from migrations.
They do not create their own test categories to avoid conflicts.
"""

import logging
from unittest.mock import patch

from django.test import TestCase

from tt.apps.api.constants import APIFields as F
from tt.apps.locations.models import LocationCategory, LocationSubCategory

from ..services import ClientConfigService

logging.disable(logging.CRITICAL)


class ClientConfigServiceTestCase(TestCase):
    """
    Test ClientConfigService business logic.

    Uses the seeded location data from migrations (Dining, Attractions, etc.)
    """

    def setUp(self):
        """Clear cache before each test."""
        ClientConfigService.invalidate_cache()

    # -------------------------------------------------------------------------
    # Config Structure Tests
    # -------------------------------------------------------------------------

    def test_get_config_serialized_returns_correct_structure(self):
        """Test get_config_serialized returns dict with version and location_categories."""
        config = ClientConfigService.get_config_serialized()

        self.assertIn(F.VERSION, config)
        self.assertIn(F.LOCATION_CATEGORIES, config)
        self.assertIsInstance(config[F.VERSION], str)
        self.assertIsInstance(config[F.LOCATION_CATEGORIES], list)

    def test_get_config_serialized_categories_sorted_alphabetically(self):
        """Test categories are sorted alphabetically by name."""
        config = ClientConfigService.get_config_serialized()
        categories = config[F.LOCATION_CATEGORIES]

        # Verify at least some categories exist from seed data
        self.assertGreater(len(categories), 0)

        # Verify alphabetical order
        names = [c[F.NAME] for c in categories]
        self.assertEqual(names, sorted(names))

    def test_get_config_serialized_subcategories_sorted_alphabetically(self):
        """Test subcategories within each category are sorted alphabetically."""
        config = ClientConfigService.get_config_serialized()
        categories = config[F.LOCATION_CATEGORIES]

        # Find Dining category (from seed data)
        dining = next((c for c in categories if c[F.SLUG] == 'dining'), None)
        self.assertIsNotNone(dining, 'Dining category should exist from seed')

        subcategories = dining[F.SUBCATEGORIES]
        self.assertGreater(len(subcategories), 0)

        # Verify alphabetical order within category
        names = [s[F.NAME] for s in subcategories]
        self.assertEqual(names, sorted(names))

    def test_get_config_serialized_category_has_all_fields(self):
        """Test each category has all required fields."""
        config = ClientConfigService.get_config_serialized()
        category = config[F.LOCATION_CATEGORIES][0]

        self.assertIn(F.ID, category)
        self.assertIn(F.NAME, category)
        self.assertIn(F.SLUG, category)
        self.assertIn(F.ICON_CODE, category)
        self.assertIn(F.COLOR_CODE, category)
        self.assertIn(F.SUBCATEGORIES, category)

    def test_get_config_serialized_subcategory_has_all_fields(self):
        """Test each subcategory has all required fields."""
        config = ClientConfigService.get_config_serialized()
        # Find a category with subcategories (Dining has them)
        dining = next(
            c for c in config[F.LOCATION_CATEGORIES]
            if c[F.SLUG] == 'dining'
        )
        subcategory = dining[F.SUBCATEGORIES][0]

        self.assertIn(F.ID, subcategory)
        self.assertIn(F.NAME, subcategory)
        self.assertIn(F.SLUG, subcategory)
        self.assertIn(F.ICON_CODE, subcategory)
        self.assertIn(F.COLOR_CODE, subcategory)

    # -------------------------------------------------------------------------
    # Version Hash Tests
    # -------------------------------------------------------------------------

    def test_version_is_md5_hash(self):
        """Test version is a valid MD5 hash (32 hex characters)."""
        config = ClientConfigService.get_config_serialized()
        version = config[F.VERSION]

        self.assertEqual(len(version), 32)
        self.assertTrue(all(c in '0123456789abcdef' for c in version))

    def test_version_is_stable_for_same_data(self):
        """Test same data produces same version hash."""
        ClientConfigService.invalidate_cache()
        config1 = ClientConfigService.get_config_serialized()

        ClientConfigService.invalidate_cache()
        config2 = ClientConfigService.get_config_serialized()

        self.assertEqual(config1[F.VERSION], config2[F.VERSION])

    def test_version_changes_when_data_changes(self):
        """Test version changes when category data changes."""
        config1 = ClientConfigService.get_config_serialized()
        version1 = config1[F.VERSION]

        # Change a category (use Dining from seed data)
        dining = LocationCategory.objects.get(slug='dining')
        original_name = dining.name
        dining.name = 'Fine Dining'
        dining.save()

        ClientConfigService.invalidate_cache()
        config2 = ClientConfigService.get_config_serialized()
        version2 = config2[F.VERSION]

        self.assertNotEqual(version1, version2)

        # Restore original name
        dining.name = original_name
        dining.save()

    def test_get_version_returns_same_as_config_serialized_version(self):
        """Test get_version() returns same value as get_config_serialized()[version]."""
        config = ClientConfigService.get_config_serialized()
        version = ClientConfigService.get_version()

        self.assertEqual(version, config[F.VERSION])

    # -------------------------------------------------------------------------
    # Caching Tests
    # -------------------------------------------------------------------------

    def test_get_config_serialized_uses_cache_on_second_call(self):
        """Test get_config_serialized returns cached result on subsequent calls."""
        with patch.object(
            ClientConfigService, '_build_and_cache_config',
            wraps=ClientConfigService._build_and_cache_config
        ) as mock_build:
            # First call should build
            ClientConfigService.get_config_serialized()
            self.assertEqual(mock_build.call_count, 1)

            # Second call should use cache (no additional build)
            ClientConfigService.get_config_serialized()
            self.assertEqual(mock_build.call_count, 1)

    def test_invalidate_cache_causes_rebuild(self):
        """Test invalidate_cache causes next get_config_serialized to rebuild."""
        with patch.object(
            ClientConfigService, '_build_and_cache_config',
            wraps=ClientConfigService._build_and_cache_config
        ) as mock_build:
            # First call builds
            ClientConfigService.get_config_serialized()
            self.assertEqual(mock_build.call_count, 1)

            # Invalidate
            ClientConfigService.invalidate_cache()

            # Next call should rebuild
            ClientConfigService.get_config_serialized()
            self.assertEqual(mock_build.call_count, 2)

    def test_get_config_serialized_works_without_redis(self):
        """Test get_config_serialized works when Redis is unavailable."""
        with patch(
            'tt.apps.client_config.services.get_redis_client',
            return_value=None
        ):
            # Should still return valid config
            config = ClientConfigService.get_config_serialized()

            self.assertIn(F.VERSION, config)
            self.assertIn(F.LOCATION_CATEGORIES, config)

    def test_get_version_works_without_redis(self):
        """Test get_version works when Redis is unavailable."""
        with patch(
            'tt.apps.client_config.services.get_redis_client',
            return_value=None
        ):
            # Should still return valid version
            version = ClientConfigService.get_version()

            self.assertEqual(len(version), 32)

    # -------------------------------------------------------------------------
    # Empty Data Tests
    # -------------------------------------------------------------------------

    def test_get_config_serialized_category_with_no_subcategories(self):
        """Test category with no subcategories has empty subcategories list."""
        # Towns category from seed data has no subcategories
        config = ClientConfigService.get_config_serialized()
        towns = next(
            (c for c in config[F.LOCATION_CATEGORIES] if c[F.SLUG] == 'towns'),
            None
        )

        self.assertIsNotNone(towns, 'Towns category should exist from seed')
        self.assertEqual(towns[F.SUBCATEGORIES], [])


class ClientConfigSignalTests(TestCase):
    """
    Test signal-based cache invalidation.

    Uses existing Dining category from seed data for signal tests
    to avoid unique constraint issues.
    """

    @classmethod
    def setUpTestData(cls):
        """Get reference to seeded category (runs once per class)."""
        cls.category = LocationCategory.objects.get(slug='dining')
        cls.original_name = cls.category.name

    def setUp(self):
        """Clear cache before each test."""
        ClientConfigService.invalidate_cache()

    def tearDown(self):
        """Restore original name if changed."""
        self.category.refresh_from_db()
        if self.category.name != self.original_name:
            self.category.name = self.original_name
            self.category.save()

    def test_category_save_invalidates_cache(self):
        """Test saving a category invalidates the cache."""
        # Prime the cache
        ClientConfigService.get_config_serialized()

        with patch.object(
            ClientConfigService, 'invalidate_cache',
            wraps=ClientConfigService.invalidate_cache
        ) as mock_invalidate:
            # Update category
            self.category.name = 'Updated Category'
            self.category.save()

            # Signal should have called invalidate_cache
            mock_invalidate.assert_called()

    def test_category_create_invalidates_cache(self):
        """Test creating a category invalidates the cache."""
        # Prime the cache
        ClientConfigService.get_config_serialized()

        with patch.object(
            ClientConfigService, 'invalidate_cache',
            wraps=ClientConfigService.invalidate_cache
        ) as mock_invalidate:
            # Create new category with unique slug
            new_cat = LocationCategory.objects.create(
                name='Signal Test Category',
                slug='signal-test-unique',
                icon_code='1001',
                color_code='RGB(50,50,50)',
            )

            mock_invalidate.assert_called()

            # Cleanup
            new_cat.delete()

    def test_category_delete_invalidates_cache(self):
        """Test deleting a category invalidates the cache."""
        # Create a temporary category to delete
        temp_cat = LocationCategory.objects.create(
            name='Temp Category',
            slug='temp-delete-test',
            icon_code='1001',
            color_code='RGB(50,50,50)',
        )
        ClientConfigService.invalidate_cache()

        # Prime the cache
        ClientConfigService.get_config_serialized()

        with patch.object(
            ClientConfigService, 'invalidate_cache',
            wraps=ClientConfigService.invalidate_cache
        ) as mock_invalidate:
            # Delete category
            temp_cat.delete()

            mock_invalidate.assert_called()

    def test_subcategory_save_invalidates_cache(self):
        """Test saving a subcategory invalidates the cache."""
        # Use existing subcategory from seed data
        subcategory = LocationSubCategory.objects.filter(
            category=self.category
        ).first()
        original_name = subcategory.name
        ClientConfigService.invalidate_cache()

        # Prime the cache
        ClientConfigService.get_config_serialized()

        with patch.object(
            ClientConfigService, 'invalidate_cache',
            wraps=ClientConfigService.invalidate_cache
        ) as mock_invalidate:
            # Update subcategory
            subcategory.name = 'Updated Sub'
            subcategory.save()

            mock_invalidate.assert_called()

        # Restore
        subcategory.name = original_name
        subcategory.save()

    def test_subcategory_delete_invalidates_cache(self):
        """Test deleting a subcategory invalidates the cache."""
        # Create a temporary subcategory to delete
        subcategory = LocationSubCategory.objects.create(
            category=self.category,
            name='Temp Sub',
            slug='temp-sub-delete-test',
            icon_code='2000',
            color_code='RGB(150,150,150)',
        )
        ClientConfigService.invalidate_cache()

        # Prime the cache
        ClientConfigService.get_config_serialized()

        with patch.object(
            ClientConfigService, 'invalidate_cache',
            wraps=ClientConfigService.invalidate_cache
        ) as mock_invalidate:
            # Delete subcategory
            subcategory.delete()

            mock_invalidate.assert_called()
