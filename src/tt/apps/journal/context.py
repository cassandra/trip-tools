from dataclasses import dataclass
from typing import Optional, Union
from uuid import UUID

from django.db.models import QuerySet

from .models import Journal, JournalEntry


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
        has_prologue: Boolean indicating if journal has a prologue entry.
        has_epilogue: Boolean indicating if journal has an epilogue entry.
    """
    journal            : Journal
    journal_entries    : Optional[QuerySet]        = None
    journal_entry_uuid : Optional[Union[UUID, str]] = None
    has_prologue       : bool                      = False
    has_epilogue       : bool                      = False

    def __post_init__(self):
        # Convert string to UUID if needed, validate format
        if self.journal_entry_uuid:
            if isinstance(self.journal_entry_uuid, str):
                try:
                    self.journal_entry_uuid = UUID(self.journal_entry_uuid)
                except (ValueError, TypeError):
                    self.journal_entry_uuid = None
        return

    @classmethod
    def create( cls,
                journal          : Optional[Journal],
                journal_entries  : Optional[QuerySet]        = None,
                journal_entry_uuid : Optional[Union[UUID, str]] = None ) -> 'JournalPageContext':
        """
        Factory method to create context with computed special entry flags.

        This computes has_prologue and has_epilogue based on the journal's entries,
        avoiding the need for callers to manage these flags separately.
        """
        has_prologue = False
        has_epilogue = False

        if journal:
            has_prologue = JournalEntry.objects.has_prologue(journal)
            has_epilogue = JournalEntry.objects.has_epilogue(journal)

        return cls(
            journal = journal,
            journal_entries = journal_entries,
            journal_entry_uuid = journal_entry_uuid,
            has_prologue = has_prologue,
            has_epilogue = has_epilogue,
        )
    
