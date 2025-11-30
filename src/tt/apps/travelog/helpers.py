"""
Helper classes and functions for travelog operations.
"""
from datetime import date
from urllib.parse import urlencode

from django.http import HttpRequest
from django.urls import reverse

from tt.apps.journal.models import Journal, JournalEntryContent


class TravelogHelpers:

    @classmethod
    def format_trip_date_span( cls, start_date: date, end_date: date) -> str:
        """
        Format a trip's date span with smart consolidation of repeated elements.

        Used for displaying trip date ranges in travelog headers with minimal
        redundancy while remaining human-readable.

        Formatting rules:
        - Same month, same year: "March 13-20, 2024"
        - Different months, same year: "March 28 - April 5, 2024"
        - Different years: "December 28, 2024 - January 5, 2025"
        - Single day (same date): "March 13, 2024"

        Args:
            start_date: The starting date of the trip
            end_date: The ending date of the trip

        Returns:
            Formatted date span string
        """
        if start_date == end_date:
            # Single day
            return start_date.strftime('%B %-d, %Y')

        same_year = start_date.year == end_date.year
        same_month = same_year and start_date.month == end_date.month

        if same_month:
            # Same month, same year: "March 13-20, 2024"
            return f"{start_date.strftime('%B')} {start_date.day}-{end_date.day}, {start_date.year}"
        elif same_year:
            # Different months, same year: "March 28 - April 5, 2024"
            return f"{start_date.strftime('%B %-d')} - {end_date.strftime('%B %-d')}, {start_date.year}"
        else:
            # Different years: "December 28, 2024 - January 5, 2025"
            return f"{start_date.strftime('%B %-d, %Y')} - {end_date.strftime('%B %-d, %Y')}"

    @classmethod
    def create_travelog_day_url( cls,
                                 request  : HttpRequest,
                                 journal  : Journal,
                                 entry    : JournalEntryContent ) -> str:
        url = reverse( 'travelog_day',
                       kwargs = { 'journal_uuid': journal.uuid,
                                  'date': entry.date.isoformat() } )
        
        query_params = {}
        version_param = request.GET.get('version')
        if version_param:
            query_params['version'] = version_param

        if query_params:
            query = urlencode(query_params)
            url = f"{url}?{query}"
        return url

