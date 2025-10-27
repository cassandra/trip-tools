from django.db import models


class ContactInfoManager(models.Manager):
    """Manager for ContactInfo model."""

    def for_object(self, obj):
        """Get all contact info for a specific object (via GenericForeignKey)."""
        from django.contrib.contenttypes.models import ContentType
        content_type = ContentType.objects.get_for_model(obj.__class__)
        return self.filter(
            content_type=content_type,
            object_id=obj.pk,
        )

    def phones(self):
        """Get only phone contact info."""
        return self.filter(contact_type='phone')

    def emails(self):
        """Get only email contact info."""
        return self.filter(contact_type='email')

    def websites(self):
        """Get only website contact info."""
        return self.filter(contact_type='website')
