from django.db import models
from .enums import BookingStatus, PaymentStatus


class BookingManager(models.Manager):

    def for_user(self, user):
        return self.filter( trip__members__user = user ).distinct()

    def for_trip(self, trip):
        return self.filter( trip = trip )

    def by_booking_status(self, status):
        return self.filter( booking_status = status )

    def by_payment_status(self, status):
        return self.filter( payment_status = status )

    def todo(self):
        return self.filter( booking_status = BookingStatus.TODO )

    def unpaid(self):
        return self.filter( payment_status = PaymentStatus.NO )
