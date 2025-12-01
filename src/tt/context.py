from dataclasses import dataclass

from tt.enums import FeaturePageType


@dataclass
class FeaturePageContext:
    """
    Encapsulates all data needed for dashboard page navigation.

    Attributes:
        active_page: Which page in the sidebar should be highlighted
    """
    active_page: FeaturePageType
