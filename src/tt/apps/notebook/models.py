from django.db import models
from django.conf import settings

from tt.apps.trips.models import Trip

from . import managers


class NotebookEntry(models.Model):
    """
    Raw daily notes taken during a trip.
    Internal-facing scratchpad for capturing experiences in the moment.
    """
    objects = managers.NotebookEntryManager()

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete = models.CASCADE,
        related_name = 'notebook_entries',
    )

    trip = models.ForeignKey(
        Trip,
        on_delete = models.CASCADE,
        related_name = 'notebook_entries',
    )

    date = models.DateField()
    text = models.TextField()

    created_datetime = models.DateTimeField(auto_now_add = True)
    modified_datetime = models.DateTimeField(auto_now = True)

    class Meta:
        verbose_name = 'Notebook Entry'
        verbose_name_plural = 'Notebook Entries'
        ordering = ['date']
        unique_together = [('trip', 'date')]
