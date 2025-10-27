from django.db import models
from .enums import BookingStatus, PaymentStatus


class BookingManager(models.Manager):
    """Manager for BookingData model."""

    def for_user(self, user):
        """Get all bookings for a specific user."""
        return self.filter(user=user)

    def for_trip(self, trip):
        """Get all bookings for a specific trip."""
        return self.filter(trip=trip)

    def by_booking_status(self, status):
        """Get bookings by booking status."""
        return self.filter(booking_status=status)

    def by_payment_status(self, status):
        """Get bookings by payment status."""
        return self.filter(payment_status=status)

    def todo(self):
        """Get bookings that still need to be completed."""
        return self.filter(booking_status=BookingStatus.TODO)

    def unpaid(self):
        """Get bookings that haven't been paid."""
        return self.filter(payment_status=PaymentStatus.NO)
