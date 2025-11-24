from enum import Enum


class DashboardPage(str, Enum):
    """Enum for dashboard-related pages."""

    TRIPS  = 'trips'
    IMAGES = 'images'
