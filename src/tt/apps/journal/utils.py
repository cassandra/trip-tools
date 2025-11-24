"""
Utility functions for journal operations.
"""
from datetime import date as date_type, datetime, timedelta
from typing import Tuple
import pytz


class JournalUtils:

    @classmethod
    def get_entry_date_boundaries( cls,
                                   entry_date   : date_type,
                                   timezone_str : str       ) -> Tuple[datetime, datetime]:
        """
        Calculate timezone-aware datetime boundaries for a journal entry's day.

        Returns the full local day boundaries, which may be 23, 24, or 25 hours
        depending on DST transitions in the specified timezone.

        Args:
            entry_date: datetime.date object for the journal entry
            timezone_str: pytz timezone string (e.g., 'America/New_York')

        Returns:
            tuple: (start_datetime, end_datetime) as timezone-aware datetimes
            representing midnight to midnight in the local timezone.

        Example:
            date = date(2025, 1, 15)
            tz = 'America/New_York'
            start, end = get_entry_date_boundaries(date, tz)
            # start = 2025-01-15 00:00:00-05:00
            # end = 2025-01-16 00:00:00-05:00
        """
        tz = pytz.timezone(timezone_str)

        # Start of day in entry timezone
        start_datetime = tz.localize(
            datetime.combine(entry_date, datetime.min.time())
        )

        # End of day (start of next day) in entry timezone
        end_datetime = tz.localize(
            datetime.combine(entry_date + timedelta(days=1), datetime.min.time())
        )

        return start_datetime, end_datetime
