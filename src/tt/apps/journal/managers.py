from typing import TYPE_CHECKING, Optional

from django.db import models

if TYPE_CHECKING:
    from .models import Journal, JournalEntry


class JournalManager(models.Manager):
    """Manager for Journal model."""

    def for_trip(self, trip) -> models.QuerySet:
        """
        Get all journals for a specific trip.
        Returns QuerySet (may be empty).
        """
        return self.filter(trip = trip)

    def get_primary_for_trip(self, trip) -> Optional['Journal']:
        """
        Get the primary/first journal for a trip (MVP convenience method).
        Returns the first journal ordered by created_datetime, or None if no journal exists.

        Note: MVP assumes one journal per trip. This method provides backwards-compatible
        access pattern while the database schema supports multiple journals.
        """
        return self.filter(trip = trip).order_by('created_datetime').first()


class JournalEntryManager(models.Manager):
    """Manager for JournalEntry model."""

    def for_journal(self, journal) -> models.QuerySet:
        """Get all entries for a specific journal."""
        return self.filter(journal = journal)
