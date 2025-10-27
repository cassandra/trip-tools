from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

from tt.apps.common.model_fields import LabeledEnumField

from .enums import ContactType
from . import managers


class ContactInfo(models.Model):
    """
    Reusable contact information that can be attached to any model.

    Uses Django's GenericForeignKey to link to Location, Booking, etc.
    Supports phone, email, website, and messaging contacts.
    """
    objects = managers.ContactInfoManager()

    # Generic relation to parent object
    content_type = models.ForeignKey(
        ContentType,
        on_delete = models.CASCADE,
    )
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    contact_type = LabeledEnumField(
        ContactType,
        'Contact Type',
    )
    value = models.TextField(
        help_text = 'Phone number, email address, URL, physical address, or username',
    )
    label = models.CharField(
        max_length = 100,
        blank = True,
        help_text = 'E.g., "Reservations", "Front Desk", "Customer Service"',
    )
    notes = models.TextField(
        blank = True,
        help_text = 'Additional context about this contact',
    )
    is_primary = models.BooleanField(
        default = False,
        help_text = 'Mark as primary contact for this type',
    )

    created_datetime = models.DateTimeField(auto_now_add = True)
    modified_datetime = models.DateTimeField(auto_now = True)

    class Meta:
        verbose_name = 'Contact Info'
        verbose_name_plural = 'Contact Info'
        ordering = ['-is_primary', 'contact_type', 'created_datetime']
        indexes = [
            models.Index( fields=['content_type', 'object_id'] ),
            models.Index( fields=['contact_type']),
        ]
