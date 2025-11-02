from django.db import models

from tt.apps.trips.models import Trip

from . import managers


class NotebookEntry(models.Model):
    """
    Raw daily notes taken during a trip.
    Internal-facing scratchpad for capturing experiences in the moment.
    """
    objects = managers.NotebookEntryManager()

    trip = models.ForeignKey(
        Trip,
        on_delete = models.CASCADE,
        related_name = 'notebook_entries',
    )

    date = models.DateField()
    text = models.TextField()

    created_datetime = models.DateTimeField(auto_now_add = True)
    modified_datetime = models.DateTimeField(auto_now = True)

    def __str__(self):
        return f"{self.trip.title} - {self.date}"

    class Meta:
        verbose_name = 'Notebook Entry'
        verbose_name_plural = 'Notebook Entries'
        ordering = ['date']
        unique_together = [('trip', 'date')]
