from enum import Enum


class DashboardPage(str, Enum):
    """Enum for dashboard-related pages."""

    DASHBOARD  = 'dashboard'
    TRIPS      = 'trips'
    IMAGES     = 'images'
