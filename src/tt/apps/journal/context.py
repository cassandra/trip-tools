from dataclasses import dataclass
from typing import Optional

from django.db.models import QuerySet

from .models import Journal


@dataclass
class JournalPageContext:
    """Context data for journal page templates.

    Attributes:
        journal: Current active journal
        journal_entries: QuerySet of JournalEntry objects for the journal,
                        ordered by date. Used for sidebar navigation.
        journal_entry_pk: Primary key of the currently viewed JournalEntry.
                         Used to highlight the active entry in sidebar.
                         None when on the list view.
    """
    journal           : Journal
    journal_entries   : Optional[QuerySet]  = None
    journal_entry_pk  : Optional[int]       = None

    def __post_init__(self):
        # Enforce int to ensure consistent type comparisons. This often comes from url params (str).
        try:
            self.journal_entry_pk = int(self.journal_entry_pk)
        except (TypeError, ValueError):
            pass
        return
    
