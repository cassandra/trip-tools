from dataclasses import dataclass
from typing import Optional

from tt.apps.journal.models import Journal

from .enums import ContentType


@dataclass
class TravelogPageContext:
    """
    Resolved content context for a travelog view request.
    """
    journal         : Journal
    content_type    : ContentType
    version_number  : Optional[int]  = None  # Only populated for VERSION content type

    def is_draft(self) -> bool:
        return self.content_type == ContentType.DRAFT

    def is_current_published(self) -> bool:
        return self.content_type == ContentType.VIEW

    def is_historical_version(self) -> bool:
        return self.content_type == ContentType.VERSION

    def get_version_param(self) -> Optional[str]:
        """
        Get version parameter for URL generation.

        Returns:
            'draft' for DRAFT content
            str(version_number) for VERSION content
            None for VIEW content (current published version)
        """
        if self.content_type == ContentType.DRAFT:
            return 'draft'
        elif self.content_type == ContentType.VERSION:
            return str(self.version_number) if self.version_number else None
        else:  # VIEW
            return None
