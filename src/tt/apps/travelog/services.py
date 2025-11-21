from django.contrib.auth.models import User as UserType
from django.db import models, transaction

from tt.apps.journal.models import Journal, JournalEntry


class PublishingService:

    @classmethod
    def publish_journal( cls, journal : Journal, user : UserType ):
        raise NotImplementedError()
