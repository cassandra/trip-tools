from dataclasses import dataclass
from typing import Optional

from django.db.models import QuerySet


@dataclass
class JournalPageContext:
    """Context data for journal page templates.

    Attributes:
        journal_entries: QuerySet of JournalEntry objects for the journal,
                        ordered by date. Used for sidebar navigation.
        journal_entry_pk: Primary key of the currently viewed JournalEntry.
                         Used to highlight the active entry in sidebar.
                         None when on the list view.
    """
    journal_entries: Optional[QuerySet] = None
    journal_entry_pk: Optional[int] = None
