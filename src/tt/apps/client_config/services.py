"""
Client config service for aggregating and caching configuration data.

Provides location categories and subcategories to browser extensions with
efficient caching and signal-based invalidation.
"""

import hashlib
import json
import logging
from typing import Any, Dict, Optional

from tt.apps.common.redis_client import get_redis_client
from tt.apps.locations.models import LocationCategory

from .api.serializers import ClientConfigSerializer
from .schemas import ClientConfig

logger = logging.getLogger(__name__)


class ClientConfigService:
    """
    Service for building and caching client configuration.

    Aggregates location categories/subcategories into a single payload with
    version hash for efficient sync. Uses Redis caching with infinite TTL
    and signal-based invalidation when source data changes.

    Cache Strategy:
    - Infinite TTL (no expiration)
    - Invalidated via signals when LocationCategory or LocationSubCategory changes
    - Version is MD5 hash of payload for change detection
    """

    CACHE_KEY_PAYLOAD = 'client_config:payload'
    CACHE_KEY_VERSION = 'client_config:version'

    @classmethod
    def get_config_serialized(cls) -> Dict[str, Any]:
        """
        Get the full client config, serialized for API response.

        Returns cached serialized config if available, otherwise builds,
        serializes, and caches it.

        Returns:
            Dict with 'version' and 'location_categories' keys, ready for API response
        """
        # Try cache first
        cached = cls._get_cached_payload()
        if cached is not None:
            return cached

        # Cache miss - build, serialize, and cache
        return cls._build_and_cache_config()

    @classmethod
    def get_version(cls) -> str:
        """
        Get just the config version hash.

        More efficient than get_config_serialized() when only version is needed
        (e.g., for ExtensionStatusView).

        Returns:
            MD5 hash string of the config payload
        """
        # Try cache first
        try:
            redis_client = get_redis_client()
            if redis_client:
                cached_version = redis_client.get(cls.CACHE_KEY_VERSION)
                if cached_version:
                    logger.debug("Cache hit for config version")
                    return cached_version.decode('utf-8')
        except Exception as e:
            logger.warning(f"Redis error getting config version: {e}")

        # Cache miss - need to build full config to get version
        config = cls._build_and_cache_config()
        return config['version']

    @classmethod
    def invalidate_cache(cls) -> None:
        """
        Invalidate cached config.

        Called by signal handlers when LocationCategory or LocationSubCategory
        changes. Next request will rebuild the config from the database.
        """
        try:
            redis_client = get_redis_client()
            if not redis_client:
                return

            deleted_payload = redis_client.delete(cls.CACHE_KEY_PAYLOAD)
            deleted_version = redis_client.delete(cls.CACHE_KEY_VERSION)

            if deleted_payload or deleted_version:
                logger.info("Invalidated client config cache")
            else:
                logger.debug("No client config cache to invalidate")

        except Exception as e:
            logger.warning(f"Redis error invalidating client config cache: {e}")

    @classmethod
    def _get_cached_payload(cls) -> Optional[Dict[str, Any]]:
        """
        Get serialized config from cache if available.

        Returns:
            Cached serialized config dict or None if not cached
        """
        try:
            redis_client = get_redis_client()
            if redis_client:
                cached_data = redis_client.get(cls.CACHE_KEY_PAYLOAD)
                if cached_data:
                    logger.debug("Cache hit for client config")
                    return json.loads(cached_data)
                logger.debug("Cache miss for client config")
        except Exception as e:
            logger.warning(f"Redis error getting cached config: {e}")

        return None

    @classmethod
    def _build_and_cache_config(cls) -> Dict[str, Any]:
        """
        Build config from database, serialize it, and cache.

        Returns:
            Serialized config dict with version and location_categories
        """
        logger.debug("Building client config from database")

        # Build typed ClientConfig with model instances
        categories = list(LocationCategory.objects.order_by('name'))
        client_config = ClientConfig(
            version='',  # Placeholder - computed after serialization
            location_categories=categories,
        )

        # Serialize using ClientConfigSerializer
        serialized = ClientConfigSerializer(client_config).data

        # Compute version hash from serialized location_categories
        # Use sort_keys=True for stable ordering
        categories_json = json.dumps(
            serialized['location_categories'],
            sort_keys=True
        )
        version = hashlib.md5(categories_json.encode('utf-8')).hexdigest()

        # Update version in serialized output
        serialized['version'] = version

        # Cache the result
        cls._cache_payload(serialized, version)

        return serialized

    @classmethod
    def _cache_payload(cls, payload: Dict[str, Any], version: str) -> None:
        """
        Store serialized config in Redis cache with infinite TTL.
        """
        try:
            redis_client = get_redis_client()
            if not redis_client:
                logger.debug("Redis not available, skipping cache storage")
                return

            # Cache full payload
            payload_json = json.dumps(payload)
            redis_client.set(cls.CACHE_KEY_PAYLOAD, payload_json)

            # Cache version separately for efficient lookups
            redis_client.set(cls.CACHE_KEY_VERSION, version)

            logger.debug(f"Cached client config (version={version})")

        except Exception as e:
            logger.warning(f"Redis error caching client config: {e}")
