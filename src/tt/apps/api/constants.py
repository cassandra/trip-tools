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
    LAST_USED_AT = 'last_used_at'

    # -------------------------------------------------------------------------
    # Locations
    # -------------------------------------------------------------------------
    LATITUDE = 'latitude'
    LONGITUDE = 'longitude'
    SUBCATEGORY_SLUG = 'subcategory_slug'
    TRIP_UUID = 'trip_uuid'
