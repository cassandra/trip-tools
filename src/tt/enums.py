from enum import Enum


class FeaturePageType(str, Enum):
    """Enum for top-level feature pages."""

    DASHBOARD  = 'dashboard'
    TRIPS      = 'trips'
    IMAGES     = 'images'
    ACCOUNT    = 'account'
    SETTINGS   = 'settings'
