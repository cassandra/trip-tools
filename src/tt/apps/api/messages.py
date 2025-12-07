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

    # -------------------------------------------------------------------------
    # Authentication messages
    # -------------------------------------------------------------------------
    INVALID_TOKEN = 'Invalid token.'
    USER_INACTIVE = 'User inactive or deleted.'

    # -------------------------------------------------------------------------
    # Rate limiting and quota messages
    # -------------------------------------------------------------------------
    TOKEN_LIMIT_REACHED = 'Maximum number of API keys reached. Please delete unused keys first.'
    RATE_LIMIT_EXCEEDED = 'Rate limit exceeded. Please try again later.'

    # -------------------------------------------------------------------------
    # Generic error messages
    # -------------------------------------------------------------------------
    BAD_REQUEST = 'Bad request'
