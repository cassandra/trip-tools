from dataclasses import dataclass

from .enums import DashboardPage


@dataclass
class DashboardPageContext:
    """
    Encapsulates all data needed for dashboard page navigation.

    Attributes:
        active_page: Which page in the sidebar should be highlighted
    """
    active_page: DashboardPage
