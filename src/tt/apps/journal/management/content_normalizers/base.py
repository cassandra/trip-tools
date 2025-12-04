"""Base class for entry content normalizers.

- Normalizers transform HTML content in JournalEntry and TravelogEntry
  records (text field).

- Each normalizer performs a specific transformation and returns a list of
  changes made for logging purposes.

"""
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tt.apps.journal.models import JournalEntryContent


class EntryContentNormalizer(ABC):
    """
    Abstract base class for entry content normalizations.

    Subclasses implement specific transformations (e.g., URL replacements,
    HTML structure fixes, etc.) that can be applied to journal/travelog
    entry content.
    """

    name         : str = "base"
    description  : str = "Base normalizer"

    @abstractmethod
    def normalize( self,
                   html_content  : str,
                   entry         : 'JournalEntryContent') -> tuple[str, list[str]]:
        """
        Normalize the HTML content.

        Args:
            html_content: The HTML text to normalize
            entry: The JournalEntryContent instance (JournalEntry or TravelogEntry)
                   providing context about the entry being processed

        Returns:
            Tuple of:
                - normalized_html: The transformed HTML content
                - changes: List of human-readable descriptions of changes made
                          (empty list if no changes)
        """
        raise NotImplementedError
