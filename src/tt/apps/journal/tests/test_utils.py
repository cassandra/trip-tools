"""
Tests for JournalUtils timezone-aware date boundary calculations.

Tests focus on:
- Timezone-aware datetime boundary calculations for journal entries
- DST transition edge cases
- Timezone offset handling
- Date boundary correctness across different timezones
- Invalid timezone handling
"""
import logging
from datetime import date, datetime, timedelta
import pytz

from django.test import TestCase

from tt.apps.journal.utils import JournalUtils

logging.disable(logging.CRITICAL)


class JournalUtilsDateBoundariesTestCase(TestCase):
    """Test timezone-aware date boundary calculations."""

    def test_get_entry_date_boundaries_utc(self):
        """UTC timezone should return standard midnight boundaries."""
        entry_date = date(2025, 1, 15)

        start, end = JournalUtils.get_entry_date_boundaries(entry_date, 'UTC')

        # Verify start is midnight UTC
        self.assertEqual(start, datetime(2025, 1, 15, 0, 0, 0, tzinfo=pytz.UTC))
        # Verify end is midnight next day UTC
        self.assertEqual(end, datetime(2025, 1, 16, 0, 0, 0, tzinfo=pytz.UTC))
        # Verify both are timezone-aware
        self.assertIsNotNone(start.tzinfo)
        self.assertIsNotNone(end.tzinfo)

    def test_get_entry_date_boundaries_new_york_est(self):
        """Eastern timezone (EST) should return correct UTC offset."""
        entry_date = date(2025, 1, 15)  # Winter - EST (UTC-5)

        start, end = JournalUtils.get_entry_date_boundaries(entry_date, 'America/New_York')

        # EST is UTC-5, so midnight EST = 05:00 UTC
        expected_start = datetime(2025, 1, 15, 5, 0, 0, tzinfo=pytz.UTC)
        expected_end = datetime(2025, 1, 16, 5, 0, 0, tzinfo=pytz.UTC)

        # Convert to UTC for comparison
        self.assertEqual(start.astimezone(pytz.UTC), expected_start)
        self.assertEqual(end.astimezone(pytz.UTC), expected_end)

    def test_get_entry_date_boundaries_new_york_edt(self):
        """Eastern timezone (EDT) should handle DST correctly."""
        entry_date = date(2025, 7, 15)  # Summer - EDT (UTC-4)

        start, end = JournalUtils.get_entry_date_boundaries(entry_date, 'America/New_York')

        # EDT is UTC-4, so midnight EDT = 04:00 UTC
        expected_start = datetime(2025, 7, 15, 4, 0, 0, tzinfo=pytz.UTC)
        expected_end = datetime(2025, 7, 16, 4, 0, 0, tzinfo=pytz.UTC)

        # Convert to UTC for comparison
        self.assertEqual(start.astimezone(pytz.UTC), expected_start)
        self.assertEqual(end.astimezone(pytz.UTC), expected_end)

    def test_get_entry_date_boundaries_tokyo(self):
        """Tokyo timezone (JST, UTC+9) should return correct offset."""
        entry_date = date(2025, 1, 15)

        start, end = JournalUtils.get_entry_date_boundaries(entry_date, 'Asia/Tokyo')

        # JST is UTC+9, so midnight JST = 15:00 previous day UTC
        expected_start = datetime(2025, 1, 14, 15, 0, 0, tzinfo=pytz.UTC)
        expected_end = datetime(2025, 1, 15, 15, 0, 0, tzinfo=pytz.UTC)

        # Convert to UTC for comparison
        self.assertEqual(start.astimezone(pytz.UTC), expected_start)
        self.assertEqual(end.astimezone(pytz.UTC), expected_end)

    def test_get_entry_date_boundaries_sydney(self):
        """Sydney timezone should handle southern hemisphere DST."""
        # January is summer in Australia (AEDT, UTC+11)
        entry_date = date(2025, 1, 15)

        start, end = JournalUtils.get_entry_date_boundaries(entry_date, 'Australia/Sydney')

        # AEDT is UTC+11, so midnight AEDT = 13:00 previous day UTC
        expected_start = datetime(2025, 1, 14, 13, 0, 0, tzinfo=pytz.UTC)
        expected_end = datetime(2025, 1, 15, 13, 0, 0, tzinfo=pytz.UTC)

        # Convert to UTC for comparison
        self.assertEqual(start.astimezone(pytz.UTC), expected_start)
        self.assertEqual(end.astimezone(pytz.UTC), expected_end)

    def test_get_entry_date_boundaries_duration_24_hours(self):
        """Date boundaries should always span exactly 24 hours."""
        test_cases = [
            ('UTC', date(2025, 1, 15)),
            ('America/New_York', date(2025, 1, 15)),
            ('Asia/Tokyo', date(2025, 6, 15)),
            ('Europe/London', date(2025, 12, 25)),
        ]

        for timezone_str, entry_date in test_cases:
            with self.subTest(timezone=timezone_str, date=entry_date):
                start, end = JournalUtils.get_entry_date_boundaries(entry_date, timezone_str)

                # Calculate duration
                duration = end - start

                # Should be exactly 24 hours
                self.assertEqual(duration, timedelta(hours=24))

    def test_get_entry_date_boundaries_start_before_end(self):
        """Start datetime should always be before end datetime."""
        entry_date = date(2025, 1, 15)

        for timezone_str in ['UTC', 'America/New_York', 'Asia/Tokyo', 'Europe/London']:
            with self.subTest(timezone=timezone_str):
                start, end = JournalUtils.get_entry_date_boundaries(entry_date, timezone_str)

                self.assertLess(start, end)

    def test_get_entry_date_boundaries_returns_tuple(self):
        """Should return tuple of two datetime objects."""
        entry_date = date(2025, 1, 15)

        result = JournalUtils.get_entry_date_boundaries(entry_date, 'UTC')

        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], datetime)
        self.assertIsInstance(result[1], datetime)


