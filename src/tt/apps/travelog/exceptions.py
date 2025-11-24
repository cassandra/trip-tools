from uuid import UUID


class PasswordRequiredException(Exception):
    """
    Exception raised when a password-protected journal requires authentication.

    Carries the journal UUID to enable redirect to password entry view.
    """

    def __init__(self, journal_uuid: UUID, message: str = "Password required to access this journal"):
        self.journal_uuid = journal_uuid
        self.message = message
        super().__init__(self.message)
