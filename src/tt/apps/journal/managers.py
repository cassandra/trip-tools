from datetime import date as date_class
from typing import TYPE_CHECKING, Optional

from django.db import models

if TYPE_CHECKING:
    from .models import Journal, JournalEntry


class JournalManager(models.Manager):

    def for_trip(self, trip) -> models.QuerySet:
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

    def for_journal(self, journal) -> models.QuerySet:
        return self.filter(journal = journal)

    def get_prologue(self, journal) -> Optional['JournalEntry']:
        return self.filter(journal=journal, date=date_class.min).first()

    def get_epilogue(self, journal) -> Optional['JournalEntry']:
        from datetime import date as date_class
        return self.filter(journal=journal, date=date_class.max).first()

    def has_prologue(self, journal) -> bool:
        return self.filter(journal=journal, date=date_class.min).exists()

    def has_epilogue(self, journal) -> bool:
        return self.filter(journal=journal, date=date_class.max).exists()