class JournalUtilsDSTTransitionTestCase(TestCase):
    """Test DST transition edge cases."""

    def test_dst_spring_forward_new_york(self):
        """Test date during spring DST transition (EST -> EDT)."""
        # 2025-03-09: DST transition in US (spring forward at 2am -> 3am)
        entry_date = date(2025, 3, 9)

        start, end = JournalUtils.get_entry_date_boundaries(entry_date, 'America/New_York')

        # On spring forward day, duration is 23 hours (clock skips 2am-3am)
        duration = end - start
        self.assertEqual(duration, timedelta(hours=23))

        # Verify timezone awareness
        self.assertIsNotNone(start.tzinfo)
        self.assertIsNotNone(end.tzinfo)

    def test_dst_fall_back_new_york(self):
        """Test date during fall DST transition (EDT -> EST)."""
        # 2025-11-02: DST transition in US (fall back at 2am -> 1am)
        entry_date = date(2025, 11, 2)

        start, end = JournalUtils.get_entry_date_boundaries(entry_date, 'America/New_York')

        # On fall back day, duration is 25 hours (clock repeats 1am-2am)
        duration = end - start
        self.assertEqual(duration, timedelta(hours=25))

        # Verify timezone awareness
        self.assertIsNotNone(start.tzinfo)
        self.assertIsNotNone(end.tzinfo)

    def test_dst_spring_forward_london(self):
        """Test date during UK spring DST transition (GMT -> BST)."""
        # 2025-03-30: UK DST transition (spring forward)
        entry_date = date(2025, 3, 30)

        start, end = JournalUtils.get_entry_date_boundaries(entry_date, 'Europe/London')

        # On spring forward day, duration is 23 hours
        duration = end - start
        self.assertEqual(duration, timedelta(hours=23))

    def test_dst_fall_back_sydney(self):
        """Test southern hemisphere DST transition (Sydney)."""
        # 2025-04-06: Sydney DST ends (fall back)
        entry_date = date(2025, 4, 6)

        start, end = JournalUtils.get_entry_date_boundaries(entry_date, 'Australia/Sydney')

        # On fall back day, duration is 25 hours
        duration = end - start
        self.assertEqual(duration, timedelta(hours=25))


