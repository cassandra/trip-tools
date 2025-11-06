from typing import TYPE_CHECKING

from django.db import models

if TYPE_CHECKING:
    from .models import TripImage


class TripImageManager(models.Manager):
    """Manager for TripImage model."""

    def for_user(self, user) -> models.QuerySet:
        """
        Get all images uploaded by the user.
        TODO: Extend to include images accessible via journal permissions.
        """
        return self.filter(uploaded_by = user)
