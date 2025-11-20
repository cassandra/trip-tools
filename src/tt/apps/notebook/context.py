from dataclasses import dataclass
from typing import Optional, Union
from uuid import UUID

from django.db.models import QuerySet


@dataclass
class NotebookPageContext:
    """Context data for notebook page templates.

    Attributes:
        notebook_entries: QuerySet of NotebookEntry objects for the trip,
                         ordered by date. Used for sidebar navigation.
        notebook_entry_uuid: UUID of the currently viewed NotebookEntry.
                            Used to highlight the active entry in sidebar.
                            None when on the list view.
    """
    notebook_entries    : Optional[QuerySet]        = None
    notebook_entry_uuid : Optional[Union[UUID, str]] = None

    def __post_init__(self):
        # Convert string to UUID if needed, validate format
        if self.notebook_entry_uuid:
            if isinstance(self.notebook_entry_uuid, str):
                try:
                    self.notebook_entry_uuid = UUID(self.notebook_entry_uuid)
                except (ValueError, TypeError):
                    self.notebook_entry_uuid = None
        return
 
