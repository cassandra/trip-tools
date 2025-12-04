from dataclasses import dataclass
from typing import Optional

from tt.apps.journal.models import Journal

from .enums import TravelogPageType, ContentType


@dataclass
class TravelogPageContext:
    """
    Resolved content context for a travelog view request.

    Contains only the core context needed to resolve content:
    - journal: The Journal being viewed
    - content_type: Whether viewing current, draft, or historical version
    - version_number: Only populated for VERSION content type

    Page-specific data (like TOC entries, day numbers) should be in
    dedicated dataclasses (e.g., DayPageData) built by services.
    """
    journal        : Journal
    content_type   : ContentType
    page_type      : TravelogPageType
    version_number : Optional[int]   = None  # Only for VERSION content type
    
    def is_draft(self) -> bool:
        return bool( self.content_type.is_draft )

    def is_current_published(self) -> bool:
        return bool( self.content_type.is_view )

    def is_historical_version(self) -> bool:
        return bool( self.content_type.is_version )

    def get_version_param(self) -> Optional[str]:
        """
        Get version parameter for URL generation.

        Returns:
            'draft' for DRAFT content
            str(version_number) for VERSION content
            None for VIEW content (current published version)
        """
        if self.content_type.is_draft:
            return 'draft'
        elif self.content_type.is_version:
            return str(self.version_number) if self.version_number else None
        else:  # VIEW
            return None
        
