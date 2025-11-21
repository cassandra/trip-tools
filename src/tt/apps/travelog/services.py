from django.contrib.auth.models import User as UserType
from django.db import models, transaction

from tt.apps.journal.models import Journal, JournalEntry


class PublishingService:

    @classmethod
    def publish_journal( cls, journal : Journal, user : UserType ):

        with transaction.atomic():
            # Auto-assigns version number safely
            travelog = Travelog.objects.create_next_version(
                journal = journal,
                title = journal.title,
                description = journal.description,
                published_datetime = timezone.now(),
                published_by = user
            )



            zzzzz needs entrries too!
            # Mark as current
            journal.travelogs.exclude( pk = travelog.pk ).update( is_current = False )
            travelog.is_current = True
            travelog.save()
            
            return travelog
