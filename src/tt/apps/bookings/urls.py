from django.urls import path

from . import views


urlpatterns = [
    path(r'trip/<uuid:trip_uuid>', views.BookingsHomeView.as_view(), name='bookings_home'),
]
