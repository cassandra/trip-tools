from datetime import date as date_type


class ISODateConverter:
    """
    Custom URL converter for ISO 8601 date format (YYYY-MM-DD).

    Validates date format at the URL routing level and converts to datetime.date objects.
    Invalid dates will automatically result in 404 responses.

    Usage in urls.py:
        from django.urls import register_converter
        from .converters import ISODateConverter

        register_converter(ISODateConverter, 'isodate')

        urlpatterns = [
            path('day/<isodate:date>', view, name='day'),
        ]
    """

    # Regex pattern for YYYY-MM-DD format
    regex = r'\d{4}-\d{2}-\d{2}'

    def to_python(self, value: str) -> date_type:
        """
        Convert URL string to datetime.date object.

        Args:
            value: Date string in YYYY-MM-DD format

        Returns:
            datetime.date object

        Raises:
            ValueError: If date string is invalid (results in 404)
        """
        try:
            return date_type.fromisoformat(value)
        except ValueError as e:
            # Invalid date format - Django will convert this to 404
            raise ValueError(f"Invalid date format: {value}") from e

    def to_url(self, value) -> str:
        """
        Convert datetime.date object (or string) to URL string.

        Args:
            value: datetime.date object or ISO string

        Returns:
            Date string in YYYY-MM-DD format
        """
        if isinstance(value, date_type):
            return value.isoformat()
        # Already a string - return as-is
        return str(value)
