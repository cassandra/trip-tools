import logging
from datetime import date

from django.test import TransactionTestCase

from ..helpers import TravelogHelpers

logging.disable(logging.CRITICAL)


class TestFormatTripDateSpan(TransactionTestCase):
    """Test smart date span formatting for trip headers."""

    def test_single_day(self):
        """Single day trip shows just one date."""
        result = TravelogHelpers.format_trip_date_span(date(2024, 3, 15), date(2024, 3, 15))
        self.assertEqual(result, 'March 15, 2024')

    def test_same_month_same_year(self):
        """Same month shows month once with day range."""
        result = TravelogHelpers.format_trip_date_span(date(2024, 3, 13), date(2024, 3, 20))
        self.assertEqual(result, 'March 13-20, 2024')

    def test_different_months_same_year(self):
        """Different months in same year shows both month-day pairs."""
        result = TravelogHelpers.format_trip_date_span(date(2024, 3, 28), date(2024, 4, 5))
        self.assertEqual(result, 'March 28 - April 5, 2024')

    def test_different_years(self):
        """Different years shows full dates on both sides."""
        result = TravelogHelpers.format_trip_date_span(date(2024, 12, 28), date(2025, 1, 5))
        self.assertEqual(result, 'December 28, 2024 - January 5, 2025')

    def test_year_boundary_same_month_name(self):
        """Year boundary with same month name (edge case)."""
        # January to January across years
        result = TravelogHelpers.format_trip_date_span(date(2024, 1, 28), date(2025, 1, 5))
        self.assertEqual(result, 'January 28, 2024 - January 5, 2025')

    def test_multi_month_span(self):
        """Trip spanning multiple months in same year."""
        result = TravelogHelpers.format_trip_date_span(date(2024, 6, 15), date(2024, 9, 20))
        self.assertEqual(result, 'June 15 - September 20, 2024')
