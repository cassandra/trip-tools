"""
URL configuration for itineraries app.
"""

from django.urls import path

from . import views

urlpatterns = [
    path(r'<uuid:trip_uuid>', views.ItinerariesHomeView.as_view(), name='itineraries_home'),
]
