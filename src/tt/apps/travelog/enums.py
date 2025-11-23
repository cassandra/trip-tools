"""
Enums for the travelog app.
"""
from tt.apps.common.enums import LabeledEnum


class ContentType(LabeledEnum):
    """
    Content type for travelog URLs - determines which version to display.

    - DRAFT: Working copy from Journal (editable, may have unpublished changes)
    - VIEW: Current published version from Travelog (is_current=True)
    - VERSION: Specific historical version from Travelog (by version number)
    """

    DRAFT = (
        'Preview',
        'Working copy with unpublished changes'
    )

    VIEW = (
        'Published',
        'Current published version'
    )

    VERSION = (
        'Archived',
        'Specific published version'
    )

    @classmethod
    def default(cls):
        return ContentType.VIEW
