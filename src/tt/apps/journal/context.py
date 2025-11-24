from dataclasses import dataclass
from typing import Optional, Union
from uuid import UUID

from django.db.models import QuerySet

from .models import Journal


@dataclass
class JournalPageContext:
    """Context data for journal page templates.

    Attributes:
        journal: Current active journal
        journal_entries: QuerySet of JournalEntry objects for the journal,
                        ordered by date. Used for sidebar navigation.
        journal_entry_uuid: UUID of the currently viewed JournalEntry.
                           Used to highlight the active entry in sidebar.
                           None when on the list view.
    """
    journal            : Journal
    journal_entries    : Optional[QuerySet]        = None
    journal_entry_uuid : Optional[Union[UUID, str]] = None

    def __post_init__(self):
        # Convert string to UUID if needed, validate format
        if self.journal_entry_uuid:
            if isinstance(self.journal_entry_uuid, str):
                try:
                    self.journal_entry_uuid = UUID(self.journal_entry_uuid)
                except (ValueError, TypeError):
                    self.journal_entry_uuid = None
        return
    
