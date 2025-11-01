from datetime import date as date_type
from typing import TYPE_CHECKING, Optional

from django.db import models

if TYPE_CHECKING:
    from .models import NotebookEntry


class NotebookEntryManager(models.Manager):

    def for_user(self, user) -> models.QuerySet:
        return self.filter(user=user)

    def for_trip(self, trip) -> models.QuerySet:
        return self.filter(trip=trip)

    def for_date(self, trip, date: date_type) -> Optional['NotebookEntry']:
        try:
            return self.get(trip=trip, date=date)
        except self.model.DoesNotExist:
            return None
