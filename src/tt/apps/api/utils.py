"""
Utility functions for API request data handling.

These helpers provide consistent whitespace handling and type conversion
for data extracted from API requests.
"""
from typing import Optional
from uuid import UUID


def clean_str(value: str) -> str:
    """
    Strip whitespace from a string value.

    Use for URL path parameters and other string inputs that need sanitizing.
    """
    return value.strip() if value else ''


def get_str(request_data, key: str, default: str = '') -> str:
    """
    Get a string value from request data, stripped of leading/trailing whitespace.

    Args:
        request_data: The request.data dict-like object
        key: The key to look up
        default: Value to return if key is missing or None

    Returns:
        Stripped string value, or default if not present
    """
    value = request_data.get(key)
    if value is None:
        return default
    return str(value).strip()


def get_uuid(request_data, key: str) -> Optional[UUID]:
    """
    Get a UUID value from request data.

    Handles whitespace stripping and UUID parsing.

    Args:
        request_data: The request.data dict-like object
        key: The key to look up

    Returns:
        UUID if valid, None if missing or invalid format
    """
    value = request_data.get(key)
    if value is None:
        return None

    str_value = str(value).strip()
    if not str_value:
        return None

    try:
        return UUID(str_value)
    except (ValueError, AttributeError):
        return None
