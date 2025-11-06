from dataclasses import dataclass
from typing import Optional

from django.db.models import QuerySet


@dataclass
class NotebookPageContext:
    """Context data for notebook page templates.

    Attributes:
        notebook_entries: QuerySet of NotebookEntry objects for the trip,
                         ordered by date. Used for sidebar navigation.
        notebook_entry_pk: Primary key of the currently viewed NotebookEntry.
                          Used to highlight the active entry in sidebar.
                          None when on the list view.
    """
    notebook_entries   : Optional[QuerySet]  = None
    notebook_entry_pk  : Optional[int]       = None

    def __post_init__(self):
        # Enforce int to ensure consistent type comparisons. This often comes from url params (str).
        try:
            self.notebook_entry_pk = int(self.notebook_entry_pk)
        except (TypeError, ValueError):
            pass
        return
 
