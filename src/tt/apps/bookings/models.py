from django.db import models

from tt.apps.attribute.models import AttributeModel
from tt.apps.common.model_fields import LabeledEnumField

from .enums import BookingStatus, PaymentStatus
from . import managers


class BookingData(models.Model):
    """
    A booking data for itinerary items
    """
    objects = managers.BookingManager()

    trip = models.ForeignKey(
        'trips.Trip',
        on_delete = models.CASCADE,
        related_name = 'bookings',
    )
    itinerary_item = models.ForeignKey(
        'itineraries.ItineraryItem',
        on_delete = models.CASCADE,
        related_name = 'bookings',
    )
    booking_status = LabeledEnumField(
        BookingStatus,
        'Booking Status',
    )
    payment_status = LabeledEnumField(
        PaymentStatus,
        'Payment Status',
    )
    cancellation_policy = models.TextField(
        blank = True,
    )
    confirmed = models.BooleanField(
        'Confirmed?',
        default = False,
    )

    booking_site = models.CharField(max_length = 200, blank = True)
    booking_reference = models.CharField(max_length = 200, blank = True)
    confirmation_number = models.CharField(max_length = 200, blank = True)
    payment_method = models.CharField(max_length = 100, blank = True)
    booking_date = models.DateField(null = True, blank = True)
    payment_date = models.DateField(null = True, blank = True)

    total_cost = models.DecimalField(
        max_digits = 10,
        decimal_places = 2,
        null = True,
        blank = True,
    )
    unit_cost = models.DecimalField(
        max_digits = 10,
        decimal_places = 2,
        null = True,
        blank = True,
    )
    currency = models.CharField(
        max_length = 3,
        blank = True,
        help_text = 'E.g., USD, EUR, GBP',
    )

    created_datetime = models.DateTimeField(auto_now_add = True)
    modified_datetime = models.DateTimeField(auto_now = True)

    class Meta:
        verbose_name = 'Booking Data'
        verbose_name_plural = 'Booking Data'

    
class BookingAttribute( AttributeModel ):

    booking_data = models.ForeignKey(
        BookingData,
        on_delete = models.CASCADE,
        related_name = 'attributes',
    )

    class Meta:
        verbose_name = 'Booking Attribute'
        verbose_name_plural = 'Booking Attributes'
    
    def get_upload_to(self):
        return 'bookings/attributes/'
