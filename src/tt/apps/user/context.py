from dataclasses import dataclass

from django.conf import settings

from .enums import AccountPage


@dataclass
class AccountPageContext:
    """
    Encapsulates all data needed for account page navigation.
    """

    user               : 'settings.AUTH_USER_MODEL'
    active_page        : AccountPage

    @property
    def account_page_list(self):
        return list( AccountPage )
    
