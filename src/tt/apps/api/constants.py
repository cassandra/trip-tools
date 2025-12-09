"""
API field name constants for consistent serialization.

These constants define the JSON keys used in API responses and requests.
Using constants ensures consistency and makes refactoring safer.

All API field names should be defined here to ensure consistency across
modules and prevent divergence. Check here first before adding a new field.
"""


class APIFields:
    """
    Field names for API responses and requests.

    All modules should import from here to ensure consistent naming.
    """

    # -------------------------------------------------------------------------
    # Common fields (used across multiple endpoints)
    # -------------------------------------------------------------------------
    ERROR = 'error'
    UUID = 'uuid'
    NAME = 'name'
    TITLE = 'title'
    EMAIL = 'email'
    CREATED_AT = 'created_at'
    CREATED_DATETIME = 'created_datetime'

    # -------------------------------------------------------------------------
    # API tokens
    # -------------------------------------------------------------------------
    LOOKUP_KEY = 'lookup_key'
    TOKEN = 'token'
    TOKEN_TYPE = 'token_type'
    LAST_USED_AT = 'last_used_at'

    # -------------------------------------------------------------------------
    # Trips
    # -------------------------------------------------------------------------
    DESCRIPTION = 'description'
    TRIP_STATUS = 'trip_status'
    VERSION = 'version'
    GMM_MAP_ID = 'gmm_map_id'

    # -------------------------------------------------------------------------
    # Locations
    # -------------------------------------------------------------------------
    LATITUDE = 'latitude'
    LONGITUDE = 'longitude'
    SUBCATEGORY_SLUG = 'subcategory_slug'
    TRIP_UUID = 'trip_uuid'

    # -------------------------------------------------------------------------
    # Client Config / Location Categories
    # -------------------------------------------------------------------------
    ID = 'id'
    SLUG = 'slug'
    ICON_CODE = 'icon_code'
    COLOR_CODE = 'color_code'
    SUBCATEGORIES = 'subcategories'
    LOCATION_CATEGORIES = 'location_categories'
    CONFIG_VERSION = 'config_version'