class JournalUtilsEdgeCasesTestCase(TestCase):
    """Test edge cases and error handling."""

    def test_leap_year_date(self):
        """Leap year dates should be handled correctly."""
        # 2024 is a leap year
        entry_date = date(2024, 2, 29)

        start, end = JournalUtils.get_entry_date_boundaries(entry_date, 'UTC')

        self.assertEqual(start, datetime(2024, 2, 29, 0, 0, 0, tzinfo=pytz.UTC))
        self.assertEqual(end, datetime(2024, 3, 1, 0, 0, 0, tzinfo=pytz.UTC))

    def test_year_boundary_date(self):
        """New Year's Eve should roll over correctly."""
        entry_date = date(2024, 12, 31)

        start, end = JournalUtils.get_entry_date_boundaries(entry_date, 'UTC')

        self.assertEqual(start, datetime(2024, 12, 31, 0, 0, 0, tzinfo=pytz.UTC))
        self.assertEqual(end, datetime(2025, 1, 1, 0, 0, 0, tzinfo=pytz.UTC))

    def test_year_boundary_with_timezone_offset(self):
        """New Year's Eve with timezone offset should be correct."""
        entry_date = date(2024, 12, 31)

        start, end = JournalUtils.get_entry_date_boundaries(entry_date, 'Asia/Tokyo')

        # JST is UTC+9, so Dec 31 midnight JST = Dec 30 15:00 UTC
        expected_start = datetime(2024, 12, 30, 15, 0, 0, tzinfo=pytz.UTC)
        expected_end = datetime(2024, 12, 31, 15, 0, 0, tzinfo=pytz.UTC)

        self.assertEqual(start.astimezone(pytz.UTC), expected_start)
        self.assertEqual(end.astimezone(pytz.UTC), expected_end)

    def test_invalid_timezone_raises_exception(self):
        """Invalid timezone string should raise exception."""
        entry_date = date(2025, 1, 15)

        with self.assertRaises(pytz.exceptions.UnknownTimeZoneError):
            JournalUtils.get_entry_date_boundaries(entry_date, 'Invalid/Timezone')

    def test_empty_timezone_raises_exception(self):
        """Empty timezone string should raise exception."""
        entry_date = date(2025, 1, 15)

        with self.assertRaises(pytz.exceptions.UnknownTimeZoneError):
            JournalUtils.get_entry_date_boundaries(entry_date, '')

    def test_consecutive_dates_no_overlap(self):
        """Consecutive dates should not overlap (end of day N = start of day N+1)."""
        date1 = date(2025, 1, 15)
        date2 = date(2025, 1, 16)

        start1, end1 = JournalUtils.get_entry_date_boundaries(date1, 'America/New_York')
        start2, end2 = JournalUtils.get_entry_date_boundaries(date2, 'America/New_York')

        # End of Jan 15 should equal start of Jan 16
        self.assertEqual(end1, start2)

        # No gap between dates
        self.assertEqual(end1 - start1, timedelta(hours=24))
        self.assertEqual(end2 - start2, timedelta(hours=24))


class JournalUtilsTimezoneConsistencyTestCase(TestCase):
    """Test timezone consistency across different scenarios."""

    def test_same_date_different_timezones(self):
        """Same date in different timezones should have different UTC times."""
        entry_date = date(2025, 1, 15)

        start_utc, _ = JournalUtils.get_entry_date_boundaries(entry_date, 'UTC')
        start_ny, _ = JournalUtils.get_entry_date_boundaries(entry_date, 'America/New_York')
        start_tokyo, _ = JournalUtils.get_entry_date_boundaries(entry_date, 'Asia/Tokyo')

        # Convert all to UTC for comparison
        start_utc_utc = start_utc.astimezone(pytz.UTC)
        start_ny_utc = start_ny.astimezone(pytz.UTC)
        start_tokyo_utc = start_tokyo.astimezone(pytz.UTC)

        # All should be different UTC times
        self.assertNotEqual(start_utc_utc, start_ny_utc)
        self.assertNotEqual(start_utc_utc, start_tokyo_utc)
        self.assertNotEqual(start_ny_utc, start_tokyo_utc)

    def test_timezone_info_preserved(self):
        """Returned datetimes should preserve timezone information."""
        entry_date = date(2025, 1, 15)

        start, end = JournalUtils.get_entry_date_boundaries(entry_date, 'America/New_York')

        # Timezone should be preserved (not UTC)
        ny_tz = pytz.timezone('America/New_York')
        self.assertEqual(start.tzinfo.zone, ny_tz.zone)
        self.assertEqual(end.tzinfo.zone, ny_tz.zone)

    def test_utc_conversion_accuracy(self):
        """UTC conversion should be mathematically accurate."""
        entry_date = date(2025, 1, 15)

        # Test with known offset timezone
        start, end = JournalUtils.get_entry_date_boundaries(entry_date, 'America/Chicago')

        # Chicago is UTC-6 in winter (CST)
        # Midnight Chicago = 06:00 UTC
        expected_utc_hour = 6

        self.assertEqual(start.astimezone(pytz.UTC).hour, expected_utc_hour)
        self.assertEqual(end.astimezone(pytz.UTC).hour, expected_utc_hour)

    def test_multiple_calls_same_result(self):
        """Multiple calls with same parameters should return same result."""
        entry_date = date(2025, 1, 15)
        timezone_str = 'America/New_York'

        result1 = JournalUtils.get_entry_date_boundaries(entry_date, timezone_str)
        result2 = JournalUtils.get_entry_date_boundaries(entry_date, timezone_str)

        self.assertEqual(result1[0], result2[0])
        self.assertEqual(result1[1], result2[1])
