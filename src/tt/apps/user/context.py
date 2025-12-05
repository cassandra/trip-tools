from dataclasses import dataclass

from .enums import AccountPageType


@dataclass
class AccountPageContext:
    """
    Encapsulates all data needed for account page navigation.
    """

    active_page       : AccountPageType
    
