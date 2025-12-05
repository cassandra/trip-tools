"""
API message helpers for consistent user-facing messages.

Use these helpers to ensure consistent phrasing across API responses.
Add parameterized methods for common patterns, or static strings for one-offs.
"""


class APIMessages:
    """
    Standardized messages for API responses.

    Methods generate parameterized messages for common patterns.
    Class attributes provide static one-off messages.
    """

    @staticmethod
    def is_required(field: str) -> str:
        return f'{field} is required'

    @staticmethod
    def not_found(resource: str) -> str:
        return f'{resource} not found'

    @staticmethod
    def already_exists(resource: str, field: str) -> str:
        return f'{resource} with this {field} already exists'
