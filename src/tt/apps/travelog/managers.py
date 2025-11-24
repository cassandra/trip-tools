from typing import TYPE_CHECKING, Optional
from django.db import models, transaction

if TYPE_CHECKING:
    from .models import Travelog, TravelogEntry

from tt.apps.journal.models import Journal


class TravelogManager(models.Manager):
    """Manager for Travelog model."""

    def for_journal(self, journal: 'Journal') -> models.QuerySet['Travelog']:
        """Get all published versions for a specific journal."""
        return self.filter(journal=journal)

    def get_current(self, journal: 'Journal') -> Optional['Travelog']:
        """Get the currently published version for a journal."""
        return self.filter(journal=journal, is_current=True).first()

    def get_version(self, journal: 'Journal', version_number: int) -> Optional['Travelog']:
        """Get a specific version by number."""
        return self.filter(journal=journal, version_number=version_number).first()

    def get_next_version_number(self, journal: 'Journal') -> int:
        """Calculate the next version number for a journal."""
        last_version = self.filter(journal=journal).aggregate(
            models.Max('version_number')
        )['version_number__max']
        return (last_version or 0) + 1

    def create_next_version(self, journal, **kwargs):
        """
        Create new travelog with auto-calculated version number.
        """
        if 'version_number' in kwargs:
            raise ValueError("version_number is auto-assigned, don't provide it")

        with transaction.atomic():
            # Lock journal row for this transaction
            locked_journal = Journal.objects.select_for_update().get(pk=journal.pk)
            
            # Calculate next version atomically
            next_version = self.get_next_version_number(locked_journal)
            
            # Create with version number
            return self.create(
                journal=locked_journal,
                version_number=next_version,
                **kwargs
            )

        
class TravelogEntryManager(models.Manager):
    """Manager for TravelogEntry model."""

    def for_travelog(self, travelog: 'Travelog') -> models.QuerySet['TravelogEntry']:
        """Get all entry snapshots for a specific published version."""
        return self.filter(travelog=travelog)

    def for_date_range(self, travelog: 'Travelog',
                       start_date, end_date) -> models.QuerySet['TravelogEntry']:
        """Get entry snapshots within a date range."""
        return self.filter(
            travelog=travelog,
            date__gte=start_date,
            date__lte=end_date
        )

    def get_by_date(self, travelog: 'Travelog', date) -> Optional['TravelogEntry']:
        """Get a specific entry snapshot by date."""
        return self.filter(travelog=travelog, date=date).first()
