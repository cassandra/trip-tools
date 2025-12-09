"""
Signal handlers for client config cache invalidation.

Invalidates the cached client config when location categories or
subcategories are created, updated, or deleted.
"""

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from tt.apps.locations.models import LocationCategory, LocationSubCategory

from .services import ClientConfigService


@receiver(post_save, sender=LocationCategory)
@receiver(post_delete, sender=LocationCategory)
def invalidate_on_category_change(sender, instance, **kwargs):
    """
    Invalidate client config cache when a LocationCategory changes.
    """
    ClientConfigService.invalidate_cache()


@receiver(post_save, sender=LocationSubCategory)
@receiver(post_delete, sender=LocationSubCategory)
def invalidate_on_subcategory_change(sender, instance, **kwargs):
    """
    Invalidate client config cache when a LocationSubCategory changes.
    """
    ClientConfigService.invalidate_cache()
